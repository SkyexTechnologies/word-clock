# Design notes

Decision records carried over from the planning conversation. Two topics:
per-device LED layout storage, and offline (no internet) time.

## 1. Per-device LED layout storage

### Problem

Every physical clock can have its own LED-index-to-word wiring (the
`words[][12]` table). Customers update firmware themselves from one shared,
centrally maintained config, so the per-unit table must not be part of the
compiled firmware. Every customer should run the same binary, and an update
must never need per-device data.

### Decision (implemented in `word-clock.yaml`)

Store the table in dedicated flash sector 250 (`0x402FA000`) on the 1 MB
`esp01_1m` layout. ESPHome preferences use sector 251 (`0x402FB000`). A custom
linker script moves the OTA staging boundary down by one sector, keeping OTA
writes below the layout sector. A small custom ESPHome component loads the
table once at boot. The effect lambda then reads it from RAM.

Ruled out:

- `globals: restore_value: true`: the ESP8266 flash-preferences pool is shared
  by all components and holds about 96 bytes in total. The table is 384-444
  bytes. There are also open ESPHome issues about flash preferences being
  disturbed by OTA on ESP8266.
- One compiled binary per customer (packages/substitutions): ESPHome's usual
  advice for sellers, but it does not fit self-service updates from one shared
  build.

### How it works

- Storage format (about 450 bytes, `EEPROMClass(250)` with a 512-byte buffer): `uint32 magic`
  ("WLK1"), `uint8 version`, `int8_t words[NUM_WORDS][12]`, `uint8 checksum`.
  Every value fits in `int8_t`, including the `-1` sentinel.
- `setup()` reads the blob. If magic, version or checksum is wrong (blank or
  corrupt unit) it logs an error and fills the table with `-1`, so the clock
  stays dark instead of lighting random LEDs.
- `led_for(word, slot)` replaces `words[word][slot]` in the effect lambda:

  ```cpp
  int8_t led = id(layout).led_for(CurrentTime[i], j);
  if (led >= 0) letters[led] = current_color;
  ```

- Writing happens only at provisioning time. An `api: services:` entry
  `set_word_layout` takes an `int[]` (rows x 12, row-major) and calls
  `write_layout_flat()`. A bench script using `aioesphomeapi` flattens the
  unit's table and calls the service once over the LAN after the first boot.
  Customer OTA updates never call it. After migrating from the old shared
  sector, provision the table once again; subsequent OTA updates preserve it.
- Wiring in YAML:

  ```yaml
  external_components:
    - source:
        type: local
        path: components
  wordclock_layout:
    id: layout
  api:
    services:
      - service: set_word_layout
        variables:
          flat_layout: int[]
        then:
          - lambda: |-
              id(layout).write_layout_flat(flat_layout);
  ```

- `on_boot` priority -10 runs after component `setup()`, so the table is
  loaded before the Clock effect starts.

### Reference code

`components/wordclock_layout/` is the live component. It uses 37 rows of 12
entries and validates each LED index (`-1` or `0..120`) before writing. The
original reference implementation remains under
`docs/layout-storage-reference/`. Changing the table shape means bumping
`CONFIG_VERSION` and re-provisioning units.

The current factory map is in `provisioning/default-layout.json`. After first
boot (and once after migrating from the previous shared-sector firmware), run
`python scripts/provision_layout.py <clock-ip-or-hostname>` to call
the `set_word_layout` service over the ESPHome API. The script checks the
row/entry counts and LED ranges before sending; the component checks them again
before committing EEPROM. The layout is not part of normal OTA updates.

### Guardrails

- Keep `board: esp01_1m` and the 1 MB flash map. The custom linker script
  reserves sector 250 and limits OTA staging to end at `0x402FA000`.
- The current OTA image is about 479 KB; the two-image OTA limit is about
  500 KB, leaving roughly 64 KB of headroom. Check image size on every release.
- Keep ESPHome preferences in sector 251; do not move `_SPIFFS_end` onto sector
  250 or restore the stock linker script.
- Keep the provisioning path separate from anything the update flow touches.
- Check the `aioesphomeapi` method names against the pinned version before
  writing the bench script (`list_entities_services`, `execute_service`).

## 2. Offline / no-internet time

### Requirement

After installation the clock must work on WiFi with no internet, as long as a
local NTP server exists on that LAN. No RTC chip (ruled out).

### Facts

- `sntp` accepts up to 3 servers, hostnames or IPs. Default is the public
  `0/1/2.pool.ntp.org`, which silently never syncs offline.
- Use a bare IP, not a hostname. Isolated LANs may have no DNS, and ESPHome
  warns that manual IPs need `dns1`/`dns2` for hostnames.
- `timezone:` accepts IANA names (`Europe/Amsterdam`) or POSIX strings. If
  omitted ESPHome infers it from the machine that compiles the firmware.

### Recommended change (not in the current YAML)

```yaml
substitutions:
  ntp_server_1: "0.pool.ntp.org"
  ntp_server_2: "1.pool.ntp.org"
  ntp_server_3: "2.pool.ntp.org"
  timezone: "Europe/Amsterdam"

time:
  - platform: sntp
    id: sntp_time
    timezone: ${timezone}
    servers:
      - ${ntp_server_1}
      - ${ntp_server_2}
      - ${ntp_server_3}
```

Offline customers override `ntp_server_1` with their local NTP server's IP.

### Caveat for customers

Many ISP routers do not serve NTP on the LAN. OPNsense, pfSense, UniFi, OpenWrt,
or a NAS / Home Assistant box running chrony or ntpd usually do. Without one of
those, the clock has no time source at all. A "last known time survives reboot"
software clock was considered and not pursued.
