# Word Clock — project context for Claude

Dutch word clock firmware by Skyex Technologies (owner: Guido). Written in
ESPHome YAML for an ESP-12S (ESP8266, `esp01_1m` board profile) driving 121
WS2812X LEDs behind a letter grid. The product is meant to be sold, so
decisions favour: one generic firmware for all customers, self-service updates
by customers, and no hard dependency on internet access.

Hardware, settings and setup are in `README.md`; the reasoning behind the
layout storage, time sources and publishing is in `docs/design-notes.md`;
open work is tracked in GitHub Issues (`gh issue list`; `gh` is installed at
`/opt/homebrew/bin`). Reference the issue number in commits that fix one.

## Repo layout

- `word-clock.yaml` — the complete firmware config.
- `components/wordclock_layout/` — external component and linker script that
  store the per-device LED word table in flash sector 250.
- `provisioning/default-layout.json` — default factory layout.
- `scripts/provision_layout.py` (LAN, via API) and
  `scripts/provision_layout_usb.py` (USB serial) — one-time layout writers.
- `requirements.txt` — pinned ESPHome version. Bump deliberately.

## Commands (run from repo root, venv active)

```bash
source .venv/bin/activate
esphome config word-clock.yaml                              # validate
esphome compile word-clock.yaml                             # build
esphome run word-clock.yaml --device /dev/cu.usbserial-XXXX # first flash (USB)
esphome run word-clock.yaml --device <ip-or-hostname>       # later flashes (OTA)
esphome logs word-clock.yaml
```

Always run `esphome config word-clock.yaml` after editing the YAML. The user
works on macOS in VS Code with the ESPHome extension.

## Key facts

- The `Clock` effect (`addressable_lambda`, 20 ms tick) reads the word table
  through `id(layout).led_for(row, slot)`: 37 rows x 12 slots, `-1` = unused.
  Rows 0-24 time phrases, 25-31 weekday letters, 32-36 minute dots.
- `external_components` loads `wordclock_layout` from
  `github://SkyexTechnologies/word-clock@main`, not a local path, so adopted
  configs can find it. Local builds therefore use the pushed component; push
  component changes before building.
- `dashboard_import` points at `word-clock.yaml` on `main`, so it and
  `components/` must stay at the repo root. Bump `project_version` per release.
- `esphome: min_version` must match the pin in `requirements.txt`.
- Timezone: no explicit `timezone:`, so Home Assistant supplies it; the
  `06. Time Zone` select can override it. Add zones only with verified
  daylight-saving rules.
- Never commit `secrets.yaml`, `.esphome/`, `.venv/`.

## Decisions already made (do not relitigate without asking)

- **No RTC chip.** Firmware-only solutions on the current hardware.
- **Offline time:** Home Assistant time over the native API, plus SNTP (a bare
  local IP where there is no DNS).
- **Per-device LED layout** lives in flash sector 250, separate from ESPHome
  preferences in sector 251. The shared ESPHome preferences pool (512 bytes,
  used by every restored entity and the Wi-Fi credentials) can't hold it.
  Fresh devices need a one-time layout write.

## Guardrails

- Keep `board: esp01_1m` and the custom linker script in sync.
- ESP8266 preferences are stored by position, in component setup order, with
  the Wi-Fi credentials last. Adding, removing or resizing anything that
  restores state (restore_value numbers/selects, switches, light
  `restore_mode`, globals) shifts them: after that update the clock loses its
  Wi-Fi credentials and settings and starts its setup hotspot. Check this
  before every flash and warn up front. Hiding an entity (`internal: true`)
  or renaming it doesn't shift positions (renaming resets only that value).
- The light (setup priority 799) is set up before the layout component (600)
  and Wi-Fi. Keep it off during setup (`RESTORE_AND_OFF`) and turn it on in
  `on_boot`; turning it on earlier crashed the fallback hotspot.
- OTA size limit: the image (~485 KB) can grow to roughly 590 KB with
  ESPHome's compressed native OTA, but only ~512 KB if an uncompressed `.bin`
  is uploaded (web server OTA). Check the image size when adding features.
- Keep the layout blob format and flash offset identical in the component and
  `scripts/provision_layout_usb.py`.
- Recheck the `aioesphomeapi` calls in `scripts/provision_layout.py` when
  bumping the ESPHome pin.

## Working style

- Verify ESPHome behaviour against esphome.io docs before asserting it.
- Prefer small, reviewable YAML edits; keep comments in the YAML in English.
- When changing the word table, keep indices `0-120` (121 LEDs) and 12 slots
  per row.
