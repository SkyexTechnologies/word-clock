#pragma once

#include "esphome/core/component.h"
#include "esphome/core/log.h"
#include <EEPROM.h>
#include <cstring>
#include <vector>

namespace esphome {
namespace wordclock_layout {

// Must match the number of rows in the words[][12] table used by the Clock
// effect (37 in the current word-clock.yaml). Changing this changes the blob
// size: bump CONFIG_VERSION and re-provision units.
static const uint8_t NUM_WORDS = 37;
static const uint8_t MAX_LEDS_PER_WORD = 12;

static const uint32_t CONFIG_MAGIC = 0x574C4B31;  // "WLK1"
static const uint8_t CONFIG_VERSION = 1;

// The emulated EEPROM sector on ESP8266 is 4096 bytes; the blob is ~450 bytes.
static const uint16_t EEPROM_SIZE = 512;

struct LayoutBlob {
  uint32_t magic;
  uint8_t version;
  int8_t words[NUM_WORDS][MAX_LEDS_PER_WORD];
  uint8_t checksum;
};

class WordClockLayout : public Component {
 public:
  void setup() override {
    EEPROM.begin(EEPROM_SIZE);
    EEPROM.get(0, blob_);

    loaded_ = blob_.magic == CONFIG_MAGIC && blob_.version == CONFIG_VERSION &&
              blob_.checksum == this->checksum_();

    if (!loaded_) {
      ESP_LOGE(TAG, "No valid word layout in flash - clock stays blank until provisioned");
      memset(blob_.words, -1, sizeof(blob_.words));
    } else {
      ESP_LOGI(TAG, "Loaded word layout from flash (version %u)", blob_.version);
    }
  }

  // Drop-in replacement for words[word][slot]; -1 means "no more LEDs".
  int8_t led_for(uint8_t word, uint8_t slot) const {
    if (word >= NUM_WORDS || slot >= MAX_LEDS_PER_WORD)
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
    for (uint8_t w = 0; w < NUM_WORDS; w++)
      for (uint8_t s = 0; s < MAX_LEDS_PER_WORD; s++)
        blob_.words[w][s] = (int8_t) flat[w * MAX_LEDS_PER_WORD + s];

    blob_.magic = CONFIG_MAGIC;
    blob_.version = CONFIG_VERSION;
    blob_.checksum = this->checksum_();

    EEPROM.put(0, blob_);
    loaded_ = EEPROM.commit();
    return loaded_;
  }

 protected:
  static constexpr const char *TAG = "wordclock_layout";
  LayoutBlob blob_{};
  bool loaded_{false};

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
