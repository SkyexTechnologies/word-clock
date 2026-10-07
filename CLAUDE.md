# Word Clock — project context for Claude

Dutch word clock firmware by Skyex Technologies (owner: Guido). Written in
ESPHome YAML for an ESP-12S (ESP8266, `esp01_1m` board profile) driving 121
WS2812X LEDs behind a letter grid. The product is meant to be sold, so
decisions favour: one generic firmware for all customers, self-service updates
by customers, and no hard dependency on internet access.

## Repo layout

- `word-clock.yaml` — the complete firmware config (single file, no packages).
- `requirements.txt` — pinned ESPHome version. Bump deliberately.
- `README.md` — user-facing docs (hardware, settings, setup).
- `docs/design-notes.md` — decisions and shelved designs (read before
  proposing changes to how the LED word table or time source works).
- `components/wordclock_layout/` — external component and linker script that
  store the per-device LED word table in dedicated flash sector 250.
- `provisioning/default-layout.json` and `scripts/provision_layout.py` — default
  factory layout and one-time LAN provisioning client.

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
works on macOS in VS Code with the ESPHome extension (set the file's language
mode to ESPHome with Cmd+K M); ESPHome Builder (desktop app) can open the same
folder via `config_dir` in its `settings.json`.

## Key facts about the firmware

- Hardware: LED data GPIO2, light sensor A0 (ADC), button GPIO0
  (hold 2-5 s = restart, 10-20 s = factory reset).
- The `Clock` effect (`addressable_lambda`, 20 ms tick) holds `words[37][12]`:
  LED indices per word, `-1` = unused slot. Rows 0-24 time phrases, 25-31
  weekday letters, 32-36 minute dots. `CurrentTime[5]` picks five rows per tick
  and the lambda fades between the old and new picture.
- Settings are numbered entities (01-13), stored with `restore_value` and
  `restore_from_flash: true`.
- `time: sntp` has no `timezone:` and no `servers:` set (see Known gaps).
- `dashboard_import` points at
  `github://SkyexTechnologies/word-clock/word-clock.yaml@main`, so
  `word-clock.yaml` must stay at the repo root on `main`. Bump
  `project_version` for each release.
- Never commit `secrets.yaml`, `.esphome/`, `.venv/` (see `.gitignore`).

## Decisions already made (do not relitigate without asking)

- **No RTC chip.** Firmware-only solutions on the current hardware.
- **Offline networks:** the target is a LAN with no internet but WITH a local
  NTP server (router/NAS/Home Assistant). Fix is a `servers:` list on `sntp`
  using a bare IP address, not a hostname (no DNS on isolated LANs).
- **Per-device LED layout:** keep the word table in dedicated flash sector 250,
  separate from ESPHome preferences in sector 251. The custom linker script
  reserves sector 250 from OTA staging. See `docs/design-notes.md` and
  `scripts/provision_layout.py` for details.
- ESPHome's `globals`/`restore_value` flash pool on ESP8266 is only ~96 bytes
  total, so it cannot hold the 37x12 table.
- Keep `board: esp01_1m` and its custom linker script in sync; the current OTA
  image has only about 64 KB of two-image OTA headroom.

## Known gaps / open items

1. `sntp` has no `timezone:`, so ESPHome infers it from the compiling machine.
   Wrong hours if that differs from the customer's zone.
2. `sntp` uses the default public pool, so it never syncs on an offline LAN.
3. Fresh devices need a one-time layout write using the `set_word_layout` API
  service and the provisioning client.
4. Confirm how customers actually receive updates (`dashboard_import` + local
   recompile, or a pre-built binary hosted on GitHub Pages with
   `ota: platform: http_request`). The layout design works with either.
5. Recheck the provisioning client's `aioesphomeapi` calls when changing the
  ESPHome dependency pin.

## Working style

- Verify ESPHome behaviour against esphome.io docs before asserting it.
- Prefer small, reviewable YAML edits; keep comments in the YAML in English.
- When changing the word table, keep indices `0-120` (121 LEDs) and 12 slots
  per row.
