#!/usr/bin/env python3
"""
Standalone audio playback tool using ALSA aplay.
No ROS2 dependency — tests the ES8388 speaker/headphone hardware directly.

Usage:
  python3 audio_play.py record.wav        # play a WAV file
  python3 audio_play.py -D hw:0,0 test.wav
  python3 audio_play.py -l                # list playback devices
"""

import argparse
import subprocess
import sys
import os
import time


def list_devices():
    """List all playback devices via aplay -l."""
    print("Available playback devices:")
    print("-" * 60)
    try:
        subprocess.run(["aplay", "-l"], check=False)
    except FileNotFoundError:
        print("Error: aplay not found. Install alsa-utils.")
        sys.exit(1)
    print("-" * 60)
    print("\nPCM device names (for -D option):")
    try:
        subprocess.run(["aplay", "-L"], check=False)
    except FileNotFoundError:
        pass


def get_wav_duration(filepath):
    """Estimate WAV duration in seconds from the header."""
    import struct
    try:
        with open(filepath, "rb") as f:
            header = f.read(44)
            if len(header) < 44 or header[:4] != b"RIFF":
                return None
            sample_rate = struct.unpack_from("<I", header, 24)[0]
            channels = struct.unpack_from("<H", header, 22)[0]
            bits = struct.unpack_from("<H", header, 34)[0]
            data_size = struct.unpack_from("<I", header, 40)[0]
            bytes_per_sample = (bits // 8) * channels
            if bytes_per_sample == 0:
                return None
            return data_size / (sample_rate * bytes_per_sample)
    except OSError:
        return None


def play(args):
    """Play audio file using aplay."""
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    duration = get_wav_duration(args.file)
    cmd = ["aplay", "-D", args.device]
    if args.quiet:
        cmd.append("-q")
    cmd.append(args.file)

    if duration:
        print(f"Playing: {args.file} ({duration:.1f}s)")
    else:
        print(f"Playing: {args.file}")

    print(f"Device: {args.device}")
    if args.loop > 0:
        print(f"Loop: {args.loop} times")

    for i in range(max(args.loop, 1)):
        if args.loop > 0:
            print(f"\n--- Loop {i + 1}/{args.loop} ---")
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

    print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="ALSA audio player (aplay wrapper)")
    parser.add_argument("-l", "--list", action="store_true",
                        help="List playback devices and exit")
    parser.add_argument("-D", "--device", default="default",
                        help="PCM device name (default: 'default')")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress verbose output")
    parser.add_argument("--loop", type=int, default=0,
                        help="Loop playback N times (0 = play once)")
    parser.add_argument("file", nargs="?", default=None,
                        help="WAV file to play")

    args = parser.parse_args()

    if args.list:
        list_devices()
        return

    if args.file is None:
        parser.print_help()
        print("\nError: Please specify a WAV file to play.")
        sys.exit(1)

    play(args)


if __name__ == "__main__":
    main()
