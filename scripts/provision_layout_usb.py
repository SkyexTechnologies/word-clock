#!/usr/bin/env python3
"""Write a word-clock LED layout and device info to its reserved flash sector over USB serial."""

import argparse
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

from provision_layout import DeviceLayout, load_layout

NUM_WORDS = 37
LEDS_PER_WORD = 12
FLASH_SECTOR_SIZE = 4096
FLASH_OFFSET = 0x3FA000  # Physical offset for memory-mapped sector 1018 (0x405FA000).
CONFIG_MAGIC = 0x574C4B31  # "WLK1"
CONFIG_VERSION = 1
# Indication bits, as FEATURE_* in components/wordclock_layout/wordclock_layout.h.
FEATURE_IT_IS = 1 << 0
FEATURE_MINUTES = 1 << 1
FEATURE_WEEKDAYS = 1 << 2
BLOB_SIZE = 456  # sizeof(LayoutBlob) in the firmware
DEFAULT_LAYOUT = Path(__file__).resolve().parents[1] / "provisioning" / "default-layout.json"


def build_sector_image(layout: DeviceLayout) -> bytes:
    """Build one erased flash sector containing the firmware's LayoutBlob."""
    expected_entries = NUM_WORDS * LEDS_PER_WORD
    if len(layout.flat) != expected_entries:
        raise ValueError(f"Expected {expected_entries} layout entries, got {len(layout.flat)}")
    if any(value < -1 or value >= 121 for value in layout.flat):
        raise ValueError("LED indices must be -1 or in the range 0..120")
    if not 1 <= layout.hardware_revision <= 255:
        raise ValueError("hardware_revision must be in the range 1..255")

    features = (
        (FEATURE_IT_IS if layout.has_it_is else 0)
        | (FEATURE_MINUTES if layout.has_minutes else 0)
        | (FEATURE_WEEKDAYS if layout.has_weekdays else 0)
    )
    # magic, version, hardware_revision, features, reserved, words, then crc.
    body = struct.pack(
        f"<IBBBB{expected_entries}b",
        CONFIG_MAGIC,
        CONFIG_VERSION,
        layout.hardware_revision,
        features,
        0,
        *layout.flat,
    )
    blob = body + struct.pack("<I", zlib.crc32(body))
    if len(blob) != BLOB_SIZE:
        raise ValueError(f"Layout blob is {len(blob)} bytes, expected {BLOB_SIZE}")
    return blob + b"\xFF" * (FLASH_SECTOR_SIZE - len(blob))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="USB serial port, e.g. /dev/cu.usbserial-XXXX")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT, help="Layout JSON file")
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    args = parser.parse_args()

    layout = load_layout(args.layout)
    image = build_sector_image(layout)

    print(
        f"Ready to write {len(image)} bytes to flash sector 1018 at 0x{FLASH_OFFSET:06X} "
        f"on {args.port}. The firmware and other flash sectors will not be written."
    )
    if not args.yes and input("Type 'yes' to continue: ").strip().lower() != "yes":
        print("Cancelled; no flash operation was performed.")
        return

    with tempfile.TemporaryDirectory(prefix="word-clock-layout-") as temp_dir:
        image_path = Path(temp_dir) / "layout-sector.bin"
        image_path.write_bytes(image)
        command = [
            sys.executable,
            "-m",
            "esptool",
            "--chip",
            "esp8266",
            "--port",
            args.port,
            "--baud",
            str(args.baud),
            "write-flash",
            "--flash-size",
            "4MB",
            f"0x{FLASH_OFFSET:X}",
            str(image_path),
        ]
        subprocess.run(command, check=True)

    print("Layout sector written and verified. Restart the clock and check its log for the loaded-layout message.")


if __name__ == "__main__":
    main()
