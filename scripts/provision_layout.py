#!/usr/bin/env python3
"""Write a word-clock LED layout to the device's EEPROM over the ESPHome API."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from aioesphomeapi import APIClient
from aioesphomeapi.model import UserServiceArgType

NUM_WORDS = 37
LEDS_PER_WORD = 12
NUM_LEDS = 121
DEFAULT_LAYOUT = Path(__file__).resolve().parents[1] / "provisioning" / "default-layout.json"


def load_layout(path: Path) -> list[int]:
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Layout file must be an object with version: 1")

    words = data.get("words")
    if not isinstance(words, list) or len(words) != NUM_WORDS:
        raise ValueError(f"Expected exactly {NUM_WORDS} word rows")

    flat: list[int] = []
    for row_number, row in enumerate(words):
        if not isinstance(row, list) or len(row) != LEDS_PER_WORD:
            raise ValueError(f"Row {row_number} must contain exactly {LEDS_PER_WORD} entries")
        for value in row:
            if type(value) is not int or value < -1 or value >= NUM_LEDS:
                raise ValueError(f"Invalid LED index in row {row_number}: {value!r}")
            flat.append(value)
    return flat


async def provision(host: str, port: int, layout: list[int], password: str | None, noise_psk: str | None) -> None:
    client = APIClient(
        host,
        port,
        password=password,
        noise_psk=noise_psk,
        client_info="word-clock-layout-provisioner",
    )
    await client.connect(login=True)
    try:
        _, services = await client.list_entities_services()
        service = next((item for item in services if item.name == "set_word_layout"), None)
        if service is None:
            raise RuntimeError("Device does not expose the set_word_layout service")
        if len(service.args) != 1 or service.args[0].name != "flat_layout" or service.args[0].type != UserServiceArgType.INT_ARRAY:
            raise RuntimeError("set_word_layout has an unexpected argument definition")

        await client.execute_service(service, {"flat_layout": layout})
    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="Device IP address or mDNS hostname")
    parser.add_argument("--port", type=int, default=6053, help="ESPHome API port (default: 6053)")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT, help="Layout JSON file")
    parser.add_argument("--password", help="ESPHome API password, if configured")
    parser.add_argument("--noise-psk", help="ESPHome API encryption key, if configured")
    args = parser.parse_args()

    flat_layout = load_layout(args.layout)
    asyncio.run(provision(args.host, args.port, flat_layout, args.password, args.noise_psk))
    print(f"Layout request sent to {args.host}; check the device log for the EEPROM save result.")


if __name__ == "__main__":
    main()
