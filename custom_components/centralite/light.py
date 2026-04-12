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

    entities = [
        CentraliteLight(device, controller, entry)
        for device in controller.loads()
        if not _is_ignored(controller.get_load_name(device), excluded_prefixes)
    ]
    async_add_entities(entities, False)


class CentraliteLight(LightEntity):
    """Representation of one Centralite load as a Home Assistant light."""

    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_should_poll = False

    def __init__(self, lj_device: int, controller, entry: ConfigEntry) -> None:
        """Initialize the HA light entity."""
        self.lj_device = lj_device
        self.controller = controller

        self._attr_name = controller.get_load_name(lj_device)
        self._attr_unique_id = f"elegance.light.{lj_device}"

        self._brightness = 0
        self._state = False

        controller.on_load_change(lj_device, self._on_load_changed)

    def _snap_brightness_to_panel_level(self, ha_brightness: int) -> int:
        """Snap HA brightness to stable Centralite panel levels."""
        if ha_brightness <= 0:
            return 0
        if ha_brightness <= 63:
            return 30
        if ha_brightness <= 127:
            return 50
        if ha_brightness <= 191:
            return 75
        return 99

    def _panel_to_ha_brightness(self, panel_level: int) -> int:
        """Convert Centralite 0..99 to HA 0..255."""
        level = max(0, min(99, int(panel_level)))
        return int(level / 99 * 255)

    def _on_load_changed(self, new_brightness) -> None:
        """Handle a spontaneous load level update from Centralite."""
        panel_level = max(0, min(99, int(new_brightness)))
        self._brightness = self._panel_to_ha_brightness(panel_level)
        self._state = panel_level != 0
        self.schedule_update_ha_state()

    @property
    def brightness(self):
        return self._brightness

    @property
    def is_on(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return {ATTR_NUMBER: self.lj_device}

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the light."""
        try:
            if ATTR_BRIGHTNESS in kwargs:
                ha_brightness = kwargs[ATTR_BRIGHTNESS]
                panel_level = self._snap_brightness_to_panel_level(ha_brightness)
            else:
                panel_level = 99

            await self.hass.async_add_executor_job(
                self.controller.activate_load_at,
                self.lj_device,
                panel_level,
                1,
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed turning on Centralite load %s: %s",
                self.lj_device,
                err,
            )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the light."""
        try:
            await self.hass.async_add_executor_job(
                self.controller.deactivate_load,
                self.lj_device,
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed turning off Centralite load %s: %s",
                self.lj_device,
                err,
            )
