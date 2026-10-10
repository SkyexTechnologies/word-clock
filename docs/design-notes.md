# Design notes

Why the firmware is built the way it is. Three topics: per-device LED layout
storage, offline (no internet) time, and how firmware is published to
customers. For setup and usage, see the [README](../README.md).

## 1. Per-device LED layout storage

### Problem

Every physical clock can have its own LED-index-to-word wiring. Customers
update firmware themselves from one shared, centrally maintained config, so
the per-unit table must not be part of the compiled firmware. Every customer
runs the same binary, and an update must never need per-device data.

### Decision

Store the table in dedicated flash sector 1018 (`0x405FA000`) of the ESP-12S's
4 MB flash (`esp12e` board profile). ESPHome preferences use sector 1019
(`0x405FB000`). A custom linker script, based on the framework's
`eagle.flash.4m.ld`, moves the OTA staging boundary down by one sector, keeping
OTA writes below the layout sector. The `wordclock_layout` component loads the
table once at boot, and the Clock effect reads it from RAM.

Ruled out:

- `globals: restore_value: true`: the ESP8266 flash-preferences pool is shared
  by all components and the Wi-Fi credentials and holds 512 bytes in total;
  the table alone is 450 bytes.
  There are also open ESPHome issues about flash preferences being disturbed by
  OTA on ESP8266.
- One compiled binary per customer (packages/substitutions): ESPHome's usual
  advice for sellers, but it does not fit self-service updates from one shared
  build.

### How it works

- Storage format, version 1 (456 bytes, `EEPROMClass(1018)` with a 512-byte
  buffer): `uint32 magic` ("WLK1"), `uint8 version`, `uint8 hardware_revision`
  (1-255), `uint8 features` (bit 0 "HET IS", bit 1 minute dots, bit 2 weekday
  letters), `uint8 reserved`, `int8_t words[37][12]`, `uint32 crc` (CRC-32 as
  computed by `zlib.crc32` over all preceding bytes). Every LED value fits in
  `int8_t`, including the `-1` sentinel. Format 1 was redefined in October 2026
  (before the first release) to add the device info and replace the 8-bit sum
  with the CRC; changing it after release means bumping `CONFIG_VERSION`.
- `setup()` reads the blob. If magic, version, CRC, the device info or any LED index is
  wrong (blank or corrupt unit), it logs an error and keeps the table at `-1`
  instead of lighting random LEDs. The Clock effect then runs an LED self-test
  on the raw LED indices (all LEDs cycling red, green, blue at full
  brightness), so an unprovisioned clock is visibly different from a broken
  one and can be checked at the factory before provisioning.
- The effect lambda calls `id(layout).led_for(row, slot)`; `-1` means unused.
- `on_boot` priority -10 runs after component `setup()`, so the table is
  loaded before the Clock effect starts.
- Writing happens only at provisioning time, never during updates:
  - **Over the LAN:** the `set_word_layout` API service takes an `int[]`
    (37 x 12, row-major), the hardware revision and three indication flags,
    and calls `write_layout()`, which validates and
    commits it. `scripts/provision_layout.py` sends
    `provisioning/default-layout.json` (or another file) to it.
  - **Over USB serial:** `scripts/provision_layout_usb.py` builds the same blob
    and writes only sector 1018 (physical offset `0x3FA000`) with esptool, for
    factory setup before Wi-Fi is available.
- Changing the table shape means bumping `CONFIG_VERSION` and re-provisioning
  every unit.

### Guardrails

- Keep `board: esp12e` and the 4 MB flash map. The custom linker script
  reserves sector 1018 and ends OTA staging at `0x405FA000`.
- Keep ESPHome preferences in sector 1019; do not move `_SPIFFS_end` onto
  sector 1018 or restore the stock linker script.
- The firmware itself can be at most 1,044,464 bytes (the ESP8266's mapped
  flash window). Updates are staged in the roughly 3 MB between the end of the
  firmware and the layout sector, so staging space is not a constraint.
- History: until October 2026 the project used the 1 MB `esp01_1m` map (layout
  in sector 250). There, the running and the staged image had to share about
  1 MB, which limited the firmware to roughly 512-590 KB and ruled out HTTPS
  updates (BearSSL adds about 148 KB). The ESP-12S has 4 MB, so the map was
  switched.
- Keep the blob format and flash offset identical in the component, the linker
  script and `scripts/provision_layout_usb.py`.
- Keep the provisioning path separate from anything the update flow touches.

## 2. Offline / no-internet time

### Requirement

After installation the clock must work on Wi-Fi with no internet, provided a
local time source is available: Home Assistant or a local NTP server. No RTC
chip (ruled out).

### Decision

The one standard firmware includes both sources:

```yaml
time:
  - platform: homeassistant
    id: homeassistant_time
  - platform: sntp
    id: sntp_time
```

- ESPHome's `homeassistant` time platform synchronizes over the native API, so
  a clock connected to Home Assistant needs no NTP server. With no explicit
  `timezone:`, it also takes Home Assistant's timezone at runtime.
- `sntp` defaults to the public `0/1/2.pool.ntp.org`, which silently never
  syncs offline. It accepts up to 3 servers; on an isolated LAN use a bare IP,
  because there may be no DNS.
- Without Home Assistant, the timezone defaults to the one inferred from the
  machine that compiled the firmware. The `06. Time Zone` select lets users
  pick a supported region instead (list in the README). It stores the option
  index and is reapplied after each Home Assistant time sync. Display hour and
  minute offsets were removed in favour of real timezones.

### Caveat for customers

Many ISP routers do not serve NTP on the LAN. OPNsense, pfSense, UniFi, OpenWrt,
or a NAS / Home Assistant box running chrony or ntpd usually do. Without one of
those, the clock has no time source after a power loss. A "last known time
survives reboot" software clock was considered and not pursued.

## 3. Publishing firmware to customers

### Current setup

This repository is public. Customers adopt a clock through `dashboard_import`
(`github://SkyexTechnologies/word-clock/word-clock.yaml@main`), and the
`wordclock_layout` component is loaded with
`external_components: source: github://SkyexTechnologies/word-clock@main`.
Both need anonymous HTTPS access, so a private repo breaks adoption and
customer builds.

A `type: local` component path does not work here: ESPHome resolves it
against the customer's config folder (`CORE.relative_config_path`), which has
no `components/` directory. Because the component is fetched from GitHub,
local builds also use the pushed version (cached, refreshed daily), not
uncommitted edits in `components/`.

`esphome: min_version` matches the pin in `requirements.txt`, so customer
dashboards running an older ESPHome fail with a clear message.

### Shelved: private repo with public release mirror

Goal: keep working history, factory scripts, provisioning data and design
notes private, and ship customers only tagged releases instead of every push
to `main`.

Plan:

- Make this repo private again. Create a public repo, e.g.
  `SkyexTechnologies/word-clock-firmware`, holding only `word-clock.yaml`,
  `components/` and a short customer README.
- Add `.github/workflows/publish.yml` here, triggered by tags `v*`. It checks
  that the tag matches `project_version`, compiles the firmware, clones the
  public repo, replaces `word-clock.yaml` and `components/`, commits
  "Release vX.Y.Z", tags it and pushes to a `release` branch.
- Authenticate with an SSH deploy key that has write access to the public repo
  only; store its private half as the Actions secret `PUBLIC_REPO_DEPLOY_KEY`.
- Point `external_components` and `dashboard_import` at
  `github://SkyexTechnologies/word-clock-firmware...@release`.
- Optional extension: the same workflow attaches the compiled `.bin` to a
  GitHub Release or GitHub Pages for `ota: platform: http_request`.

The owner has to create the public repo and the deploy key.
