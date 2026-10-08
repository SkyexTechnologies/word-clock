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

- Time from Home Assistant or NTP (SNTP), shown in words to the nearest
  5 minutes, plus four minute dots (LEDs 117-120) for the minutes in between.
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
| 06. Time Zone | Follow Home Assistant/build default, or select a region with its UTC offset |
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
├── word-clock.yaml        # the complete firmware configuration
├── components/
│   └── wordclock_layout/  # layout storage component and linker script
├── provisioning/          # default factory LED layout (JSON)
├── scripts/               # one-time layout writers (LAN and USB serial)
├── docs/
│   └── design-notes.md    # why the firmware is built this way
├── requirements.txt       # pinned ESPHome version
├── CLAUDE.md              # project context for Claude Code
├── .gitignore
└── README.md
```

`.esphome/` (build cache) and `secrets.yaml` are created locally and are
ignored by git.

## How the time is shown

Each clock stores a table of LED indices for every word (37 rows of 12
entries, `-1` marks an unused slot) in its own flash; see
[Provisioning a word layout](#provisioning-a-word-layout). Each tick, the
`Clock` effect in `word-clock.yaml` picks up to five rows for the current time:
"HET IS", the minute phrase, the hour, the weekday letter and the minute dots.
It then lights the LEDs listed for those rows and fades between the old and new
picture. The table matches one specific letter-grid wiring; a different grid
layout needs different indices.

## Notes

- **Time source and time zone:** the firmware includes both Home Assistant
  time and SNTP. Home Assistant sends time and its configured time zone over
  the native API; no NTP service on the clock's LAN is needed when Home
  Assistant is connected. The `06. Time Zone` selector follows Home Assistant
  by default, or can choose one representative region for each supported
  timezone: UTC (+00:00), Amsterdam (+01:00 / +02:00 DST), London (+00:00 /
  +01:00 DST), New York (-05:00 / -04:00 DST), Chicago (-06:00 / -05:00 DST),
  Denver (-07:00 / -06:00 DST), Los Angeles (-08:00 / -07:00 DST), Seoul,
  South Korea (+09:00), or Sydney (+10:00 / +11:00 DST). The selection is saved across
  restarts and includes daylight-saving rules for the listed regions. Home
  Assistant 2026.3 or newer is required to send its timezone automatically;
  older versions can use a manually selected region. In standalone use, the
  default zone is inferred when the firmware is compiled; select a region in
  the local web UI if needed. Embedded daylight-saving rules may need a
  firmware update if regional laws change. SNTP uses the public pool by
  default. For an internet-free LAN without Home Assistant, set SNTP to a
  reachable local NTP server IP (use an IP if the LAN has no DNS). The ESP-12S
  has no battery-backed RTC, so after a power loss it needs Home Assistant or
  an NTP server to recover the current time.
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

For factory setup without Wi-Fi, connect the USB-serial adapter and write the
layout directly to the reserved flash sector instead:

```bash
python scripts/provision_layout_usb.py --port /dev/cu.usbserial-XXXX
```

Use 3.3 V UART levels; if the adapter has no automatic reset/bootloader
circuit, enter ESP8266 bootloader mode (GPIO0 low while resetting). On Windows,
pass the adapter's COM port (for example, `COM3`). The script asks for
confirmation, builds the same versioned/checksummed layout blob used by the
firmware, then uses the ESPHome-installed `esptool` to write only sector 250
(`0xFA000`). Use `--layout` for another layout JSON, `--baud` to change the
serial speed, or `--yes` to skip confirmation in a controlled factory process.
Do not use `esptool erase-flash`: that erases the firmware and saved settings as
well as the layout. After flashing, restart the clock and confirm the log says
it loaded the layout. The USB tool is for the project's 1 MB `esp01_1m` flash
map; use the API provisioner for other flash layouts.

The firmware reserves flash sector 250 for the layout and sector 251 for
ESPHome preferences. Keep the `esp01_1m` board and the project linker script
together; changing either can invalidate the storage map. The current firmware
is close to the ESP8266's two-image OTA size limit, so check the OTA binary size
when adding features.
