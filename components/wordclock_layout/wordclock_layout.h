#pragma once

#include "esphome/core/component.h"
#include "esphome/core/log.h"
#include <EEPROM.h>
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
// Sector 250 (0x402FA000) is reserved by the custom 1 MB linker script.
// ESPHome preferences remain in sector 251 (0x402FB000).
static const uint32_t LAYOUT_FLASH_SECTOR = 250;

struct LayoutBlob {
  uint32_t magic;
  uint8_t version;
  int8_t words[NUM_WORDS][MAX_LEDS_PER_WORD];
  uint8_t checksum;
};

class WordClockLayout : public Component {
 public:
  void setup() override {
    this->layout_eeprom_.begin(EEPROM_SIZE);
    this->layout_eeprom_.get(0, blob_);

    loaded_ = blob_.magic == CONFIG_MAGIC && blob_.version == CONFIG_VERSION &&
              blob_.checksum == this->checksum_() && this->values_valid_();

    if (!loaded_) {
      ESP_LOGE(TAG, "No valid word layout in flash - running LED self-test until provisioned");
      memset(blob_.words, -1, sizeof(blob_.words));
    } else {
      ESP_LOGI(TAG, "Loaded word layout from flash (version %u)", blob_.version);
    }
  }

  // Drop-in replacement for words[word][slot]; -1 means "no more LEDs".
  int8_t led_for(uint8_t word, uint8_t slot) const {
    if (!loaded_ || word >= NUM_WORDS || slot >= MAX_LEDS_PER_WORD)
      return -1;
    return blob_.words[word][slot];
  }

  bool is_provisioned() const { return loaded_; }

  // `flat` is NUM_WORDS * MAX_LEDS_PER_WORD entries, row-major. Only called
  // from the factory provisioning API service, never by the update flow.
  bool write_layout_flat(const std::vector<int32_t> &flat) {
    if (flat.size() != (size_t) NUM_WORDS * MAX_LEDS_PER_WORD) {
      ESP_LOGE(TAG, "Layout has %u entries, expected %u", (unsigned) flat.size(),
               (unsigned) (NUM_WORDS * MAX_LEDS_PER_WORD));
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
    blob_.checksum = this->checksum_();

    this->layout_eeprom_.put(0, blob_);
    loaded_ = this->layout_eeprom_.commit();
    if (loaded_) {
      ESP_LOGI(TAG, "Saved word layout to EEPROM");
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
    for (uint8_t w = 0; w < NUM_WORDS; w++)
      for (uint8_t s = 0; s < MAX_LEDS_PER_WORD; s++)
        if (blob_.words[w][s] < -1 || blob_.words[w][s] >= NUM_LEDS)
          return false;
    return true;
  }

  uint8_t checksum_() const {
    uint8_t sum = 0;
    const uint8_t *p = reinterpret_cast<const uint8_t *>(blob_.words);
    for (size_t i = 0; i < sizeof(blob_.words); i++)
      sum += p[i];
    return sum;
  }
};

}  // namespace wordclock_layout
}  // namespace esphome
