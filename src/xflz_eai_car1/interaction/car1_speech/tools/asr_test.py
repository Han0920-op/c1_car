#!/usr/bin/env python3
"""
ASR streaming test using sherpa-onnx with ALSA microphone + RKNN.

Uses sherpa-onnx built-in endpoint detection (same as RK3588 version).
This preserves the recognizer's streaming context across the entire session,
which is critical for Zipformer accuracy.

Mimics the behavior of:
  sherpa-onnx-alsa --tokens=~/models/zipformer/tokens.txt \\
                   --encoder=~/models/zipformer/encoder.rknn \\
                   --decoder=~/models/zipformer/decoder.rknn \\
                   --joiner=~/models/zipformer/joiner.rknn \\
                   --provider=rknn --num-threads=1 \\
                   --decoding-method=greedy_search plughw:0,0

Usage:
  python3 asr_test.py                                       # default params
  python3 asr_test.py --provider cpu                        # CPU fallback
  python3 asr_test.py --no-mic-boost                        # disable ALC
  python3 asr_test.py --capture-volume 60                   # lower mic volume
"""

import argparse
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

    # ---- Device ----
    parser.add_argument("-D", "--device", default="plughw:0,0",
                        help="ALSA PCM device (default: plughw:0,0)")

    # ---- Provider & performance ----
    parser.add_argument("--provider", default="rknn",
                        choices=["cpu", "rknn"],
                        help="ONNX execution provider (default: rknn)")
    parser.add_argument("--num-threads", type=int, default=1,
                        help="For RKNN, this is NPU core mask (default: 1 = auto)")
    parser.add_argument("--sample-rate", type=int, default=16000)

    # ---- Decoding ----
    parser.add_argument("--decoding-method", default="greedy_search",
                        choices=["greedy_search", "modified_beam_search"])
    parser.add_argument("--blank-penalty", type=float, default=0.0,
                        help="Penalty on blank symbol (default: 0.0, same as RK3588)")

    # ---- Endpoint detection (built-in, replaces external VAD) ----
    parser.add_argument("--rule1-min-trailing-silence", type=float, default=2.4,
                        help="Rule 1: min trailing silence for endpoint (default: 2.4s)")
    parser.add_argument("--rule2-min-trailing-silence", type=float, default=1.2,
                        help="Rule 2: min trailing silence after non-empty result (default: 1.2s)")
    parser.add_argument("--rule3-min-utterance-length", type=float, default=300.0,
                        help="Rule 3: min utterance length to trigger endpoint (default: 300s = effectively disabled)")

    # ---- Feature extraction ----
    parser.add_argument("--feature-dim", type=int, default=80)

    # ---- Hotwords ----
    parser.add_argument("--hotwords-file", type=str, default="",
                        help="Path to hotwords file for biasing")
    parser.add_argument("--hotwords-score", type=float, default=1.5)

    # ---- Capture volume & mic boost ----
    parser.add_argument("--card", type=int, default=0)
    parser.add_argument("--capture-volume", type=int, default=100,
                        help="Set mic capture volume 0-100%% (default: 100)")
    parser.add_argument("--no-mic-boost", action="store_true",
                        help="Disable ALC (automatic level control) + Mic input switching")

    # ---- Debug ----
    parser.add_argument("--debug", action="store_true")

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
    # Build recognizer (with built-in endpoint detection, matches RK3588 config)
    # -----------------------------------------------------------------------
    print("Initializing recognizer...")
    print(f"  tokens:   {args.tokens}")
    print(f"  encoder:  {args.encoder}")
    print(f"  decoder:  {args.decoder}")
    print(f"  joiner:   {args.joiner}")
    print(f"  provider: {args.provider}")
    print(f"  threads:  {args.num_threads}")
    print(f"  method:   {args.decoding_method}")
    print(f"  blank_penalty: {args.blank_penalty}")
    print(f"  rule1 silence: {args.rule1_min_trailing_silence}s")
    print(f"  rule2 silence: {args.rule2_min_trailing_silence}s")

    recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=args.tokens,
        encoder=args.encoder,
        decoder=args.decoder,
        joiner=args.joiner,
        num_threads=args.num_threads,
        sample_rate=args.sample_rate,
        feature_dim=args.feature_dim,
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=args.rule1_min_trailing_silence,
        rule2_min_trailing_silence=args.rule2_min_trailing_silence,
        rule3_min_utterance_length=args.rule3_min_utterance_length,
        decoding_method=args.decoding_method,
        provider=args.provider,
        hotwords_file=args.hotwords_file,
        hotwords_score=args.hotwords_score,
        blank_penalty=args.blank_penalty,
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
    # sherpa_onnx.Alsa internally resamples to 16kHz — always feed the
    # recognizer at the model's rate, regardless of hardware capture rate.
    sample_rate = args.sample_rate

    # -----------------------------------------------------------------------
    # Streaming recognition loop
    #
    # Architecture (same as RK3588 offline_stt.py):
    #   ALSA → Recognizer (streaming decode + built-in endpoint detection)
    #        → is_endpoint() → reset stream, keep going
    #
    # A SINGLE stream is used across the whole session (only reset on endpoint,
    # not recreated).  This preserves the recognizer's temporal context, which
    # is critical for Zipformer accuracy.
    # -----------------------------------------------------------------------
    samples_per_read = int(0.1 * sample_rate)  # 100 ms per read (same as RK3588)
    print(f"\nsamples per read: {samples_per_read} (~100ms)")
    print(f"\nStarted! Please speak (Ctrl+C to stop)\n")

    running = True

    def on_sigint(signum, frame):
        nonlocal running
        running = False
        print("\n\nStopping...")

    signal.signal(signal.SIGINT, on_sigint)

    stream = recognizer.create_stream()
    last_result = ""
    segment_id = 0

    try:
        while running:
            samples = alsa.read(samples_per_read)  # blocking read
            if not samples:
                continue

            stream.accept_waveform(sample_rate, samples)
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)

            is_endpoint = recognizer.is_endpoint(stream)
            result = recognizer.get_result(stream)

            # Live partial update — overwrite current line
            if result and (last_result != result):
                last_result = result
                print(f"\r{segment_id}:{result}", end="", flush=True)

            if is_endpoint:
                # Always emit a newline on endpoint so the next segment
                # starts on a fresh line. If no text was produced this
                # segment, still print a marker so we can see endpoint
                # firing in the logs.
                final = result if result else last_result
                if final:
                    print(f"\r{segment_id}:{final}", flush=True)
                    segment_id += 1
                else:
                    print(f"\r[endpoint, no text]", flush=True)
                last_result = ""
                recognizer.reset(stream)

    except KeyboardInterrupt:
        pass

    if last_result:
        sys.stdout.write("\n")
        sys.stdout.flush()
    print("Done.")


if __name__ == "__main__":
    main()
