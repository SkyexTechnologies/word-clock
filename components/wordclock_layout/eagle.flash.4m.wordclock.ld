/*
 * ESPHome word-clock flash map for 4 MB ESP-12S modules (board esp12e).
 *
 * Based on the framework's eagle.flash.4m.ld (no filesystem). Reserve sector
 * 1018 (0x405FA000..0x405FAFFF) for the per-device LED layout: FS_start and
 * FS_end move down by one sector, and OTA staging ends at FS_start, so OTA
 * writes cannot overwrite the layout. ESPHome's flash preferences stay in the
 * standard EEPROM sector 1019 at 0x405FB000.
 */
/* Flash Split for 4M chips */
/* sketch @0x40200000 (~1019KB) (1044464B) */
/* empty  @0x402FEFF0 (~3052KB), used for OTA staging */
/* layout @0x405FA000 (4KB) */
/* eeprom @0x405FB000 (4KB), ESPHome preferences */
/* rfcal  @0x405FC000 (4KB) */
/* wifi   @0x405FD000 (12KB) */

MEMORY
{
  dport0_0_seg :                        org = 0x3FF00000, len = 0x10
  dram0_0_seg :                         org = 0x3FFE8000, len = 0x14000
  irom0_0_seg :                         org = 0x40201010, len = 0xfeff0
}

/* FS_start bounds OTA staging; leave the layout sector above it untouched. */
PROVIDE ( _FS_start = 0x405FA000 );
PROVIDE ( _FS_end = 0x405FA000 );
PROVIDE ( _FS_page = 0x0 );
PROVIDE ( _FS_block = 0x0 );

/* ESPHome derives its preferences sector from _SPIFFS_end: keep it at 0x405FB000. */
PROVIDE ( _EEPROM_start = 0x405FB000 );
PROVIDE ( _SPIFFS_start = 0x405FB000 );
PROVIDE ( _SPIFFS_end = 0x405FB000 );
PROVIDE ( _SPIFFS_page = 0x0 );
PROVIDE ( _SPIFFS_block = 0x0 );

INCLUDE "local.eagle.app.v6.common.ld"
