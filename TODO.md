# To do

Open items from the repo review of 2026-10-08. Remove an item once it's done.

## High priority

- [ ] **Release channel.** `dashboard_import` and `external_components` follow
  `@main`, so every push reaches customers on their next recompile. Point both
  at a `release` branch or a version tag.
- [ ] **Decide how customers receive updates:** `dashboard_import` plus local
  recompile, or a pre-built binary on GitHub Pages with
  `ota: platform: http_request`. The layout storage works with either.
- [ ] **Private repo with public release mirror.** Keep this repo private and
  publish only `word-clock.yaml` and `components/` to a public repo from a
  tag-triggered GitHub Action. Full plan in
  [docs/design-notes.md](docs/design-notes.md#shelved-private-repo-with-public-release-mirror).
- [ ] **OTA headroom is only about 30 KB** (image 481,888 bytes, maximum about
  512 KB). Free up space: set `logger: level: INFO`, and decide whether
  `web_server` is needed alongside the API and captive portal.
- [ ] **Security.** `api:` has no encryption, `ota:` has no password and
  `wifi: ap: {}` is an open access point, so anyone on the LAN can flash
  firmware or call `set_word_layout`. A shared key can't live in a public repo;
  check whether the pinned ESPHome lets Home Assistant set the API key during
  adoption, or document the risk.

## Bugs and rough edges

- [ ] **NaN brightness at boot.** `set_light_brightness` can run (min/max
  numbers restoring) before the light sensor has a reading; the clamp doesn't
  catch `NaN`. Guard with `isnan(sensor_reading)`.
- [ ] **Colour sliders jump.** ESPHome rescales light colours so the strongest
  channel is 1.0 (`normalize_color()` in `light_call.cpp`), and `on_state`
  copies that back to the numbers (0.5/0.5/0.5 snaps to 1.0). Remove the
  sliders or document the behaviour.
- [ ] **"Build default" timezone may be captured too early.** `apply_timezone`
  saves it on its first run, which may be the select's restore during setup,
  before the timezone is set (so it could become UTC). Selecting option 0 after
  Home Assistant has set the zone also restores the build-host zone until the
  next HA sync. Verify in the logs.
- [ ] **Timezone options are stored by position.** Add a YAML comment that new
  zones must be appended, never inserted or reordered.

## Smaller improvements

- [ ] **Free RAM in the layout component:** call `end()` after loading in
  `setup()` and `begin()` again only when writing (about 512 bytes).
- [ ] **"Layout provisioned" diagnostic sensor,** so a dark, unprovisioned clock
  can be told apart from a broken one.
- [ ] **Entity names:** number 07 is missing, and `06.` has a dot while
  `08 Indication` doesn't. Template switches would suit the "Indication"
  settings better than On/Off selects, but changing them resets entity IDs and
  saved settings.
- [ ] **Stronger checksum:** if `CONFIG_VERSION` is ever bumped, replace the
  8-bit sum with a CRC that also covers magic and version.
