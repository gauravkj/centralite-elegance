"""
Support for Centralite lighting loads.

This platform exposes Centralite loads as Home Assistant light entities.

Centralite reports brightness on a 0 to 99 scale.
Home Assistant uses a 0 to 255 brightness scale.
This module converts between those 2 scales in both directions.
"""

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)

from . import CENTRALITE_CONTROLLER, CENTRALITE_DEVICES, LJDevice

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["centralite"]

ATTR_NUMBER = "number"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up Centralite light entities."""
    controller = hass.data[CENTRALITE_CONTROLLER]

    _LOGGER.debug("light.py setup, devices=%s", hass.data[CENTRALITE_DEVICES])

    add_entities(
        [
            CentraliteLight(device, controller)
            for device in hass.data[CENTRALITE_DEVICES]["light"]
        ],
        True,
    )


class CentraliteLight(LJDevice, LightEntity):
    """Representation of one Centralite load as a Home Assistant light."""

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, lj_device, controller):
        """Initialize the HA light entity."""
        _LOGGER.debug("Initializing light for load %s", lj_device)

        self._brightness = 0
        self._state = False
        self._name = controller.get_load_name(lj_device)
        self._attr_unique_id = f"elegance.light.{lj_device}"

        _LOGGER.debug("  load name=%s", self._name)
        _LOGGER.debug("  unique_id=%s", self._attr_unique_id)

        super().__init__(lj_device, controller, self._name)

        controller.on_load_change(lj_device, self._on_load_changed)

    def _on_load_changed(self, new_brightness):
        """Handle a spontaneous load level update from Centralite."""
        _LOGGER.debug("Notification update for %s", self._name)
        _LOGGER.debug("  panel level=%s", new_brightness)

        panel_level = max(0, min(99, int(new_brightness)))
        self._brightness = int(panel_level / 99 * 255)
        self._state = self._brightness != 0

        _LOGGER.debug("  new HA brightness=%s", self._brightness)

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
        return {
            ATTR_NUMBER: self.lj_device
        }

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
        _LOGGER.debug("Updating light %s load %s", self._name, self.lj_device)

        level = max(0, min(99, int(self.controller.get_load_level(self.lj_device))))
        self._brightness = int(level / 99 * 255)
        self._state = self._brightness != 0
