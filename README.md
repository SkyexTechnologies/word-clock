# Word Clock

ESPHome firmware for a Dutch word clock ("HET IS VIJF OVER HALF ZES"), built
by Skyex Technologies. A 121-LED WS2812X strip sits behind a letter grid and
lights up the words for the current time, the weekday letter, and up to four
minute dots.

- **Hardware:** ESP-12S with 4 MB flash (ESP8266, `esp12e` board profile)
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
- Automatic brightness from the light sensor, or a fixed brightness set on the
  light.
- Smooth fade between times, adjustable from 0 to 10 seconds.
- Settings, colour and the set brightness are stored in flash and survive
  power loss (`restore_from_flash`); after a power cut the clock turns on again.
- WiFi setup through a captive portal or Improv over serial; local web server
  on port 80 (works without Home Assistant, including a colour picker); native
  API for Home Assistant.

### Settings exposed in Home Assistant / the web UI

| Entity | What it does |
| --- | --- |
| 01. Word Clock | The light itself: on/off, colour (colour picker in the web UI) and brightness |
| 02. Transition | Fade time between times, 0-10 s |
| 03. Automatic Brightness | On: follow the light sensor. Off: use the brightness set on the light |
| 04. / 05. Minimum / Maximum Brightness | Range used by automatic brightness |
| 06. Time Zone | Follow Home Assistant/build default, or select a region with its UTC offset |
| 07. Indication: It is | Show or hide "HET IS" |
| 08. Indication: Minutes | Show or hide the four minute dots |
| 09. Indication: Week Days | Show or hide the weekday letter |
| Restart Word Clock | Button. A factory reset is only possible with the physical button (hold 10-20 s), not over the network |
| Firmware Update | Diagnostic: installed version and whether an update is available |
| Check for Firmware Update / Install Firmware Update | Buttons for the downloaded updates (see [Updating the firmware](#updating-the-firmware)) |
| Layout Provisioned | Diagnostic: on when a valid word layout is stored; off means no layout, and the clock runs its LED self-test (colour cycle) until it is provisioned |

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
  not compiled into the firmware. A new or unprovisioned clock runs an LED
  self-test (see [LED self-test and setup signals](#led-self-test-and-setup-signals))
  until its layout is written once. The custom 4 MB linker map keeps OTA writes
  away from the layout and ESPHome-preferences sectors. Clocks flashed with the
  earlier 1 MB flash map need a one-time USB flash and layout write.
- **Pinned ESPHome and Python versions:** `requirements.txt` pins ESPHome.
  Check the release's supported Python versions before upgrading; ESPHome
  2026.9.1 requires Python 3.12-3.14.
- **Design decisions:** see [docs/design-notes.md](docs/design-notes.md) for
  the offline-time and per-device-layout design notes.

## Updating the firmware

**Downloaded updates (no Home Assistant or ESPHome needed).** The clock checks a
manifest (`update_manifest_url` in the substitutions) every 6 hours. The web page
shows the result under *Firmware Update*; *Install Firmware Update* downloads the
new firmware, checks its MD5 and installs it. Home Assistant shows the same
update as a standard update entity. Updates are never installed automatically.
Until firmware is published (issue #2), the URL is a placeholder and the status
reads "update server not reachable". ESPHome cannot verify HTTPS certificates
on the ESP8266 (`verify_ssl: false`); the MD5 in the manifest protects against
corrupted downloads, not against a tampered server.

The web page no longer accepts firmware uploads (`web_server: ota: false`), so
nobody on the network can install their own firmware through it.

**ESPHome Dashboard / Builder.** The config includes `dashboard_import`, so a
clock that is discovered by an ESPHome Dashboard can be adopted straight from
`github://SkyexTechnologies/word-clock/word-clock.yaml@main`. Keep
`word-clock.yaml` at the repository root on the `main` branch. See `CLAUDE.md`
for the version numbering (`X.Y.Z-dev` between releases).

## Provisioning a word layout

### LED self-test and setup signals

Until the clock is fully set up, the LEDs show its state instead of the time:

| State | What the LEDs do |
| --- | --- |
| **No layout written** (LED self-test) | All LEDs cycle red, green and blue at full brightness, one second each. Every LED should show every colour; a dark LED or a missing colour points to a faulty LED or solder joint. Needs no Wi-Fi or time. |
| **Layout written, but no time yet since power-on** (no Wi-Fi, Home Assistant or NTP) | A single LED steps through all 121 LEDs, 0.1 s each, in the clock's colour. This also shows the wiring order. |
| **Time known** | The time in words. If Wi-Fi drops later, the clock keeps showing the time it knows. |

The self-test always runs at full brightness, whatever the brightness settings
say. White is left out on purpose: all LEDs at full white draw about 7 A. Once a
layout is written, the clock switches to the next state without a restart.

To map the wiring of a new letter grid, write any layout (for example the
default), keep the clock offline, and set `logger: level: VERBOSE`: the log then
prints `[led_test] LED n` for each LED of the running light.

### Writing the layout

The firmware exposes the `set_word_layout` API service for factory setup. After
the first flash and WiFi setup, connect the clock and provisioning computer to
the same LAN, activate the project virtual environment, then run:

```bash
python scripts/provision_layout.py <clock-ip-or-hostname>
```

The default table is in `provisioning/default-layout.json`. The script validates
37 rows of 12 LED indices and sends them over the encrypted/native ESPHome API
when configured. The device log reports whether EEPROM commit succeeded, and
the `Layout Provisioned` diagnostic sensor turns on once it has. Keep
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
firmware, then uses the ESPHome-installed `esptool` to write only sector 1018
(`0x3FA000`). Use `--layout` for another layout JSON, `--baud` to change the
serial speed, or `--yes` to skip confirmation in a controlled factory process.
Do not use `esptool erase-flash`: that erases the firmware and saved settings as
well as the layout. After flashing, restart the clock and confirm the log says
it loaded the layout, or that `Layout Provisioned` is on. The USB tool is for
the project's 4 MB flash map; use the API provisioner for other flash layouts.

The firmware reserves flash sector 1018 for the layout and sector 1019 for
ESPHome preferences. Keep the `esp12e` board and the project linker script
together; changing either can invalidate the storage map. The firmware can
grow to about 1 MB, the ESP8266 maximum, with about 3 MB of flash left for
staging updates (see [design notes](docs/design-notes.md#guardrails)).

### Removing the layout

Erase the layout to rerun the [LED self-test](#led-self-test-and-setup-signals),
to reuse a board behind a different letter grid, or to return a unit to its
factory state. The layout cannot be removed over Wi-Fi, and the factory reset
(hold the button 10-20 s) keeps it on purpose: that reset only clears Wi-Fi and
settings in sector 1019.

Connect the clock over USB (as for the USB layout writer above), then erase
only the 4 KB layout sector:

```bash
source .venv/bin/activate
python -m esptool --chip esp8266 --port /dev/cu.usbserial-XXXX erase-region 0x3FA000 0x1000
```

Restart the clock. It starts the LED self-test, and `Layout Provisioned` is
off. Firmware, Wi-Fi and settings are untouched. To put a layout back, use
either method under [Writing the layout](#writing-the-layout).

- Use exactly `0x3FA000 0x1000`. Another address or length can erase the
  firmware, the settings or the Wi-Fi calibration data.
- Never use `esptool erase-flash`; it erases everything.
- The address only applies to the project's 4 MB flash map (`esp12e`).
