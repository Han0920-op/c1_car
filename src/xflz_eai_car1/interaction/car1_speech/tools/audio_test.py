#!/usr/bin/env python3
"""
ES8388 audio loopback test tool — record + play simultaneously, or record/play separately.

Modes:
  loopback (default):  record and play at the same time (arecord | aplay pipeline).
                        Optionally save the recording to a file.
  record:              record only, save to a WAV file.
  play:                play an existing WAV file.

Default parameters match ES8388 on RK3576:
  Card:    0 (rockchip-es8388)
  Device:  hw:0,0
  Rate:    16000 Hz
  Format:  S16_LE
  Channels: 2 (stereo — use -c 1 for mono if needed)

Mixer volume is NOT changed unless you pass --playback-volume / --capture-volume.
Volume is set via dB values (20*log10), so 50% = -6dB, 25% = -12dB, etc.
Use --list-mixer to inspect current mixer state.

Tuning tips:
  --playback-volume 50 --capture-volume 50       # half volume (-6dB)
  --playback-volume 100 --capture-volume 100     # max (0dB)
  --capture-volume 38                            # capture ≈ +9dB (19*log10)
  --list-mixer                                   # inspect all mixer controls

Usage:
  python3 audio_test.py                              # loopback (no save)
  python3 audio_test.py -o rec.wav                   # loopback + save
  python3 audio_test.py --mode record -o rec.wav     # record only
  python3 audio_test.py --mode play test.wav         # play only
  python3 audio_test.py -l                           # list PCM devices
  python3 audio_test.py --list-mixer                 # list mixer controls
  python3 audio_test.py --playback-volume 100        # loopback with max volume
"""

import argparse
import math
import os
import re
import signal
import subprocess
import sys


# ---------------------------------------------------------------------------
# Mixer helpers
# ---------------------------------------------------------------------------

def run_amixer(card, args, check=True):
    """Run amixer on the given card, return stdout lines."""
    cmd = ["amixer", "-c", str(card)] + args
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        print(f"amixer error: {p.stderr.strip()}")
        sys.exit(1)
    return p.stdout.splitlines()


def pct_to_db(pct):
    """Convert volume percentage to dB: 100% → 0dB, 50% → -6dB, 25% → -12dB."""
    if pct >= 100:
        return 0.0
    if pct <= 0:
        return -96.0
    return 20.0 * math.log10(pct / 100.0)


def set_mixer_volume(card, controls, pct):
    """Set mixer controls using dB values computed from percentage."""
    db_val = pct_to_db(pct)
    for ctl in controls:
        subprocess.run(
            ["amixer", "-c", str(card), "sset", ctl, "--", f"{db_val:.1f}dB"],
            capture_output=True, check=False)


def apply_playback_volume(card, pct):
    """Set Output 1/2 and PCM to the given percentage volume."""
    db_val = pct_to_db(pct)
    for ctl in ["Output 1", "Output 2", "PCM"]:
        subprocess.run(
            ["amixer", "-c", str(card), "sset", ctl, "--", f"{db_val:.1f}dB"],
            capture_output=True, check=False)


def apply_capture_volume(card, pct):
    """
    Set capture volume from percentage.

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


def get_mixer_volume(card, control):
    """Get current volume as integer percentage (first number found)."""
    lines = run_amixer(card, ["sget", control])
    for line in lines:
        m = re.search(r'\[(\d+)%\]', line)
        if m:
            return int(m.group(1))
    return None


def list_mixer_controls(card):
    """Print all mixer controls and their current values."""
    lines = run_amixer(card, ["scontents"])
    print(f"Mixer controls for card {card}:\n")
    for line in lines:
        print(line)


# ---------------------------------------------------------------------------
# PCM device listing
# ---------------------------------------------------------------------------

def list_devices():
    print("=== Capture Devices ===")
    try:
        subprocess.run(["arecord", "-l"], check=False)
    except FileNotFoundError:
        print("Error: arecord not found. Install alsa-utils.")
        sys.exit(1)

    print("\n=== Playback Devices ===")
    try:
        subprocess.run(["aplay", "-l"], check=False)
    except FileNotFoundError:
        pass

    print("\nPCM device names (for -D option):")
    try:
        subprocess.run(["arecord", "-L"], check=False)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------

def build_arecord_cmd(args):
    """Build the arecord command for record / loopback modes."""
    rec_dev = args.rec_device or args.device
    cmd = ["arecord", "-q"]
    cmd.extend(["-D", rec_dev])
    cmd.extend(["-f", args.format])
    cmd.extend(["-r", str(args.rate)])
    cmd.extend(["-c", str(args.channels)])
    cmd.extend(["-t", "wav"])
    if args.period_size:
        cmd.extend(["--period-size", str(args.period_size)])
    if args.buffer_size:
        cmd.extend(["--buffer-size", str(args.buffer_size)])
    if args.duration > 0:
        cmd.extend(["-d", str(args.duration)])
    return cmd


def build_aplay_cmd(args):
    """Build the aplay command for playback / loopback modes (reads from stdin)."""
    play_dev = args.playback_device or args.device
    cmd = ["aplay", "-q"]
    cmd.extend(["-D", play_dev])
    cmd.extend(["-f", args.format])
    cmd.extend(["-r", str(args.rate)])
    cmd.extend(["-c", str(args.channels)])
    cmd.extend(["-t", "wav"])
    if args.period_size:
        cmd.extend(["--period-size", str(args.period_size)])
    if args.buffer_size:
        cmd.extend(["--buffer-size", str(args.buffer_size)])
    cmd.append("-")
    return cmd


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def loopback_mode(args):
    """Record and play simultaneously via pipe (arecord | aplay)."""
    arecord_cmd = build_arecord_cmd(args)
    arecord_cmd.append("-")          # stdout, WAV format

    aplay_cmd = build_aplay_cmd(args)

    rec_dev = args.rec_device or args.device
    play_dev = args.playback_device or args.device

    if not args.quiet:
        print(f"Loopback: rec={rec_dev}  play={play_dev}")
        print(f"  rate={args.rate}, fmt={args.format}, channels={args.channels}")
        if args.period_size:
            print(f"  period_size={args.period_size}")
        if args.buffer_size:
            print(f"  buffer_size={args.buffer_size}")
        if args.duration > 0:
            print(f"  duration={args.duration}s")
        else:
            print(f"  duration=unlimited (Ctrl+C to stop)")
        if args.output:
            print(f"  saving to: {args.output}")
        print()

    arecord_proc = subprocess.Popen(
        arecord_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    aplay_proc = subprocess.Popen(
        aplay_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    out_fh = None
    if args.output:
        out_fh = open(args.output, "wb")

    try:
        chunk = (args.period_size or 1024) * args.channels * 2
        while True:
            data = arecord_proc.stdout.read(chunk)
            if not data:
                break
            if out_fh:
                out_fh.write(data)
            try:
                aplay_proc.stdin.write(data)
                aplay_proc.stdin.flush()
            except BrokenPipeError:
                break
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nStopped by user.")

    if out_fh:
        out_fh.close()

    arecord_proc.stdout.close()
    try:
        arecord_proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        arecord_proc.kill()
        arecord_proc.wait()

    if aplay_proc.poll() is None:
        aplay_proc.stdin.close()
        try:
            aplay_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            aplay_proc.kill()
            aplay_proc.wait()

    if not args.quiet:
        rc = arecord_proc.returncode
        if rc == 0 or rc == -signal.SIGINT:
            if args.output and os.path.exists(args.output):
                size_kb = os.path.getsize(args.output) / 1024
                print(f"Done: {args.output} ({size_kb:.1f} KB)")
            else:
                print("Done.")
        else:
            print(f"Recording failed (exit code {rc})")
            sys.exit(1)


def record_only(args):
    """Record only, save to file."""
    cmd = build_arecord_cmd(args)
    rec_dev = args.rec_device or args.device

    if not args.quiet:
        cmd.remove("-q")  # show VU meter
        print(f"Recording: device={rec_dev}, rate={args.rate}, "
              f"fmt={args.format}, channels={args.channels}")
        if args.duration > 0:
            print(f"  duration={args.duration}s")
        print(f"  saving to: {args.output}")
        print("Press Ctrl+C to stop early.\n")

    cmd.append(args.output)

    proc = subprocess.Popen(cmd)
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nRecording stopped by user.")
        proc.send_signal(signal.SIGINT)
        proc.wait()

    if proc.returncode == 0 or proc.returncode == -signal.SIGINT:
        if os.path.exists(args.output):
            size_kb = os.path.getsize(args.output) / 1024
            print(f"Done: {args.output} ({size_kb:.1f} KB)")
    else:
        print(f"Recording failed (exit code {proc.returncode})")
        sys.exit(1)


def play_only(args):
    """Play a WAV file."""
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    play_dev = args.playback_device or args.device
    cmd = ["aplay"]
    if args.quiet:
        cmd.append("-q")
    cmd.extend(["-D", play_dev])
    cmd.append(args.file)

    if not args.quiet:
        print(f"Playing: {args.file}")
        print(f"  device={play_dev}")

    proc = subprocess.Popen(cmd)
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nPlayback stopped by user.")
        proc.terminate()
        proc.wait()
        return

    if proc.returncode != 0:
        print(f"Playback failed (exit code {proc.returncode})")
        sys.exit(1)
    if not args.quiet:
        print("Done.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ES8388 audio test tool (loopback / record / play)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 audio_test.py                              # loopback (no save)
  python3 audio_test.py --playback-volume 100        # loopback, max volume
  python3 audio_test.py --capture-volume 38          # loopback, +9dB capture
  python3 audio_test.py -o rec.wav                   # loopback + save
  python3 audio_test.py --mode record -o rec.wav     # record only
  python3 audio_test.py --mode play test.wav         # play only
  python3 audio_test.py -l                           # list PCM devices
  python3 audio_test.py --list-mixer                 # list mixer controls
        """,
    )

    # ---- Mode ----
    parser.add_argument(
        "--mode", choices=["loopback", "record", "play"], default="loopback",
        help="loopback (default) | record | play")

    # ---- Card & devices ----
    parser.add_argument("--card", type=int, default=0,
                        help="ALSA card number for mixer controls (default: 0)")
    parser.add_argument("-D", "--device", default="hw:0,0",
                        help="Default PCM device for both record and playback (default: hw:0,0)")
    parser.add_argument("--rec-device", default=None,
                        help="Record PCM device (overrides --device for recording)")
    parser.add_argument("--playback-device", default=None,
                        help="Playback PCM device (overrides --device for playback)")

    # ---- Audio format ----
    parser.add_argument("-r", "--rate", type=int, default=16000,
                        help="Sample rate in Hz (default: 16000)")
    parser.add_argument("-f", "--format", default="S16_LE",
                        help="Sample format (default: S16_LE)")
    parser.add_argument("-c", "--channels", type=int, default=2,
                        help="Number of channels (default: 2, stereo)")

    # ---- Duration ----
    parser.add_argument("-d", "--duration", type=int, default=0,
                        help="Duration in seconds (0 = unlimited, Ctrl+C to stop)")

    # ---- Output ----
    parser.add_argument("-o", "--output", default="",
                        help="Output WAV file (record / loopback modes)")

    # ---- Playback file ----
    parser.add_argument("file", nargs="?", default=None,
                        help="WAV file to play (play mode only)")

    # ---- Buffer / latency tuning ----
    parser.add_argument("--period-size", type=int, default=None,
                        help="ALSA period size in frames (smaller = lower latency, may cause xruns)")
    parser.add_argument("--buffer-size", type=int, default=None,
                        help="ALSA buffer size in frames (larger = more stable, higher latency)")

    # ---- Mixer volume ----
    parser.add_argument("--playback-volume", type=int, default=None,
                        help="Set playback volume 0-100%% (amixer: Output 1, Output 2, PCM)")
    parser.add_argument("--capture-volume", type=int, default=None,
                        help="Set capture volume 0-100%% (amixer: Left Channel, Right Channel, Capture Digital)")

    # ---- Listing ----
    parser.add_argument("-l", "--list", action="store_true",
                        help="List PCM devices and exit")
    parser.add_argument("--list-mixer", action="store_true",
                        help="List mixer controls for --card and exit")

    # ---- Misc ----
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress output messages")

    args = parser.parse_args()

    # ---- Listing actions (exit after) ----
    if args.list:
        list_devices()
        return
    if args.list_mixer:
        list_mixer_controls(args.card)
        return

    # ---- Apply mixer volume (only when explicitly requested) ----
    if args.playback_volume is not None:
        pct = max(0, min(100, args.playback_volume))
        db_val = pct_to_db(pct)
        if not args.quiet:
            print(f"[mixer] playback {pct}%  →  {db_val:.1f} dB")
        apply_playback_volume(args.card, pct)

    if args.capture_volume is not None:
        pct = max(0, min(100, args.capture_volume))
        db_val = pct_to_db(pct)
        if not args.quiet:
            print(f"[mixer] capture {pct}%  →  {db_val:.1f} dB  (preamp +24dB + digital {db_val:.1f}dB)")
        apply_capture_volume(args.card, pct)

    # ---- Run selected mode ----
    if args.mode == "play":
        if args.file is None:
            parser.print_help()
            print("\nError: Please specify a WAV file to play.")
            sys.exit(1)
        play_only(args)
    elif args.mode == "record":
        if not args.output:
            args.output = "record.wav"
        record_only(args)
    elif args.mode == "loopback":
        loopback_mode(args)


if __name__ == "__main__":
    main()
