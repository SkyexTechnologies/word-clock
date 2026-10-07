from pathlib import Path

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

wordclock_layout_ns = cg.esphome_ns.namespace("wordclock_layout")
WordClockLayout = wordclock_layout_ns.class_("WordClockLayout", cg.Component)

DEPENDENCIES = ["esp8266"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(WordClockLayout),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    # Reserve the final 4 KB of the OTA staging region for the per-device
    # layout. This project targets the 1 MB esp01_1m flash map.
    linker_script = Path(__file__).with_name("eagle.flash.1m.wordclock.ld")
    cg.add_platformio_option("board_build.ldscript", str(linker_script))

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add_library("EEPROM", None)
