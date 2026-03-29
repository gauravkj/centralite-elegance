from __future__ import annotations

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_EXCLUDE_NAMES, DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_NUMBER = "number"


def _is_ignored(name: str, excluded_prefixes: list[str]) -> bool:
    """Return True if entity name should be ignored."""
    return any(name.startswith(prefix) for prefix in excluded_prefixes)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Centralite light entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    controller = data.controller
    excluded_prefixes = entry.data.get(CONF_EXCLUDE_NAMES, [])

    entities = []
    for device in controller.loads():
        name = controller.get_load_name(device)
        if not _is_ignored(name, excluded_prefixes):
            entities.append(CentraliteLight(device, controller))

    async_add_entities(entities, True)


class CentraliteLight(LightEntity):
    """Representation of one Centralite load as a Home Assistant light."""

    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, lj_device: int, controller) -> None:
        """Initialize the HA light entity."""
        self.lj_device = lj_device
        self.controller = controller
        self._attr_name = controller.get_load_name(lj_device)
        self._attr_unique_id = f"elegance.light.{lj_device}"
        self._brightness = 0
        self._state = False

        controller.on_load_change(lj_device, self._on_load_changed)

    def _on_load_changed(self, new_brightness) -> None:
        """Handle a spontaneous load level update from Centralite."""
        panel_level = max(0, min(99, int(new_brightness)))
        self._brightness = int(panel_level / 99 * 255)
        self._state = self._brightness != 0
        self.schedule_update_ha_state()

    @property
    def brightness(self):
        """Return brightness using Home Assistant's 0 to 255 scale."""
        return self._brightness

    @property
    def is_on(self):
        """Return True if the light is on."""
        return self._brightness != 0

    @property
    def should_poll(self):
        """Return False because Centralite pushes updates."""
        return False

    @property
    def extra_state_attributes(self):
        """Expose the Centralite load number."""
        return {ATTR_NUMBER: self.lj_device}

    def turn_on(self, **kwargs):
        """Turn on the light."""
        if ATTR_BRIGHTNESS in kwargs:
            ha_brightness = kwargs[ATTR_BRIGHTNESS]
            panel_level = int(ha_brightness / 255 * 99)
            self.controller.activate_load_at(self.lj_device, panel_level, 1)
            self._brightness = ha_brightness
        else:
            self.controller.activate_load(self.lj_device)
            self._brightness = 255

        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off the light."""
        self.controller.deactivate_load(self.lj_device)
        self._state = False
        self._brightness = 0
        self.schedule_update_ha_state()

    def update(self):
        """Read the current load level from Centralite."""
        level = max(0, min(99, int(self.controller.get_load_level(self.lj_device))))
        self._brightness = int(level / 99 * 255)
        self._state = self._brightness != 0
