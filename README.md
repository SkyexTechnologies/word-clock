# Word Clock

ESPHome firmware for a Dutch word clock ("HET IS VIJF OVER HALF ZES"), built
by Skyex Technologies. A 121-LED WS2812X strip sits behind a letter grid and
lights up the words for the current time, the weekday letter, and up to four
minute dots.

- **Hardware:** ESP-12S (ESP8266, `esp01_1m` board profile)
- **Framework:** [ESPHome](https://esphome.io)
- **Main config:** [`word-clock.yaml`](word-clock.yaml)

## Hardware

| Function | Pin | Notes |
| --- | --- | --- |
| LED data | GPIO2 | 121 x WS2812X, GRB order, driven by `neopixelbus` |
| Ambient light sensor | A0 | Analog input, read every 15 s, drives automatic brightness |
| Button | GPIO0 | Pulled up, active low (see below) |

### Button

| Hold time | Action |
| --- | --- |
| 2 - 5 seconds | Restart the clock |
| 10 - 20 seconds | Factory reset (clears WiFi and saved settings) |

## Features

- Time from NTP (SNTP), shown in words to the nearest 5 minutes, plus four
  minute dots (LEDs 117-120) for the minutes in between.
- Weekday letter (Z M D W D V Z, LEDs 110-116).
- Automatic brightness from the light sensor, or manual brightness.
- Smooth fade between times, adjustable from 0 to 10 seconds.
- Settings are stored in flash and survive power loss (`restore_from_flash`).
- WiFi setup through a captive portal or Improv over serial; local web server
  on port 80; native API for Home Assistant.

### Settings exposed in Home Assistant / the web UI

| Entity | What it does |
| --- | --- |
| 01. Word Clock | The light itself (on/off, colour, brightness) |
| 02. Transition | Fade time between times, 0-10 s |
| 03. Brightness | `Automatic` (light sensor) or `Manual` |
| 04. / 05. Minimum / Maximum Brightness | Range used by automatic brightness |
| 06. Hour Offset | Add 0-23 hours to the displayed time |
| 07. Minutes Offset | Add 0-59 minutes to the displayed time |
| 08. Indication: It is | Show or hide "HET IS" |
| 09. Indication: Minutes | Show or hide the four minute dots |
| 10. Indication: Week Days | Show or hide the weekday letter |
| 11. / 12. / 13. Red / Green / Blue | Colour channels (disabled by default) |
| Restart / Factory Reset | Buttons |

## Getting started

You need Python 3.12, 3.13, or 3.14 and a USB-serial adapter for the first
flash. ESPHome is pinned in `requirements.txt`; that release does not support
Python 3.9 or Python 3.15.

On macOS, install Python 3.12 with Homebrew if it is not already available:

```bash
brew install python@3.12
```

On Windows, install Python 3.12 from [python.org](https://www.python.org/downloads/).
Create the environment with `py -3.12 -m venv .venv`, then activate it with
`.venv\Scripts\activate` in Command Prompt or
`.venv\Scripts\Activate.ps1` in PowerShell. Use the same pip and ESPHome
commands below after activation.

If you already have a `.venv` made with an unsupported Python version, deactivate
it and remove that folder before recreating it.

```bash
git clone https://github.com/SkyexTechnologies/word-clock.git
cd word-clock

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

esphome config word-clock.yaml     # validate the configuration
esphome run word-clock.yaml        # compile, upload and show logs
```

The first upload has to go over USB serial. On macOS, find the port with
`ls /dev/cu.*` and pass it explicitly:

```bash
esphome run word-clock.yaml --device /dev/cu.usbserial-XXXX
```

After the first flash the clock appears on your network and later updates can
go over WiFi (OTA): `esphome run word-clock.yaml --device <ip-or-hostname>`.
The configuration enables native ESPHome OTA (`ota: - platform: esphome`);
keep the clock and computer on the same network for wireless updates.

### First-time WiFi setup

1. Power the clock. With no WiFi configured it opens its own access point.
2. Connect to it from a phone or laptop; the captive portal opens.
3. Pick your WiFi network and enter the password.

### Using ESPHome Builder or VS Code

Open this folder in [ESPHome Builder](https://github.com/esphome/esphome-desktop)
(set it as the `config_dir` in its `settings.json`) or in VS Code with the
official [ESPHome extension](https://marketplace.visualstudio.com/items?itemName=ESPHome.esphome-vscode)
for validation and autocomplete. Both work on the same files.

## Project layout

```
word-clock/
├── word-clock.yaml    # the complete firmware configuration
├── requirements.txt   # pinned ESPHome version
├── CLAUDE.md          # project context for Claude Code
├── docs/              # design notes and shelved reference code
├── .gitignore
└── README.md
```

`.esphome/` (build cache) and `secrets.yaml` are created locally and are
ignored by git.

## How the time is shown

The `Clock` effect in `word-clock.yaml` holds a table of LED indices for every
word (`words[37][12]`, `-1` marks an unused slot). Each tick it builds up to
five entries from the current time: "HET IS", the minute phrase, the hour, the
weekday letter and the minute dots. It then lights the LEDs listed for those
entries and fades between the old and new picture. The table matches one
specific letter-grid wiring; a different grid layout needs different indices.

## Notes

- **Time zone:** the `sntp` time platform currently has no `timezone:` set,
  so ESPHome infers it from the computer that compiles the firmware. If the
  clock's time zone differs from the build computer, set an explicit IANA zone
  such as `Europe/Amsterdam` in the `sntp` configuration.
- **Networks without internet:** SNTP currently uses the public NTP pool by
  default. To work on an internet-free LAN, configure an `sntp` server with the
  IP address of a local NTP server. Use an IP rather than a hostname if the
  network has no DNS. Some routers do not provide NTP; a NAS, Home Assistant
  host, or router configured as an NTP server can provide it. There is no RTC,
  so the clock needs an available NTP time source.
- **LED layout:** the LED-to-word table is stored in a dedicated flash sector,
  not compiled into the firmware. A new or unprovisioned clock stays dark until
  its layout is written once. The custom 1 MB linker map keeps OTA writes away
  from the layout and ESPHome-preferences sectors. After installing this
  storage fix from older firmware, provision the layout again once.
- **Pinned ESPHome and Python versions:** `requirements.txt` pins ESPHome.
  Check the release's supported Python versions before upgrading; ESPHome
  2026.9.1 requires Python 3.12-3.14.
- **Design decisions:** see [docs/design-notes.md](docs/design-notes.md) for
  the offline-time and per-device-layout design notes.

## Updating via ESPHome Dashboard

The config includes `dashboard_import`, so a clock that is discovered by an
ESPHome Dashboard can be adopted straight from
`github://SkyexTechnologies/word-clock/word-clock.yaml@main`. Keep
`word-clock.yaml` at the repository root on the `main` branch, and bump
`project_version` in the substitutions for every release.

## Provisioning a word layout

The firmware exposes the `set_word_layout` API service for factory setup. After
the first flash and WiFi setup, connect the clock and provisioning computer to
the same LAN, activate the project virtual environment, then run:

```bash
python scripts/provision_layout.py <clock-ip-or-hostname>
```

The default table is in `provisioning/default-layout.json`. The script validates
37 rows of 12 LED indices and sends them over the encrypted/native ESPHome API
when configured. The device log reports whether EEPROM commit succeeded. Keep
the layout JSON with factory records; ordinary firmware updates must not call
the provisioning service.

The firmware reserves flash sector 250 for the layout and sector 251 for
ESPHome preferences. Keep the `esp01_1m` board and the project linker script
together; changing either can invalidate the storage map. The current firmware
is close to the ESP8266's two-image OTA size limit, so check the OTA binary size
when adding features.
