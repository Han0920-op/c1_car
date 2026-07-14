#!/usr/bin/env python3
"""
ASR streaming test using sherpa-onnx with ALSA microphone + Silero VAD + RKNN.

The VAD (Voice Activity Detector) precisely segments speech from silence,
solving two common problems:
  1. Audio at beginning/end being lost (deletion)
  2. Repeated output on short utterances

Mimics the behavior of:
  sherpa-onnx-alsa --tokens=~/models/zipformer/tokens.txt \\
                   --encoder=~/models/zipformer/encoder.rknn \\
                   --decoder=~/models/zipformer/decoder.rknn \\
                   --joiner=~/models/zipformer/joiner.rknn \\
                   --provider=rknn --num-threads=-4 \\
                   --decoding-method=greedy_search plughw:0,0

Usage:
  python3 asr_test.py                                       # default params
  python3 asr_test.py --provider cpu                        # CPU fallback
  python3 asr_test.py                                       # default (capture=100%, ALC on)
  python3 asr_test.py --no-mic-boost                        # disable ALC
  python3 asr_test.py --capture-volume 60                   # lower mic volume
"""

import argparse
import collections
import math
import signal
import subprocess
import sys

import sherpa_onnx


# ---------------------------------------------------------------------------
# Mixer helpers (ES8388 / RK3576) — same logic validated in audio_test.py
# ---------------------------------------------------------------------------

def pct_to_db(pct):
    """Convert volume percentage to dB: 100% → 0dB, 50% → -6dB, 25% → -12dB."""
    if pct >= 100:
        return 0.0
    if pct <= 0:
        return -96.0
    return 20.0 * math.log10(pct / 100.0)


def apply_capture_volume(card, pct):
    """Set capture volume from percentage.

    Capture path: Left/Right Channel (preamp, 0..+24dB) + Capture Digital (-96..0dB).
    Preamp stays at max (+24dB) for best SNR; Capture Digital handles attenuation.
    """
    # Preamp at max (24dB) — best signal-to-noise ratio
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "Left Channel", "--", "24.0dB"],
        capture_output=True, check=False)
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "Right Channel", "--", "24.0dB"],
        capture_output=True, check=False)

    # Digital attenuation: 100% → 0dB, 50% → -6dB, 25% → -12dB
    db_val = pct_to_db(pct)
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "Capture Digital", "--", f"{db_val:.1f}dB"],
        capture_output=True, check=False)
    print(f"  Capture volume: {pct}% ({db_val:.1f} dB) + preamp 24 dB")


def enable_alc(card):
    """Enable ALC (Automatic Level Control) for better low-volume pickup."""
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "ALC Capture Function", "Stereo"],
        capture_output=True, check=False)
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "ALC Capture Target", "12"],
        capture_output=True, check=False)
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "ALC Capture Max PGA", "7"],
        capture_output=True, check=False)
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "ALC Capture Attack Time", "5"],
        capture_output=True, check=False)
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "ALC Capture Decay Time", "0"],
        capture_output=True, check=False)
    print("  ALC: enabled (Stereo, target=12, max_pga=7)")


def switch_input_to_mic(card):
    """Switch ES8388 input mux from Line to Mic inputs."""
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "Left Line Mux", "MicL"],
        capture_output=True, check=False)
    subprocess.run(
        ["amixer", "-c", str(card), "sset", "Right Line Mux", "MicR"],
        capture_output=True, check=False)
    print("  Input mux: MicL / MicR")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ASR streaming test (sherpa-onnx + ALSA + VAD + RKNN)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 asr_test.py
  python3 asr_test.py --provider cpu
  python3 asr_test.py --no-mic-boost
        """,
    )

    # ---- Model files ----
    parser.add_argument("--tokens",
                        default="/home/iflytek/models/zipformer/tokens.txt")
    parser.add_argument("--encoder",
                        default="/home/iflytek/models/zipformer/encoder.rknn")
    parser.add_argument("--decoder",
                        default="/home/iflytek/models/zipformer/decoder.rknn")
    parser.add_argument("--joiner",
                        default="/home/iflytek/models/zipformer/joiner.rknn")
    parser.add_argument("--vad-model",
                        default="/home/iflytek/models/vad/silero_vad.onnx")

    # ---- Device ----
    parser.add_argument("-D", "--device", default="plughw:0,0",
                        help="ALSA PCM device (default: plughw:0,0)")

    # ---- Provider & performance ----
    parser.add_argument("--provider", default="rknn",
                        choices=["cpu", "rknn"],
                        help="ONNX execution provider (default: rknn)")
    parser.add_argument("--num-threads", type=int, default=4)
    parser.add_argument("--sample-rate", type=int, default=16000)

    # ---- Decoding ----
    parser.add_argument("--decoding-method", default="greedy_search",
                        choices=["greedy_search", "modified_beam_search"])
    parser.add_argument("--max-active-paths", type=int, default=4)
    parser.add_argument("--blank-penalty", type=float, default=0.5,
                        help="Penalty on blank symbol (higher = fewer deletions). "
                             "0.3-0.5 helps avoid losing beginning/end of speech. (default: 0.5)")

    # ---- VAD ----
    parser.add_argument("--vad-threshold", type=float, default=0.5,
                        help="VAD speech probability threshold (default: 0.5)")
    parser.add_argument("--vad-min-silence", type=float, default=0.5,
                        help="VAD min silence to end speech segment, seconds (default: 0.5)")
    parser.add_argument("--vad-min-speech", type=float, default=0.25,
                        help="VAD min speech duration, seconds (default: 0.25)")
    parser.add_argument("--vad-max-speech", type=float, default=20.0,
                        help="VAD max speech duration before forced cutoff, seconds (default: 20.0)")

    # ---- Feature extraction ----
    parser.add_argument("--feature-dim", type=int, default=80)
    parser.add_argument("--low-freq", type=float, default=20.0)
    parser.add_argument("--high-freq", type=float, default=-400.0)

    # ---- Capture volume & mic boost ----
    parser.add_argument("--card", type=int, default=0)
    parser.add_argument("--capture-volume", type=int, default=100,
                        help="Set mic capture volume 0-100%% (default: 100)")
    parser.add_argument("--no-mic-boost", action="store_true",
                        help="Disable ALC (automatic level control) + Mic input switching")

    # ---- Debug ----
    parser.add_argument("--debug", action="store_true")

    # ---- Pre-speech buffer ----
    parser.add_argument("--pre-speech-buffer", type=float, default=0.5,
                        help="Seconds of audio to buffer before VAD triggers. "
                             "Prevents losing the first word. (default: 0.5)")

    # ---- Read chunk ----
    parser.add_argument("--chunk-size", type=int, default=4000,
                        help="Samples per ALSA read (default: 4000, ~250ms @ 16kHz)")

    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # Audio mixer setup (on by default for best recognition)
    # -----------------------------------------------------------------------
    print("Audio mixer setup...")
    pct = max(0, min(100, args.capture_volume))
    apply_capture_volume(args.card, pct)
    if not args.no_mic_boost:
        enable_alc(args.card)
        switch_input_to_mic(args.card)
    else:
        print("  Mic boost: disabled")

    # -----------------------------------------------------------------------
    # Build VAD
    # -----------------------------------------------------------------------
    print("Initializing VAD...")
    silero_vad_config = sherpa_onnx.SileroVadModelConfig(
        model=args.vad_model,
        threshold=args.vad_threshold,
        min_silence_duration=args.vad_min_silence,
        min_speech_duration=args.vad_min_speech,
        max_speech_duration=args.vad_max_speech,
    )
    # VAD always runs on CPU — the Silero VAD model is ONNX format (not RKNN),
    # is tiny (~600 KB), and runs faster on CPU than the overhead of NPU dispatch.
    vad_config = sherpa_onnx.VadModelConfig(
        silero_vad=silero_vad_config,
        sample_rate=args.sample_rate,
        num_threads=args.num_threads,
        provider="cpu",
        debug=args.debug,
    )
    vad = sherpa_onnx.VoiceActivityDetector(
        config=vad_config,
        buffer_size_in_seconds=args.vad_max_speech + 5,
    )
    print(f"  model:    {args.vad_model}")
    print(f"  threshold:  {args.vad_threshold}")
    print(f"  min_silence: {args.vad_min_silence}s")
    print(f"  min_speech:  {args.vad_min_speech}s")
    print(f"  max_speech:  {args.vad_max_speech}s")

    # -----------------------------------------------------------------------
    # Build recognizer
    # -----------------------------------------------------------------------
    print("\nInitializing recognizer...")
    print(f"  tokens:   {args.tokens}")
    print(f"  encoder:  {args.encoder}")
    print(f"  decoder:  {args.decoder}")
    print(f"  joiner:   {args.joiner}")
    print(f"  provider: {args.provider}")
    print(f"  threads:  {args.num_threads}")
    print(f"  method:   {args.decoding_method}")
    print(f"  blank_penalty: {args.blank_penalty}")

    recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=args.tokens,
        encoder=args.encoder,
        decoder=args.decoder,
        joiner=args.joiner,
        provider=args.provider,
        num_threads=args.num_threads,
        sample_rate=args.sample_rate,
        feature_dim=args.feature_dim,
        low_freq=args.low_freq,
        high_freq=args.high_freq,
        decoding_method=args.decoding_method,
        max_active_paths=args.max_active_paths,
        blank_penalty=args.blank_penalty,
        debug=args.debug,
    )

    # -----------------------------------------------------------------------
    # Open ALSA device
    # -----------------------------------------------------------------------
    print(f"\nOpening ALSA device: {args.device}")
    alsa = sherpa_onnx.Alsa(args.device)
    actual_rate = alsa.actual_sample_rate
    expected_rate = alsa.expected_sample_rate
    print(f"  expected sample rate: {expected_rate}")
    print(f"  actual sample rate:   {actual_rate}")
    sample_rate = actual_rate if actual_rate > 0 else args.sample_rate

    # -----------------------------------------------------------------------
    # Streaming recognition loop (VAD-driven)
    #
    # Architecture:
    #   ALSA → VAD → [speech segment] → Recognizer → final text
    #                                    ↘ streaming decode → partial text
    #
    # VAD handles speech/non-speech segmentation precisely, avoiding:
    #   - Lost audio at utterance boundaries
    #   - False endpoints from silence-based heuristics
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # Pre-speech buffer — a rolling window of recent audio samples.
    #
    # VAD needs ~0.3-0.5s to confirm speech has started. By the time
    # is_speech_detected() returns True, those first frames have already been
    # consumed.  We keep the last N samples so we can prepend them to the
    # recognizer when speech begins.  Using deque with maxlen instead of
    # sherpa_onnx.CircularBuffer to avoid overflow warnings on long silence.
    pre_speech_samples = int(args.pre_speech_buffer * args.sample_rate)
    pre_num_chunks = max(1, pre_speech_samples // args.chunk_size)
    pre_buf = collections.deque(maxlen=pre_num_chunks)

    print(f"  pre-speech buffer: {args.pre_speech_buffer}s "
          f"({pre_num_chunks} chunks × {args.chunk_size} samples)")
    print(f"\nListening... (Ctrl+C to stop)\n")

    running = True

    def on_sigint(signum, frame):
        nonlocal running
        running = False
        print("\n\nStopping...")

    signal.signal(signal.SIGINT, on_sigint)

    stream = recognizer.create_stream()
    in_speech = False
    last_partial = ""

    try:
        while running:
            samples = alsa.read(args.chunk_size)
            if not samples:
                continue

            # Always keep a rolling window of recent audio (VAD needs it too)
            vad.accept_waveform(samples)
            pre_buf.append(samples)

            if vad.is_speech_detected():
                if not in_speech:
                    # Speech just started — replay buffered chunks so the
                    # recognizer doesn't miss the first word
                    in_speech = True
                    stream = recognizer.create_stream()
                    for chunk in pre_buf:
                        stream.accept_waveform(sample_rate, chunk)
                        while recognizer.is_ready(stream):
                            recognizer.decode_stream(stream)

                # Feed current chunk for real-time partial decode
                stream.accept_waveform(sample_rate, samples)
                while recognizer.is_ready(stream):
                    recognizer.decode_stream(stream)
                partial = recognizer.get_result_all(stream)
                partial_text = partial.text.strip() if partial.text else ""
                if partial_text and partial_text != last_partial:
                    pad = max(0, len(last_partial) - len(partial_text))
                    print(f"\r[{partial_text}]{' ' * pad}", end="", flush=True)
                    last_partial = partial_text

            elif in_speech:
                # Speech segment ended
                in_speech = False
                pre_buf.clear()

                stream.input_finished()
                while recognizer.is_ready(stream):
                    recognizer.decode_stream(stream)

                result = recognizer.get_result_all(stream)
                result_text = result.text.strip() if result.text else ""

                if result_text:
                    print(f"\r{' ' * (max(0, len(last_partial)) + 4)}", end="", flush=True)
                    print(f"\r[Final] {result_text}")
                last_partial = ""

            # Drain completed VAD segments
            while not vad.empty():
                vad.pop()

    except KeyboardInterrupt:
        pass

    # -----------------------------------------------------------------------
    # Cleanup — flush any remaining speech
    # -----------------------------------------------------------------------
    if in_speech:
        stream.input_finished()
        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)
        result = recognizer.get_result_all(stream)
        result_text = result.text.strip() if result.text else ""
        if result_text:
            print(f"\r[Final] {result_text}")

    print("Done.")


if __name__ == "__main__":
    main()
