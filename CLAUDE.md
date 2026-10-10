# Word Clock — project context for Claude

Dutch word clock firmware by Skyex Technologies (owner: Guido). Written in
ESPHome YAML for an ESP-12S (ESP8266, 4 MB flash, `esp12e` board profile) driving 121
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
  store the per-device LED word table in flash sector 1018 (4 MB flash map).
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
  component changes before building. ESPHome caches the clone for a day: after
  pushing a component change, delete `.esphome/external_components/` so the
  next build fetches it. To test component changes before pushing, point the
  source temporarily at `type: local`, `path: components` (never commit that).
- `dashboard_import` points at `word-clock.yaml` on `main`, so it and
  `components/` must stay at the repo root.
- `project_version` is `X.Y.Z-dev` between releases (nothing shipped yet; the
  first release will be `1.0.0`). Don't bump it per change: on release, drop
  `-dev` and tag the commit `vX.Y.Z`, then set the next `-dev` version.
- `esphome: min_version` must match the pin in `requirements.txt`.
- Timezone: no explicit `timezone:`, so Home Assistant supplies it; the
  `06. Time Zone` select can override it. Add zones only with verified
  daylight-saving rules.
- Security: `api: encryption: {}` (Home Assistant sets a per-clock key) and a
  `provisioning:` 15-minute setup window. Native OTA stays, without a password
  (decided 2026-10-09); with a runtime key ESPHome only offers OTA encryption,
  so unencrypted uploads remain possible on the LAN. Downloaded updates via
  `update: http_request`. Once a clock has a key, `esphome logs` over the
  network needs that key; use serial logs on the bench clock (decided
  2026-10-10: no separate dev config).
- Never commit `secrets.yaml`, `.esphome/`, `.venv/`.

## Decisions already made (do not relitigate without asking)

- **No RTC chip.** Firmware-only solutions on the current hardware.
- **Offline time:** Home Assistant time over the native API, plus SNTP (a bare
  local IP where there is no DNS).
- **Per-device LED layout** lives in flash sector 1018, separate from ESPHome
  preferences in sector 1019. The shared ESPHome preferences pool (512 bytes,
  used by every restored entity and the Wi-Fi credentials) can't hold it.
  Fresh devices need a one-time layout write.

## Guardrails

- **4 MB flash map** (decided 2026-10-09, replacing `esp01_1m`): keep
  `board: esp12e` and `eagle.flash.4m.wordclock.ld` in sync. Changing the map
  moves the layout and settings sectors (USB flash + re-provisioning).
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
- Firmware size limit: 1,044,464 bytes (ESP8266 mapped flash window). OTA
  staging has about 3 MB, so it is not a constraint.
- Keep the layout blob format and flash offset identical in the component and
  `scripts/provision_layout_usb.py`.
- Recheck the `aioesphomeapi` calls in `scripts/provision_layout.py` when
  bumping the ESPHome pin.

## Working style

- Verify ESPHome behaviour against esphome.io docs before asserting it.
- Prefer small, reviewable YAML edits; keep comments in the YAML in English.
- When changing the word table, keep indices `0-120` (121 LEDs) and 12 slots
  per row.
