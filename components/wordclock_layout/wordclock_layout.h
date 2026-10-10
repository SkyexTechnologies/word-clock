#pragma once

#include "esphome/core/component.h"
#include "esphome/core/log.h"
#include <EEPROM.h>
#include <cstddef>
#include <cstring>
#include <vector>

namespace esphome {
namespace wordclock_layout {

static const uint8_t NUM_WORDS = 37;
static const uint8_t MAX_LEDS_PER_WORD = 12;
static const uint8_t NUM_LEDS = 121;

static const uint32_t CONFIG_MAGIC = 0x574C4B31;  // "WLK1"
static const uint8_t CONFIG_VERSION = 1;
static const uint16_t EEPROM_SIZE = 512;
// Sector 1018 (0x405FA000) is reserved by the custom 4 MB linker script.
// ESPHome preferences remain in sector 1019 (0x405FB000).
static const uint32_t LAYOUT_FLASH_SECTOR = 1018;

// Indications fitted on this clock (LayoutBlob::features bits).
static const uint8_t FEATURE_IT_IS = 1 << 0;     // "HET IS"
static const uint8_t FEATURE_MINUTES = 1 << 1;   // four minute dots
static const uint8_t FEATURE_WEEKDAYS = 1 << 2;  // weekday letters
static const uint8_t FEATURE_ALL = FEATURE_IT_IS | FEATURE_MINUTES | FEATURE_WEEKDAYS;

// Per-device factory data. Keep identical to scripts/provision_layout_usb.py.
struct LayoutBlob {
  uint32_t magic;
  uint8_t version;
  uint8_t hardware_revision;  // 1-255
  uint8_t features;           // FEATURE_* bits
  uint8_t reserved;           // 0
  int8_t words[NUM_WORDS][MAX_LEDS_PER_WORD];
  uint32_t crc;  // CRC-32 (zlib) over all bytes above
};
static_assert(sizeof(LayoutBlob) == 456, "LayoutBlob layout must match provision_layout_usb.py");

class WordClockLayout : public Component {
 public:
  void setup() override {
    this->layout_eeprom_.begin(EEPROM_SIZE);
    this->layout_eeprom_.get(0, blob_);
    // blob_ holds the copy we use; free the EEPROM library's 512-byte RAM
    // buffer. Nothing was changed, so end() does not write to flash.
    this->layout_eeprom_.end();

    loaded_ = blob_.magic == CONFIG_MAGIC && blob_.version == CONFIG_VERSION && blob_.crc == this->crc_() &&
              this->values_valid_();

    if (!loaded_) {
      ESP_LOGE(TAG, "No valid word layout in flash - running LED self-test until provisioned");
      memset(blob_.words, -1, sizeof(blob_.words));
      blob_.hardware_revision = 0;
      blob_.features = 0;
    } else {
      ESP_LOGI(TAG, "Loaded word layout from flash (version %u, hardware revision %u, indications 0x%02X)",
               blob_.version, blob_.hardware_revision, blob_.features);
    }
  }

  // Drop-in replacement for words[word][slot]; -1 means "no more LEDs".
  int8_t led_for(uint8_t word, uint8_t slot) const {
    if (!loaded_ || word >= NUM_WORDS || slot >= MAX_LEDS_PER_WORD)
      return -1;
    return blob_.words[word][slot];
  }

  bool is_provisioned() const { return loaded_; }
  // 0 while unprovisioned.
  uint8_t hardware_revision() const { return blob_.hardware_revision; }
  // An unprovisioned clock reports every indication, so nothing is hidden.
  bool has_feature(uint8_t feature) const { return !loaded_ || (blob_.features & feature) != 0; }

  // `flat` is NUM_WORDS * MAX_LEDS_PER_WORD entries, row-major. Only called
  // from the factory provisioning API service, never by the update flow.
  bool write_layout(const std::vector<int32_t> &flat, int32_t hardware_revision, bool has_it_is, bool has_minutes,
                    bool has_weekdays) {
    if (flat.size() != (size_t) NUM_WORDS * MAX_LEDS_PER_WORD) {
      ESP_LOGE(TAG, "Layout has %u entries, expected %u", (unsigned) flat.size(),
               (unsigned) (NUM_WORDS * MAX_LEDS_PER_WORD));
      return false;
    }
    if (hardware_revision < 1 || hardware_revision > 255) {
      ESP_LOGE(TAG, "Hardware revision %ld is outside 1..255", (long) hardware_revision);
      return false;
    }

    for (int32_t led : flat) {
      if (led < -1 || led >= NUM_LEDS) {
        ESP_LOGE(TAG, "Layout LED index %ld is outside -1..%u", (long) led, NUM_LEDS - 1);
        return false;
      }
    }

    for (uint8_t w = 0; w < NUM_WORDS; w++)
      for (uint8_t s = 0; s < MAX_LEDS_PER_WORD; s++)
        blob_.words[w][s] = (int8_t) flat[w * MAX_LEDS_PER_WORD + s];

    blob_.magic = CONFIG_MAGIC;
    blob_.version = CONFIG_VERSION;
    blob_.hardware_revision = (uint8_t) hardware_revision;
    blob_.features = (has_it_is ? FEATURE_IT_IS : 0) | (has_minutes ? FEATURE_MINUTES : 0) |
                     (has_weekdays ? FEATURE_WEEKDAYS : 0);
    blob_.reserved = 0;
    blob_.crc = this->crc_();

    // The buffer is only allocated while writing (see setup()).
    this->layout_eeprom_.begin(EEPROM_SIZE);
    this->layout_eeprom_.put(0, blob_);
    loaded_ = this->layout_eeprom_.commit();
    this->layout_eeprom_.end();
    if (loaded_) {
      ESP_LOGI(TAG, "Saved word layout to EEPROM (hardware revision %u, indications 0x%02X); restart to apply "
                    "indication visibility",
               blob_.hardware_revision, blob_.features);
    } else {
      ESP_LOGE(TAG, "EEPROM commit failed; word layout is unavailable until reboot or reprovisioning");
    }
    return loaded_;
  }

 protected:
  static constexpr const char *TAG = "wordclock_layout";
  EEPROMClass layout_eeprom_{LAYOUT_FLASH_SECTOR};
  LayoutBlob blob_{};
  bool loaded_{false};

  bool values_valid_() const {
    if (blob_.hardware_revision == 0 || (blob_.features & ~FEATURE_ALL) != 0)
      return false;
    for (uint8_t w = 0; w < NUM_WORDS; w++)
      for (uint8_t s = 0; s < MAX_LEDS_PER_WORD; s++)
        if (blob_.words[w][s] < -1 || blob_.words[w][s] >= NUM_LEDS)
          return false;
    return true;
  }

  // CRC-32 as computed by zlib.crc32() (reflected, polynomial 0xEDB88320).
  uint32_t crc_() const {
    uint32_t crc = 0xFFFFFFFF;
    const uint8_t *p = reinterpret_cast<const uint8_t *>(&blob_);
    for (size_t i = 0; i < offsetof(LayoutBlob, crc); i++) {
      crc ^= p[i];
      for (uint8_t bit = 0; bit < 8; bit++)
        crc = (crc >> 1) ^ (0xEDB88320 & (0u - (crc & 1)));
    }
    return ~crc;
  }
};

}  // namespace wordclock_layout
}  // namespace esphome
