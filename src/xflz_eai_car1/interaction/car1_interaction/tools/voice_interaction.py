#!/usr/bin/env python3
"""
Real-time voice interaction system — full pipeline:

  Microphone → VAD(gating) → KWS(wake word) → ASR(streaming) → LLM(streaming) → TTS(segmented playback)

Architecture:
  4 daemon threads, communicating via Queue + Event:
    Audio Capture  — ALSA → audio_queue
    Main Loop       — state machine, VAD/KWS/ASR inference
    LLM Worker      — HTTP streaming, sentence segmentation → tts_queue
    TTS Player      — synthesis + aplay

States:  IDLE ←→ LISTENING → PROCESSING → ACTIVE_LISTENING → IDLE

Usage:
  python3 voice_interaction.py
  python3 voice_interaction.py --config my_config.yaml
  python3 voice_interaction.py --debug
"""

import argparse
import json
import logging
import os
import queue
import re
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from collections import deque
from queue import Queue, Empty

import numpy as np
import sherpa_onnx
import yaml

from audio_utils import setup_capture, setup_playback, play_wav_sync

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-5s] %(message)s",
    datefmt="%H:%M:%S",
)

# Module-level loggers, shared across threads
log_audio = logging.getLogger("Audio")
log_vad   = logging.getLogger("VAD")
log_kws   = logging.getLogger("KWS")
log_asr   = logging.getLogger("ASR")
log_llm   = logging.getLogger("LLM")
log_tts   = logging.getLogger("TTS")
log_state = logging.getLogger("State")


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(script_dir, p):
    """Resolve a path: absolute paths stay, relative paths are relative to script_dir."""
    if os.path.isabs(p):
        return p
    return os.path.join(script_dir, p)


# ---------------------------------------------------------------------------
# LLM HTTP client (minimal, compatible with RKLLM server)
# ---------------------------------------------------------------------------

class LLMClient:
    """OpenAI-compatible streaming client for RKLLM server."""

    def __init__(self, base_url, timeout=120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        try:
            import requests
            self.requests = requests
        except ImportError:
            log_llm.error("requests 库未安装，请执行: pip install requests")
            sys.exit(1)
        self.session = self.requests.Session()
        self.session.keep_alive = False

    def chat_stream(self, messages, temperature=0.8, top_p=0.9, max_tokens=4096,
                    repeat_penalty=1.1, interrupt_event=None):
        """Streaming chat — yields content tokens.

        Checks interrupt_event (threading.Event) before each token; stops
        immediately when the event is set.
        """
        data = {
            "model": "rkllm",
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "repeat_penalty": repeat_penalty,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "stream": True,
        }
        headers = {"Content-Type": "application/json", "Authorization": "not_required"}
        resp = self.session.post(
            f"{self.base_url}/v1/chat/completions",
            json=data, headers=headers, stream=True,
            timeout=(10, self.timeout),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM 服务器返回 {resp.status_code}: {resp.text[:200]}")

        try:
            for line in resp.iter_lines(decode_unicode=True):
                # Respect external interrupt
                if interrupt_event and interrupt_event.is_set():
                    resp.close()
                    break

                if not (line.startswith("data: ") and len(line) > 6):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break

                try:
                    chunk = json.loads(payload)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        finally:
            # Ensure connection is closed even on exception
            resp.close()


# ---------------------------------------------------------------------------
# VoiceInteraction — main class
# ---------------------------------------------------------------------------

class VoiceInteraction:
    """Real-time voice interaction pipeline."""

    # Sentence splitter: Chinese punctuation always splits; English (.?!) only
    # when followed by space/newline/end-of-string (avoids splitting "Qwen3.5").
    _SENTENCE_RE = re.compile(
        r'([。！？；，\n]|[.?!](?=\s|$))'
    )

    def __init__(self, config_path, auto_start_llm=True):
        self.config = load_config(config_path)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        cfg_audio = self.config["audio"]
        self.sample_rate = cfg_audio["sample_rate"]
        self.chunk_size = cfg_audio["chunk_size"]
        self.capture_device = cfg_audio["capture_device"]
        self.playback_device = cfg_audio["playback_device"]

        # Resolve resource dir
        self.resource_dir = resolve_path(
            self.script_dir, self.config["interaction"]["resource_dir"])

        # --- Thread control ---
        self.running = threading.Event()
        self.running.set()
        self.interrupt_event = threading.Event()
        self.tts_done_event = threading.Event()
        self.tts_done_event.set()  # initially idle

        # --- Queues ---
        self.audio_queue = Queue(maxsize=200)
        self.llm_request_queue = Queue(maxsize=1)
        self.tts_queue = Queue(maxsize=50)

        # --- State ---
        self.state_lock = threading.Lock()
        self._state = "IDLE"

        # --- Pre-buffer (for VAD gating delay compensation) ---
        pre_buf_sec = self.config["vad"]["pre_buffer_duration"]
        self.pre_buf_chunks = max(1, int(
            pre_buf_sec * self.sample_rate / self.chunk_size))
        self.pre_buffer = deque(maxlen=self.pre_buf_chunks)
        log_audio.info(
            f"预缓冲: {pre_buf_sec}s ({self.pre_buf_chunks} 帧 × {self.chunk_size} 采样)")

        # --- Audio mixer ---
        self._setup_mixer()

        # --- Init models ---
        self._init_vad()
        self._init_kws()
        self._init_asr()
        self._init_tts()

        # --- Start LLM server (if configured for auto-start) ---
        if auto_start_llm and self.config.get("llm_server", {}).get("auto_start", True):
            self._start_llm_server()
            self._wait_for_llm_server()

        self._init_llm_client()

        # --- KWS stream & VAD state ---
        self.kws_stream = None
        self._vad_in_speech = False
        self._vad_waiting_silence = False  # Flag to wait for silence after wake-word

        # --- ASR stream ---
        self.asr_stream = None
        self._asr_last_partial = ""

        # --- ACTIVE_LISTENING timer ---
        self.active_timeout = self.config["interaction"]["active_timeout"]
        self._active_start = 0.0

        # --- TTS subprocess (so we can kill it on interrupt) ---
        self._aplay_proc = None

        # --- LLM server subprocess (auto-started unless --no-server) ---
        self._llm_server_proc = None

        # --- Prompt playback tracking (async, so main loop isn't blocked) ---
        self._prompt_proc = None
        self._vad_mute_until = 0.0

        log_state.info("初始化完成，进入 IDLE 状态")

    # -------------------------------------------------------------------
    # Property for thread-safe state access
    # -------------------------------------------------------------------

    @property
    def state(self):
        with self.state_lock:
            return self._state

    @state.setter
    def state(self, val):
        with self.state_lock:
            self._state = val

    # -------------------------------------------------------------------
    # Audio mixer
    # -------------------------------------------------------------------

    def _setup_mixer(self):
        cfg = self.config["audio"]
        card = 0
        setup_capture(card, cfg["capture_volume"], cfg.get("mic_boost", True))
        log_audio.info(
            f"录音: {cfg['capture_device']} vol={cfg['capture_volume']}% "
            f"boost={'on' if cfg.get('mic_boost', True) else 'off'}")
        setup_playback(card, cfg["playback_volume"])
        log_audio.info(
            f"播放: {cfg['playback_device']} vol={cfg['playback_volume']}%")

    # -------------------------------------------------------------------
    # Model initialisation
    # -------------------------------------------------------------------

    def _init_vad(self):
        cfg = self.config["vad"]
        silero = sherpa_onnx.SileroVadModelConfig(
            model=cfg["model"],
            threshold=cfg["threshold"],
            min_silence_duration=cfg["min_silence_duration"],
            min_speech_duration=cfg["min_speech_duration"],
            max_speech_duration=cfg["max_speech_duration"],
        )
        vad_config = sherpa_onnx.VadModelConfig(
            silero_vad=silero,
            sample_rate=self.sample_rate,
            num_threads=4,
            provider="cpu",
        )
        self.vad = sherpa_onnx.VoiceActivityDetector(
            config=vad_config,
            buffer_size_in_seconds=cfg["max_speech_duration"] + 5,
        )
        log_vad.info(
            f"模型: {os.path.basename(cfg['model'])} "
            f"threshold={cfg['threshold']} "
            f"min_silence={cfg['min_silence_duration']}s "
            f"min_speech={cfg['min_speech_duration']}s")

    def _init_kws(self):
        cfg = self.config["kws"]
        model_dir = cfg["model_dir"]
        keywords_file = resolve_path(self.script_dir, cfg["keywords_file"])

        self.kws = sherpa_onnx.KeywordSpotter(
            tokens=os.path.join(model_dir, "tokens.txt"),
            encoder=os.path.join(model_dir, "encoder-epoch-13-avg-2-chunk-16-left-64.int8.onnx"),
            decoder=os.path.join(model_dir, "decoder-epoch-13-avg-2-chunk-16-left-64.onnx"),
            joiner=os.path.join(model_dir, "joiner-epoch-13-avg-2-chunk-16-left-64.int8.onnx"),
            keywords_file=keywords_file,
            num_threads=4,
            sample_rate=self.sample_rate,
            max_active_paths=4,
            keywords_score=cfg["keywords_score"],
            keywords_threshold=cfg["threshold"],
            num_trailing_blanks=2,
            provider=cfg["provider"],
        )
        # Show configured keywords
        with open(keywords_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and "@" in line:
                    log_kws.info(f"唤醒词: {line.split('@')[-1].strip()}")
        log_kws.info(f"threshold={cfg['threshold']} provider={cfg['provider']}")

    def _init_asr(self):
        cfg = self.config["asr"]
        model_dir = cfg["model_dir"]

        # For RKNN provider, num_threads controls NPU core mask:
        #   1=auto, 0=core0, -1=core1, -2=core2, -3=core0_1, -4=core0_1_2
        npu_threads = 1 if cfg["provider"] == "rknn" else 4
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=os.path.join(model_dir, "tokens.txt"),
            encoder=os.path.join(model_dir, "encoder.rknn"),
            decoder=os.path.join(model_dir, "decoder.rknn"),
            joiner=os.path.join(model_dir, "joiner.rknn"),
            provider=cfg["provider"],
            num_threads=npu_threads,
            sample_rate=self.sample_rate,
            feature_dim=80,
            decoding_method="greedy_search",
            max_active_paths=4,
            blank_penalty=cfg["blank_penalty"],
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=cfg["endpoint_silence"],
            rule2_min_trailing_silence=cfg["endpoint_silence"] + 1.0,
            rule3_min_utterance_length=20.0,
        )
        log_asr.info(
            f"provider={cfg['provider']} "
            f"blank_penalty={cfg['blank_penalty']} "
            f"endpoint_silence={cfg['endpoint_silence']}s")

    def _init_tts(self):
        cfg = self.config["tts"]
        model_dir = cfg["model_dir"]

        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                    acoustic_model=os.path.join(model_dir, "model-steps-3.onnx"),
                    vocoder=os.path.join(model_dir, "vocos-16khz-univ.onnx"),
                    lexicon=os.path.join(model_dir, "lexicon.txt"),
                    tokens=os.path.join(model_dir, "tokens.txt"),
                    data_dir=os.path.join(model_dir, "espeak-ng-data"),
                ),
                num_threads=cfg["num_threads"],
                debug=False,
            ),
            max_num_sentences=1,
            rule_fsts=",".join([
                os.path.join(model_dir, "phone-zh.fst"),
                os.path.join(model_dir, "date-zh.fst"),
                os.path.join(model_dir, "number-zh.fst"),
            ]),
        )
        if not config.validate():
            raise RuntimeError("TTS 配置验证失败")
        self.tts = sherpa_onnx.OfflineTts(config)
        self.tts_speed = cfg["speed"]
        self.tts_gain = cfg["gain"]
        self.tts_sid = cfg["sid"]
        log_tts.info(f"speed={cfg['speed']} gain=×{cfg['gain']} sid={cfg['sid']}")

    def _init_llm_client(self):
        cfg = self.config["llm"]
        self.llm_client = LLMClient(cfg["server_url"], timeout=cfg["timeout"])
        self.llm_temperature = cfg["temperature"]
        self.llm_top_p = cfg["top_p"]
        self.llm_max_tokens = cfg["max_tokens"]
        self.llm_repeat_penalty = cfg["repeat_penalty"]
        self.llm_system_prompt = cfg["system_prompt"]
        log_llm.info(f"server={cfg['server_url']} temperature={cfg['temperature']}")

    # -------------------------------------------------------------------
    # LLM server subprocess management
    # -------------------------------------------------------------------

    def _start_llm_server(self):
        """Launch the RKLLM Flask server as a subprocess.

        Uses the bundled llm_server/ directory (flask_server.py + fix_freq
        script copied from the RKLLM SDK).  No external SDK paths are
        required at runtime — only librkllmrt.so from the system is needed.
        """
        cfg = self.config["llm_server"]
        # llm_server/ lives next to this script
        server_dir = os.path.join(self.script_dir, "..", "llm_server")
        server_dir = os.path.abspath(server_dir)
        flask_script = os.path.join(server_dir, "flask_server.py")

        if not os.path.exists(flask_script):
            log_llm.error(f"flask_server.py 不存在: {flask_script}")
            raise FileNotFoundError(f"flask_server.py not found: {flask_script}")

        # --- lib/librkllmrt.so symlink ---
        lib_dir = os.path.join(server_dir, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        lib_dst = os.path.join(lib_dir, "librkllmrt.so")
        if not os.path.exists(lib_dst):
            lib_src = cfg["lib_path"]
            if os.path.exists(lib_src):
                os.symlink(lib_src, lib_dst)
                log_llm.info(f"lib 链接: {lib_dst} -> {lib_src}")
            else:
                log_llm.warning(f"librkllmrt.so 未找到: {lib_src}")

        # --- fix_freq: real if enabled, sysfs write if possible ---
        platform = cfg["platform"]
        fix_freq_script = os.path.join(server_dir, f"fix_freq_{platform}.sh")
        if cfg.get("fix_freq", False):
            # Try sudo first, then direct sysfs write, fall back gracefully
            if os.path.exists(fix_freq_script):
                os.chmod(fix_freq_script, 0o755)
                r = subprocess.run(["sudo", "-n", "bash", fix_freq_script],
                                   capture_output=True, check=False)
                if r.returncode != 0:
                    # sudo failed — try direct sysfs (user may have pre-chmod'd)
                    self._fix_freq_sysfs()
            else:
                self._fix_freq_sysfs()
        else:
            # flask_server.py requires this script to exist; make it a no-op
            if not os.path.exists(fix_freq_script):
                with open(fix_freq_script, "w") as f:
                    f.write("#!/bin/bash\nexit 0\n")
                os.chmod(fix_freq_script, 0o755)

        # --- Fake sudo (flask_server.py hardcodes "sudo bash fix_freq_*.sh") ---
        self._fake_sudo_dir = tempfile.mkdtemp(prefix="voice_interaction_")
        fake_sudo = os.path.join(self._fake_sudo_dir, "sudo")
        with open(fake_sudo, "w") as f:
            f.write("#!/bin/bash\nexit 0\n")
        os.chmod(fake_sudo, 0o755)

        env = os.environ.copy()
        env["PATH"] = f"{self._fake_sudo_dir}:{env.get('PATH', '')}"

        # --- Python executable ---
        venv_python = cfg.get("venv_python", sys.executable)
        if not os.path.exists(venv_python):
            venv_python = sys.executable

        cmd = [
            venv_python, flask_script,
            "--rkllm_model_path", cfg["model"],
            "--target_platform", platform,
        ]

        log_llm.info(f"启动 LLM 服务: {os.path.basename(cfg['model'])} @ {platform}")
        log_llm.info("等待 LLM 服务就绪...")

        self._llm_server_proc = subprocess.Popen(
            cmd, cwd=server_dir, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _write_sysfs(path, value):
        """Best-effort write to a sysfs node.  PermissionError is silently
        swallowed — the caller should have pre-chmod'd the nodes or run as
        root for frequency tuning to take effect."""
        try:
            with open(path, "w") as f:
                f.write(str(value))
            return True
        except PermissionError:
            return False

    def _fix_freq_sysfs(self):
        """Direct sysfs write to lock NPU/CPU/GPU/DDR at max frequency.

        Requires the sysfs nodes to be writable — either via `chmod 666`
        done once by root, or by running this script as root.
        """
        ok = 0
        total = 0

        # NPU @ 1 GHz
        for p, v in [
                ("/sys/class/devfreq/27700000.npu/governor", "userspace"),
                ("/sys/class/devfreq/27700000.npu/userspace/set_freq", "1000000000")]:
            total += 1
            ok += self._write_sysfs(p, v)

        # CPU cores
        for cpu in range(8):
            total += 1
            ok += self._write_sysfs(
                f"/sys/devices/system/cpu/cpu{cpu}/cpuidle/state1/disable", "1")
        for policy, freq in [("policy0", "2208000"), ("policy4", "2304000")]:
            for p, v in [
                    (f"/sys/devices/system/cpu/cpufreq/{policy}/scaling_governor", "userspace"),
                    (f"/sys/devices/system/cpu/cpufreq/{policy}/scaling_setspeed", freq)]:
                total += 1
                ok += self._write_sysfs(p, v)

        # GPU @ 950 MHz
        for p, v in [
                ("/sys/class/devfreq/27800000.gpu/governor", "userspace"),
                ("/sys/class/devfreq/27800000.gpu/userspace/set_freq", "950000000")]:
            total += 1
            ok += self._write_sysfs(p, v)

        # DDR @ 2112 MHz
        for p, v in [
                ("/sys/class/devfreq/dmc/governor", "userspace"),
                ("/sys/class/devfreq/dmc/userspace/set_freq", "2112000000")]:
            total += 1
            ok += self._write_sysfs(p, v)

        if ok == total:
            log_llm.info(f"频率锁定完成 ({ok}/{total})")
        else:
            log_llm.warning(
                f"频率锁定: {ok}/{total} 成功，其余需 root 权限。"
                f"执行一次: sudo chmod 666 /sys/class/devfreq/*/governor "
                f"/sys/class/devfreq/*/userspace/set_freq "
                f"/sys/devices/system/cpu/cpufreq/*/scaling_governor "
                f"/sys/devices/system/cpu/cpufreq/*/scaling_setspeed "
                f"/sys/devices/system/cpu/cpu*/cpuidle/state1/disable")

    def _wait_for_llm_server(self, max_wait=120):
        """Poll /v1/models until the LLM server responds."""
        url = self.config["llm"]["server_url"]
        deadline = time.time() + max_wait
        while time.time() < deadline:
            if self._llm_server_proc and self._llm_server_proc.poll() is not None:
                log_llm.error("LLM 服务进程意外退出")
                return False
            try:
                import requests
                r = requests.get(f"{url}/v1/models", timeout=3)
                if r.status_code == 200:
                    log_llm.info(f"LLM 服务就绪 ({url})")
                    return True
            except Exception:
                pass
            time.sleep(1.0)
        log_llm.error(f"LLM 服务启动超时 ({max_wait}s)")
        return False

    def _drain_audio_queue(self):
        """Discard all pending audio chunks to prevent stale data in new state."""
        drained = 0
        while True:
            try:
                self.audio_queue.get_nowait()
                drained += 1
            except Empty:
                break
        if drained > 0:
            log_audio.debug(f"排空 {drained} 帧音频队列")

    # -------------------------------------------------------------------
    # KWS helpers
    # -------------------------------------------------------------------

    def _ensure_kws_stream(self):
        if self.kws_stream is None:
            self.kws_stream = self.kws.create_stream()

    def _destroy_kws_stream(self):
        self.kws_stream = None

    def _check_kws(self, chunk):
        """Feed chunk to KWS; return keyword string if detected, else None."""
        if self.kws_stream is None:
            return None
        self.kws_stream.accept_waveform(self.sample_rate, chunk)
        while self.kws.is_ready(self.kws_stream):
            self.kws.decode_stream(self.kws_stream)
        result = self.kws.get_result(self.kws_stream)
        if result:
            keyword = result.split("@")[-1].strip() if "@" in result else result.strip()
            self.kws.reset_stream(self.kws_stream)
            return keyword
        return None

    # -------------------------------------------------------------------
    # VAD helpers
    # -------------------------------------------------------------------

    def _vad_speech_ended(self):
        """Check if VAD transitioned speech→silence."""
        return self._vad_in_speech and not self.vad.is_speech_detected()

    def _vad_speech_started(self):
        """Check if VAD transitioned silence→speech."""
        return not self._vad_in_speech and self.vad.is_speech_detected()

    # -------------------------------------------------------------------
    # WAV playback
    # -------------------------------------------------------------------

    def _play_wav_sync(self, name):
        """Block the caller until wav playback finishes."""
        path = os.path.join(self.resource_dir, name)
        if os.path.exists(path):
            play_wav_sync(path, self.playback_device)
        else:
            log_audio.warning(f"提示音文件不存在: {path}")

    def _play_wav_async(self, name):
        """Play wav in background; returns subprocess.Popen handle."""
        path = os.path.join(self.resource_dir, name)
        if not os.path.exists(path):
            log_audio.warning(f"提示音文件不存在: {path}")
            return None
        from audio_utils import play_wav
        return play_wav(path, self.playback_device)

    # -------------------------------------------------------------------
    # TTS helpers
    # -------------------------------------------------------------------

    def _tts_synthesize(self, text):
        """Synthesize text and return audio object."""
        return self.tts.generate(text, sid=self.tts_sid, speed=self.tts_speed)

    def _write_wav_stereo(self, path, samples_float32, sample_rate):
        """Write float32 mono samples as stereo S16_LE WAV (for ES8388 I2S)."""
        mono = (np.asarray(samples_float32, dtype=np.float32)
                 .clip(-1.0, 1.0) * 32767).astype(np.int16)
        stereo = np.column_stack([mono, mono]).ravel()
        import wave
        with wave.open(path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(stereo.tobytes())

    def _play_audio(self, audio):
        """Apply gain, write stereo wav, play via aplay (tracked subprocess)."""
        samples = np.array(audio.samples, dtype=np.float32)
        samples = (samples * self.tts_gain).clip(-1.0, 1.0)

        tmp_wav = "/tmp/interaction_tts.wav"
        self._write_wav_stereo(tmp_wav, samples, audio.sample_rate)

        self._aplay_proc = subprocess.Popen(
            ["aplay", "-q", "-D", self.playback_device, tmp_wav],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _kill_playback(self):
        """Kill the active aplay subprocess if any."""
        proc = self._aplay_proc
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=0.5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
        self._aplay_proc = None

    def _kill_prompt(self):
        """Kill the active prompt wav subprocess if any."""
        proc = self._prompt_proc
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=0.5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                pass
        self._prompt_proc = None

    def _wait_playback(self):
        """Wait for current aplay to finish."""
        proc = self._aplay_proc
        if proc is not None:
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        self._aplay_proc = None

    # ===================================================================
    # Threads
    # ===================================================================

    # -------------------------------------------------------------------
    # Thread 1: Audio Capture
    # -------------------------------------------------------------------

    def _audio_capture_loop(self):
        """Continuously read ALSA and push chunks to audio_queue."""
        log_audio.info(f"录音线程启动: device={self.capture_device}")
        try:
            alsa = sherpa_onnx.Alsa(self.capture_device)
        except Exception as e:
            log_audio.error(f"无法打开录音设备: {e}")
            self.running.clear()
            return

        actual_rate = alsa.actual_sample_rate
        log_audio.info(f"实际采样率: {actual_rate}")
        sample_rate = actual_rate if actual_rate > 0 else self.sample_rate

        while self.running.is_set():
            try:
                samples = alsa.read(self.chunk_size)
            except Exception:
                log_audio.warning("ALSA 读取异常，跳过一帧")
                continue
            if not samples:
                continue
            try:
                self.audio_queue.put((sample_rate, samples), timeout=0.5)
            except queue.Full:
                # 丢弃旧帧，保持实时性
                try:
                    self.audio_queue.get_nowait()
                except Empty:
                    pass
                try:
                    self.audio_queue.put((sample_rate, samples), timeout=0.1)
                except queue.Full:
                    pass

    # -------------------------------------------------------------------
    # Thread 2: Main Loop (state machine)
    # -------------------------------------------------------------------

    def _main_loop(self):
        """State machine consuming audio chunks."""
        log_state.info("主循环启动")

        while self.running.is_set():
            try:
                rate, chunk = self.audio_queue.get(timeout=0.3)
            except Empty:
                continue

            # Maintain rolling pre-buffer (used by IDLE / ACTIVE_LISTENING)
            self.pre_buffer.append(chunk)

            state = self.state  # snapshot

            if state == "IDLE":
                self._handle_idle(chunk)
            elif state == "LISTENING":
                self._handle_listening(chunk)
            elif state == "PROCESSING":
                self._handle_processing(chunk)
            elif state == "ACTIVE_LISTENING":
                self._handle_active_listening(chunk)

    # -------------------------------------------------------------------
    # State handler: IDLE
    # -------------------------------------------------------------------

    def _handle_idle(self, chunk):
        """VAD gating → pre_buffer → KWS.  VAD ends without wake → stop KWS."""
        self.vad.accept_waveform(chunk)

        if self._vad_speech_started():
            # Speech just began — create KWS stream and replay pre-buffer.
            # Must check for keyword during replay, not just feed-and-ignore.
            self._ensure_kws_stream()
            detected = None
            for old_chunk in self.pre_buffer:
                kw = self._check_kws(old_chunk)
                if kw:
                    detected = kw
                    break
            if detected:
                self._destroy_kws_stream()
                log_kws.info(f"检测到唤醒词: {detected}")
                self._transition_to_listening()
                return
            self._vad_in_speech = True
            if self.config.get("debug", {}).get("show_vad_status", False):
                log_vad.debug("语音开始 → KWS 激活")

        if self._vad_in_speech:
            # Feed current chunk
            keyword = self._check_kws(chunk)
            if keyword:
                self._destroy_kws_stream()
                self._vad_in_speech = False
                log_kws.info(f"检测到唤醒词: {keyword}")
                self._transition_to_listening()
                return

        if self._vad_speech_ended():
            # Speech ended without wake word — destroy KWS, back to pure VAD
            self._destroy_kws_stream()
            self._vad_in_speech = False
            if self.config.get("debug", {}).get("show_vad_status", False):
                log_vad.debug("语音结束，KWS 关闭")

        # Drain completed VAD segments
        while not self.vad.empty():
            self.vad.pop()

    # -------------------------------------------------------------------
    # State handler: LISTENING
    # -------------------------------------------------------------------

    def _handle_listening(self, chunk):
        """Frontend VAD gating → ASR (built-in endpoint) + KWS interrupt.

        VAD is a voice/silence detector—only feed ASR when someone is actually
        speaking.  Prevents environmental noise from producing spurious
        "VI"-type artifacts.  The recognizer's built-in is_endpoint() handles
        utterance endpointing once speech begins.
        """
        # --- Prompt gate ---
        if self._prompt_proc is not None:
            if self._prompt_proc.poll() is None:
                # Prompt still playing — ignore audio, only check KWS interrupt
                keyword = self._check_kws(chunk)
                if keyword:
                    log_kws.info(f"检测到唤醒词(打断): {keyword}")
                    self._transition_to_listening()
                return
            # Prompt finished — reset state for fresh VAD cycle
            self._prompt_proc = None
            self._drain_audio_queue()
            self.pre_buffer.clear()
            self.asr_stream = None
            self._asr_last_partial = ""
            self._vad_in_speech = False
            self._vad_waiting_silence = True
            log_state.info("提示音播放完成，等待用户说话...")

        # --- VAD gating ---
        self.vad.accept_waveform(chunk)

        # Must wait for silence first (to clear wake-word residue)
        if self._vad_waiting_silence:
            if not self.vad.is_speech_detected():
                # Reached silence — now ready to detect new speech
                self._vad_waiting_silence = False
                log_state.info("检测到静音，准备接收用户语音")
            # During silence-waiting, only check KWS interrupt
            keyword = self._check_kws(chunk)
            if keyword:
                log_kws.info(f"检测到唤醒词(打断): {keyword}")
                self._transition_to_listening()
            # Drain VAD segments but continue to maintain pre_buffer (main loop does it)
            while not self.vad.empty():
                self.vad.pop()
            return

        # --- Normal VAD gating (after silence confirmed) ---
        if self._vad_speech_started():
            self.asr_stream = self.recognizer.create_stream()
            self._asr_last_partial = ""
            for old_chunk in self.pre_buffer:
                self.asr_stream.accept_waveform(self.sample_rate, old_chunk)
                while self.recognizer.is_ready(self.asr_stream):
                    self.recognizer.decode_stream(self.asr_stream)
            self._vad_in_speech = True
            log_vad.info("检测到用户开始说话 → ASR 激活")

        if self._vad_in_speech:
            self.asr_stream.accept_waveform(self.sample_rate, chunk)
            while self.recognizer.is_ready(self.asr_stream):
                self.recognizer.decode_stream(self.asr_stream)

            partial = self.recognizer.get_result_all(self.asr_stream)
            partial_text = partial.text.strip() if partial.text else ""
            if partial_text and partial_text != self._asr_last_partial:
                pad = max(0, len(self._asr_last_partial) - len(partial_text))
                print(f"\r[ASR] {partial_text}{' ' * pad}", end="", flush=True)
                self._asr_last_partial = partial_text

            # Endpoint
            if self.recognizer.is_endpoint(self.asr_stream):
                self.asr_stream.input_finished()
                while self.recognizer.is_ready(self.asr_stream):
                    self.recognizer.decode_stream(self.asr_stream)
                final = self.recognizer.get_result_all(self.asr_stream)
                final_text = final.text.strip() if final.text else ""
                self.asr_stream = None
                self._vad_in_speech = False

                if self._asr_last_partial:
                    print()
                    self._asr_last_partial = ""

                if final_text and len(final_text) >= 2:
                    log_asr.info(f"识别结果: {final_text}")
                    self._transition_to_processing(final_text)
                    return  # Important: exit handler after state transition
                else:
                    if final_text:
                        log_asr.info(f"识别结果过短，丢弃: \"{final_text}\"")
                    else:
                        log_asr.info("端点触发，无有效结果，继续监听")
                    # Reset to wait for new speech
                    self._vad_waiting_silence = True
                    return

        # VAD ended without endpoint (brief noise, cough, etc.)
        if self._vad_speech_ended():
            self._vad_in_speech = False

        while not self.vad.empty():
            self.vad.pop()

        # --- KWS interrupt (full audio, independent of VAD) ---
        keyword = self._check_kws(chunk)
        if keyword:
            if self._vad_in_speech and self.asr_stream:
                self.asr_stream = None
                if self._asr_last_partial:
                    print()
            self._vad_in_speech = False
            log_kws.info(f"检测到唤醒词(打断): {keyword}")
            self._transition_to_listening()

    # -------------------------------------------------------------------
    # State handler: PROCESSING
    # -------------------------------------------------------------------

    def _handle_processing(self, chunk):
        """KWS interrupt detection; LLM+TTS run in their worker threads."""
        # KWS interrupt
        keyword = self._check_kws(chunk)
        if keyword:
            log_kws.info(f"检测到唤醒词(打断): {keyword}")
            self._interrupt_pipeline()
            self._transition_to_listening()
            return

        # Check if pipeline is done
        if self.tts_done_event.is_set():
            log_state.info("LLM+TTS 流水线完成，进入免唤醒窗口")
            self._transition_to_active_listening()

    # -------------------------------------------------------------------
    # State handler: ACTIVE_LISTENING
    # -------------------------------------------------------------------

    def _handle_active_listening(self, chunk):
        """VAD gating → ASR + KWS + countdown timer.  Timeout → IDLE."""
        # Ignore audio during VAD mute window (TTS echo suppression).
        # Pop from pre_buffer to undo main loop's append — we don't want
        # TTS echo sitting in the buffer when we start real VAD processing.
        if time.time() < self._vad_mute_until:
            self.pre_buffer.pop()
            keyword = self._check_kws(chunk)
            if keyword:
                log_kws.info(f"检测到唤醒词: {keyword}")
                self._transition_to_listening()
            return

        elapsed = time.time() - self._active_start

        # Timeout?
        if elapsed >= self.active_timeout:
            log_state.info(f"免唤醒超时 ({self.active_timeout}s) → IDLE")
            self._play_wav_sync("idle.wav")
            self._transition_to_idle()
            return

        # VAD gating
        self.vad.accept_waveform(chunk)

        if self._vad_speech_started():
            # User spoke — replay pre_buffer into ASR
            self.asr_stream = self.recognizer.create_stream()
            self._asr_last_partial = ""
            for old_chunk in self.pre_buffer:
                self.asr_stream.accept_waveform(self.sample_rate, old_chunk)
                while self.recognizer.is_ready(self.asr_stream):
                    self.recognizer.decode_stream(self.asr_stream)
            self._vad_in_speech = True
            if self.config.get("debug", {}).get("show_vad_status", False):
                log_vad.debug("免唤醒窗口 → 语音触发 ASR")

        if self._vad_in_speech:
            # Feed ASR
            self.asr_stream.accept_waveform(self.sample_rate, chunk)
            while self.recognizer.is_ready(self.asr_stream):
                self.recognizer.decode_stream(self.asr_stream)
            partial = self.recognizer.get_result_all(self.asr_stream)
            partial_text = partial.text.strip() if partial.text else ""
            if partial_text and partial_text != self._asr_last_partial:
                pad = max(0, len(self._asr_last_partial) - len(partial_text))
                print(f"\r[ASR] {partial_text}{' ' * pad}", end="", flush=True)
                self._asr_last_partial = partial_text

            # Check endpoint
            if self.recognizer.is_endpoint(self.asr_stream):
                self.asr_stream.input_finished()
                while self.recognizer.is_ready(self.asr_stream):
                    self.recognizer.decode_stream(self.asr_stream)
                final = self.recognizer.get_result_all(self.asr_stream)
                final_text = final.text.strip() if final.text else ""
                if self._asr_last_partial:
                    print()
                if final_text:
                    log_asr.info(f"识别结果: {final_text}")
                    self._transition_to_processing(final_text)
                self.asr_stream = None
                self._vad_in_speech = False
                return

        if self._vad_speech_ended():
            self._vad_in_speech = False
            if self.config.get("debug", {}).get("show_vad_status", False):
                log_vad.debug("语音结束")

        # Drain VAD
        while not self.vad.empty():
            self.vad.pop()

        # KWS interrupt (full audio)
        keyword = self._check_kws(chunk)
        if keyword:
            if self._vad_in_speech and self.asr_stream:
                self.asr_stream = None  # discard partial
                if self._asr_last_partial:
                    print()
            self._vad_in_speech = False
            log_kws.info(f"检测到唤醒词: {keyword}")
            self._transition_to_listening()

    # -------------------------------------------------------------------
    # State transitions
    # -------------------------------------------------------------------

    def _transition_to_idle(self):
        old = self.state
        self.state = "IDLE"
        self._destroy_kws_stream()
        self.asr_stream = None
        self._vad_in_speech = False
        self._asr_last_partial = ""
        self._kill_prompt()
        self._drain_audio_queue()
        while not self.vad.empty():
            self.vad.pop()
        self.pre_buffer.clear()
        if old != "IDLE":
            log_state.info(f"{old} → IDLE")

    def _transition_to_listening(self):
        old = self.state
        self.state = "LISTENING"
        self._ensure_kws_stream()
        self.asr_stream = None
        self._asr_last_partial = ""
        self._vad_in_speech = False
        self._vad_waiting_silence = True  # Must reach silence before detecting new speech
        self._kill_prompt()
        self._drain_audio_queue()
        self.pre_buffer.clear()
        # VAD internal state was contaminated by the wake-word audio in the
        # IDLE handler.  Play prompt (gives feedback + time for VAD to settle),
        # then wait for silence before accepting new speech.
        self._prompt_proc = self._play_wav_async("kws.wav")
        if old != "LISTENING":
            log_state.info(f"{old} → LISTENING")
        else:
            log_state.info("LISTENING 重置 (打断)")

    def _transition_to_processing(self, user_text):
        old = self.state
        self.state = "PROCESSING"
        self._ensure_kws_stream()      # KWS must be active for interrupt detection
        log_state.info(f"{old} → PROCESSING (query: {user_text})")

        # Clear events + drain stale TTS items for a clean pipeline start
        self.interrupt_event.clear()
        self.tts_done_event.clear()
        while True:
            try:
                self.tts_queue.get_nowait()
            except Empty:
                break

        # Wake up LLM worker
        try:
            self.llm_request_queue.put_nowait(user_text)
        except queue.Full:
            log_llm.warning("LLM 请求队列已满，丢弃旧请求")
            try:
                self.llm_request_queue.get_nowait()
            except Empty:
                pass
            self.llm_request_queue.put_nowait(user_text)

    def _transition_to_active_listening(self):
        old = self.state
        self.state = "ACTIVE_LISTENING"
        self._ensure_kws_stream()      # KWS active for interrupt / explicit wake
        self._active_start = time.time()
        self._vad_in_speech = False
        self.asr_stream = None
        self._asr_last_partial = ""
        # Mute VAD to ignore TTS playback echo from the room.
        # 3.0s covers the last sentence's full decay + reverb tail.
        # Also drain audio queue (backlog of echo chunks from PROCESSING),
        # reset VAD, and clear pre_buffer.
        self._vad_mute_until = time.time() + 3.0
        self._drain_audio_queue()
        while not self.vad.empty():
            self.vad.pop()
        self.pre_buffer.clear()
        log_state.info(f"{old} → ACTIVE_LISTENING (超时: {self.active_timeout}s)")

    # -------------------------------------------------------------------
    # Interrupt pipeline
    # -------------------------------------------------------------------

    def _interrupt_pipeline(self):
        """Signal LLM and TTS threads to stop immediately, wait for cleanup.

        Main thread takes ownership of cleanup: sets interrupt flag, kills
        playback, drains the TTS queue.  LLM worker will still send its
        buffer+sentinel, but TTS player skips them because interrupt_event
        is set.  _transition_to_processing drains again for a clean start.
        """
        self.interrupt_event.set()
        self._kill_playback()
        # Drain any sentences already queued (LLM may add more after this,
        # but TTS player will skip them due to interrupt_event)
        while True:
            try:
                self.tts_queue.get_nowait()
            except Empty:
                break
        # Let TTS player set the done event when it sees the sentinel;
        # we don't wait here — the state machine moves on immediately.

    # -------------------------------------------------------------------
    # Thread 3: LLM Worker
    # -------------------------------------------------------------------

    def _llm_worker(self):
        """Block on llm_request_queue → HTTP stream → segment → tts_queue."""
        log_llm.info("LLM 工作线程启动")

        while self.running.is_set():
            try:
                user_text = self.llm_request_queue.get(timeout=0.5)
            except Empty:
                continue

            messages = [
                {"role": "system", "content": self.llm_system_prompt},
                {"role": "user", "content": user_text},
            ]

            buffer = ""
            print()  # fresh line for LLM output
            print("[LLM] ", end="", flush=True)

            try:
                for token in self.llm_client.chat_stream(
                    messages,
                    temperature=self.llm_temperature,
                    top_p=self.llm_top_p,
                    max_tokens=self.llm_max_tokens,
                    repeat_penalty=self.llm_repeat_penalty,
                    interrupt_event=self.interrupt_event,
                ):
                    if self.interrupt_event.is_set():
                        break

                    print(token, end="", flush=True)
                    buffer += token

                    # Segment on sentence boundaries (regex avoids splitting
                    # e.g. "Qwen3.5" on the period)
                    while True:
                        m = self._SENTENCE_RE.search(buffer)
                        if not m:
                            break
                        end = m.end()
                        sentence = buffer[:end].strip()
                        buffer = buffer[end:]
                        if sentence and len(sentence) > 1:
                            self.tts_queue.put(sentence)

            except Exception as e:
                log_llm.error(f"请求失败: {e}")

            print()  # end LLM output line

            # Always send remaining buffer + sentinel (even if interrupted).
            # TTS player checks interrupt_event and skips synthesis/playback
            # when set, so stale text will be harmlessly drained.
            if buffer.strip():
                self.tts_queue.put(buffer.strip())
            self.tts_queue.put(None)

    # -------------------------------------------------------------------
    # Thread 4: TTS Player
    # -------------------------------------------------------------------

    def _tts_player(self):
        """Block on tts_queue → synthesize → aplay (can be interrupted)."""
        log_tts.info("TTS 播放线程启动")

        while self.running.is_set():
            try:
                text = self.tts_queue.get(timeout=0.5)
            except Empty:
                continue

            # None sentinel = end of a response
            if text is None:
                # Wait for last aplay to finish
                self._wait_playback()
                self.tts_done_event.set()
                continue

            # Check interrupt before synthesis
            if self.interrupt_event.is_set():
                # Drain remaining items until sentinel
                while True:
                    try:
                        item = self.tts_queue.get(timeout=0.1)
                        if item is None:
                            self._wait_playback()
                            self.tts_done_event.set()
                            break
                    except Empty:
                        break
                continue

            # Synthesize
            try:
                t0 = time.perf_counter()
                audio = self._tts_synthesize(text)
                t1 = time.perf_counter()
                dur = len(audio.samples) / audio.sample_rate
                log_tts.info(
                    f"合成: \"{text}\" ({dur:.1f}s, RTF={((t1-t0)/dur):.2f})")
            except Exception as e:
                log_tts.error(f"合成异常: {e}")
                continue

            # Check interrupt again before playback
            if self.interrupt_event.is_set():
                continue

            # Play (track subprocess for interrupt kill)
            self._play_audio(audio)

    # ===================================================================
    # Run / shutdown
    # ===================================================================

    def run(self):
        """Start all threads and block until Ctrl+C."""
        self.threads = [
            threading.Thread(target=self._audio_capture_loop, daemon=True, name="Capture"),
            threading.Thread(target=self._main_loop,          daemon=True, name="Main"),
            threading.Thread(target=self._llm_worker,         daemon=True, name="LLM"),
            threading.Thread(target=self._tts_player,         daemon=True, name="TTS"),
        ]
        for t in self.threads:
            t.start()

        log_state.info("=" * 50)
        log_state.info("系统就绪 — 请说「小飞同学」唤醒我")
        log_state.info("=" * 50)

        # Handle Ctrl+C gracefully
        def on_signal(signum, frame):
            print()
            log_state.info("收到退出信号...")
            self.shutdown()

        signal.signal(signal.SIGINT, on_signal)
        signal.signal(signal.SIGTERM, on_signal)

        # Wait for threads
        try:
            for t in self.threads:
                while t.is_alive():
                    t.join(timeout=0.5)
        except KeyboardInterrupt:
            self.shutdown()

        log_state.info("已退出")

    def shutdown(self):
        """Clean shutdown — stop threads, release resources."""
        self.running.clear()
        self._kill_playback()
        self._kill_prompt()
        self._kill_llm_server()

    def _kill_llm_server(self):
        """Terminate the LLM server subprocess."""
        proc = self._llm_server_proc
        if proc is not None and proc.poll() is None:
            log_llm.info("关闭 LLM 服务进程...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        self._llm_server_proc = None
        # Clean up fake sudo dir
        if hasattr(self, '_fake_sudo_dir') and os.path.exists(self._fake_sudo_dir):
            try:
                os.remove(os.path.join(self._fake_sudo_dir, "sudo"))
                os.rmdir(self._fake_sudo_dir)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="实时语音交互系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
示例:
  python3 voice_interaction.py
  python3 voice_interaction.py --config my_config.yaml
  python3 voice_interaction.py --debug
        """),
    )
    parser.add_argument("--config", "-c",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "config.yaml"),
                        help="配置文件路径 (默认: config.yaml)")
    parser.add_argument("--no-server", action="store_true",
                        help="不自动启动 LLM 服务 (连接已有的外部服务)")
    parser.add_argument("--debug", action="store_true",
                        help="开启调试日志")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        # Quiet down sherpa-onnx internal logging
        for name in logging.root.manager.loggerDict:
            if "sherpa" in name.lower():
                logging.getLogger(name).setLevel(logging.WARNING)

    if not os.path.exists(args.config):
        print(f"错误: 配置文件不存在: {args.config}")
        sys.exit(1)

    app = VoiceInteraction(args.config, auto_start_llm=not args.no_server)
    app.run()


if __name__ == "__main__":
    main()
