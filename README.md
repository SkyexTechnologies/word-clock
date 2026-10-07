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

You need Python 3 and a USB-serial adapter for the first flash.

```bash
git clone https://github.com/SkyexTechnologies/word-clock.git
cd word-clock

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
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

- **Time zone:** the `sntp` time platform has no `timezone:` set, so ESPHome
  infers it from the computer that compiles the firmware. Set `timezone:`
  explicitly (for example `Europe/Amsterdam`) if the clock shows the wrong
  hour.
- **Networks without internet:** `sntp` uses the public NTP pool by default.
  On a LAN with no internet, add a `servers:` list under the `sntp` platform
  with the IP address of a local NTP server (router, NAS, ...).
- **Pinned ESPHome version:** see `requirements.txt` before upgrading.

## Updating via ESPHome Dashboard

The config includes `dashboard_import`, so a clock that is discovered by an
ESPHome Dashboard can be adopted straight from
`github://SkyexTechnologies/word-clock/word-clock.yaml@main`. Keep
`word-clock.yaml` at the repository root on the `main` branch, and bump
`project_version` in the substitutions for every release.
