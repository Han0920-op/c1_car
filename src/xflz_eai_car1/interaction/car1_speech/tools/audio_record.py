#!/usr/bin/env python3
"""
Standalone audio recording tool using ALSA arecord.
No ROS2 dependency — tests the ES8388 mic hardware directly.

Usage:
  python3 audio_record.py               # record 5s, save to record.wav
  python3 audio_record.py -d 10 -o test.wav  # 10s recording
  python3 audio_record.py -l            # list audio devices
  python3 audio_record.py -D hw:0,0 -r 16000 -f S16_LE -c 1 -d 3
"""

import argparse
import subprocess
import sys
import os
import signal


def list_devices():
    """List all capture devices via arecord -l."""
    print("Available capture devices:")
    print("-" * 60)
    try:
        subprocess.run(["arecord", "-l"], check=False)
    except FileNotFoundError:
        print("Error: arecord not found. Install alsa-utils.")
        sys.exit(1)
    print("-" * 60)
    print("\nPCM device names (for -D option):")
    try:
        subprocess.run(["arecord", "-L"], check=False)
    except FileNotFoundError:
        pass


def record(args):
    """Record audio using arecord."""
    cmd = ["arecord"]

    if args.quiet:
        cmd.append("-q")
    else:
        cmd.append("-V")
        cmd.append("mono" if args.channels == 1 else "stereo")

    cmd.extend([
        "-D", args.device,
        "-c", str(args.channels),
        "-f", args.format,
        "-r", str(args.rate),
        "-d", str(args.duration),
        "-t", "wav",
        args.output,
    ])

    print(f"Recording: device={args.device}, rate={args.rate}, "
          f"fmt={args.format}, channels={args.channels}, "
          f"duration={args.duration}s")
    print(f"Saving to: {args.output}")
    print("Press Ctrl+C to stop early.\n")

    proc = subprocess.Popen(cmd)
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nRecording stopped by user.")
        proc.send_signal(signal.SIGINT)
        proc.wait()

    if proc.returncode == 0 and os.path.exists(args.output):
        size_kb = os.path.getsize(args.output) / 1024
        print(f"Done: {args.output} ({size_kb:.1f} KB)")
    else:
        print(f"Recording failed (exit code {proc.returncode})")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ALSA audio recorder (arecord wrapper)")
    parser.add_argument("-l", "--list", action="store_true",
                        help="List capture devices and exit")
    parser.add_argument("-D", "--device", default="default",
                        help="PCM device name (default: 'default')")
    parser.add_argument("-r", "--rate", type=int, default=44100,
                        help="Sample rate in Hz (default: 44100)")
    parser.add_argument("-f", "--format", default="S16_LE",
                        help="Sample format (default: S16_LE)")
    parser.add_argument("-c", "--channels", type=int, default=1,
                        help="Number of channels (default: 1)")
    parser.add_argument("-d", "--duration", type=int, default=5,
                        help="Recording duration in seconds (default: 5)")
    parser.add_argument("-o", "--output", default="record.wav",
                        help="Output WAV file (default: record.wav)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress VU meter output")

    args = parser.parse_args()

    if args.list:
        list_devices()
        return

    record(args)


if __name__ == "__main__":
    main()
