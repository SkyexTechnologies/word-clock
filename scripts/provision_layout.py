#!/usr/bin/env python3
"""Write a word-clock LED layout and device info to the device over the ESPHome API."""

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aioesphomeapi import APIClient
from aioesphomeapi.model import UserServiceArgType

NUM_WORDS = 37
LEDS_PER_WORD = 12
NUM_LEDS = 121
DEFAULT_LAYOUT = Path(__file__).resolve().parents[1] / "provisioning" / "default-layout.json"

# Argument names and types of the firmware's set_word_layout service.
SERVICE_ARGS = {
    "flat_layout": UserServiceArgType.INT_ARRAY,
    "hardware_revision": UserServiceArgType.INT,
    "has_it_is": UserServiceArgType.BOOL,
    "has_minutes": UserServiceArgType.BOOL,
    "has_weekdays": UserServiceArgType.BOOL,
}


@dataclass
class DeviceLayout:
    flat: list[int]
    hardware_revision: int
    has_it_is: bool
    has_minutes: bool
    has_weekdays: bool


def load_layout(path: Path) -> DeviceLayout:
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Layout file must be an object with version: 1")

    revision = data.get("hardware_revision")
    if type(revision) is not int or not 1 <= revision <= 255:
        raise ValueError("hardware_revision must be an integer from 1 to 255")

    indications = data.get("indications")
    if not isinstance(indications, dict) or set(indications) != {"it_is", "minutes", "weekdays"}:
        raise ValueError("indications must be an object with it_is, minutes and weekdays")
    if any(type(value) is not bool for value in indications.values()):
        raise ValueError("indications values must be true or false")

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
    return DeviceLayout(
        flat=flat,
        hardware_revision=revision,
        has_it_is=indications["it_is"],
        has_minutes=indications["minutes"],
        has_weekdays=indications["weekdays"],
    )


async def provision(host: str, port: int, layout: DeviceLayout, password: str | None, noise_psk: str | None) -> None:
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
        if {arg.name: arg.type for arg in service.args} != SERVICE_ARGS:
            raise RuntimeError("set_word_layout has an unexpected argument definition; update the firmware")

        await client.execute_service(
            service,
            {
                "flat_layout": layout.flat,
                "hardware_revision": layout.hardware_revision,
                "has_it_is": layout.has_it_is,
                "has_minutes": layout.has_minutes,
                "has_weekdays": layout.has_weekdays,
            },
        )
    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="Device IP address or mDNS hostname")
    parser.add_argument("--port", type=int, default=6053, help="ESPHome API port (default: 6053)")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT, help="Layout JSON file")
    parser.add_argument("--password", help="ESPHome API password, if configured")
    parser.add_argument("--noise-psk", help="ESPHome API encryption key, if the clock has one")
    args = parser.parse_args()

    layout = load_layout(args.layout)
    asyncio.run(provision(args.host, args.port, layout, args.password, args.noise_psk))
    print(
        f"Layout request sent to {args.host}; check the device log for the EEPROM save result "
        "and restart the clock to apply indication visibility."
    )


if __name__ == "__main__":
    main()
