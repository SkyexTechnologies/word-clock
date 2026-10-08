#!/usr/bin/env python3
"""Write a word-clock LED layout to its reserved flash sector over USB serial."""

import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from provision_layout import load_layout

NUM_WORDS = 37
LEDS_PER_WORD = 12
FLASH_SECTOR_SIZE = 4096
FLASH_OFFSET = 0xFA000  # Physical offset for memory-mapped sector 250 (0x402FA000).
CONFIG_MAGIC = 0x574C4B31  # "WLK1"
CONFIG_VERSION = 1
DEFAULT_LAYOUT = Path(__file__).resolve().parents[1] / "provisioning" / "default-layout.json"


def build_sector_image(flat_layout: list[int]) -> bytes:
    """Build one erased flash sector containing the firmware's LayoutBlob."""
    expected_entries = NUM_WORDS * LEDS_PER_WORD
    if len(flat_layout) != expected_entries:
        raise ValueError(f"Expected {expected_entries} layout entries, got {len(flat_layout)}")
    if any(value < -1 or value >= 121 for value in flat_layout):
        raise ValueError("LED indices must be -1 or in the range 0..120")

    checksum = sum(value & 0xFF for value in flat_layout) & 0xFF
    blob = struct.pack(
        f"<IB{expected_entries}bB",
        CONFIG_MAGIC,
        CONFIG_VERSION,
        *flat_layout,
        checksum,
    )
    if len(blob) > FLASH_SECTOR_SIZE:
        raise ValueError("Layout blob does not fit in the reserved flash sector")
    return blob + b"\xFF" * (FLASH_SECTOR_SIZE - len(blob))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="USB serial port, e.g. /dev/cu.usbserial-XXXX")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT, help="Layout JSON file")
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    args = parser.parse_args()

    flat_layout = load_layout(args.layout)
    image = build_sector_image(flat_layout)

    print(
        f"Ready to write {len(image)} bytes to flash sector 250 at 0x{FLASH_OFFSET:05X} "
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
            "1MB",
            f"0x{FLASH_OFFSET:X}",
            str(image_path),
        ]
        subprocess.run(command, check=True)

    print("Layout sector written and verified. Restart the clock and check its log for the loaded-layout message.")


if __name__ == "__main__":
    main()
