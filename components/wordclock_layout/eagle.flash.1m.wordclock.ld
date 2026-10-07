/*
 * ESPHome word-clock flash map for the esp01_1m board.
 *
 * Reserve sector 250 (0x402FA000..0x402FAFFF) for the per-device LED layout.
 * Moving FS_start down by one sector also moves the ESP8266 OTA staging end
 * down, so OTA writes cannot overwrite the layout sector. ESPHome's flash
 * preferences continue to use the EEPROM sector at 0x402FB000.
 */
/* Flash Split for 1M chips */
/* sketch @0x40200000 (~999KB) (1023984B) */
/* layout @0x402FA000 (4KB) */
/* preferences @0x402FB000 (4KB) */
/* rfcal  @0x402FC000 (4KB) */
/* wifi   @0x402FD000 (12KB) */

MEMORY
{
  dport0_0_seg :                        org = 0x3FF00000, len = 0x10
  dram0_0_seg :                         org = 0x3FFE8000, len = 0x14000
  irom0_0_seg :                         org = 0x40201010, len = 0xf9ff0
}

/* FS_start bounds OTA staging; leave the layout sector above it untouched. */
PROVIDE ( _FS_start = 0x402FA000 );
PROVIDE ( _FS_end = 0x402FA000 );
PROVIDE ( _FS_page = 0x0 );
PROVIDE ( _FS_block = 0x0 );

/* Keep ESPHome's preferences in their original, separate sector. */
PROVIDE ( _EEPROM_start = 0x402FB000 );
PROVIDE ( _SPIFFS_start = 0x402FB000 );
PROVIDE ( _SPIFFS_end = 0x402FB000 );
PROVIDE ( _SPIFFS_page = 0x0 );
PROVIDE ( _SPIFFS_block = 0x0 );

INCLUDE "local.eagle.app.v6.common.ld"