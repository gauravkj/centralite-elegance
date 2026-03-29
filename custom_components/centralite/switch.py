"""
Support for Centralite switch entities.
"""

import logging

from homeassistant.components.switch import SwitchEntity

from . import CENTRALITE_CONTROLLER, CENTRALITE_DEVICES, LJDevice

DEPENDENCIES = ["centralite"]

ATTR_NUMBER = "number"

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Centralite switch platform."""
    controller = hass.data[CENTRALITE_CONTROLLER]

    _LOGGER.debug("switch.py setup, devices=%s", hass.data[CENTRALITE_DEVICES])

    add_entities(
        [
            CentraliteSwitch(device, controller)
            for device in hass.data[CENTRALITE_DEVICES]["switch"]
        ],
        True,
    )


class CentraliteSwitch(LJDevice, SwitchEntity):
    """Representation of a single Centralite switch."""

    def __init__(self, sw_device, controller):
        """Initialize a Centralite switch."""
        _LOGGER.debug("Initializing switch for sw_device %s", sw_device)

        self._index = sw_device
        self._state = False
        self._name = controller.get_switch_name(sw_device)

        self._attr_unique_id = f"elegance.switch.{sw_device}"

        _LOGGER.debug("  switch name=%s", self._name)
        _LOGGER.debug("  unique_id=%s", self._attr_unique_id)

        super().__init__(sw_device, controller, self._name)

        controller.on_switch_pressed(sw_device, self._on_switch_pressed)
        controller.on_switch_released(sw_device, self._on_switch_released)

    def _on_switch_pressed(self, *args):
        """Handle switch press event."""
        _LOGGER.debug("Updating pressed for %s", self._name)
        self._state = True
        try:
            self.schedule_update_ha_state()
        except Exception as err:
            _LOGGER.debug(
                "Failed schedule_update_ha_state for %s: %s",
                self._name,
                err,
            )

    def _on_switch_released(self, *args):
        """Handle switch release event."""
        _LOGGER.debug("Updating released for %s", self._name)
        self._state = False
        self.schedule_update_ha_state()

    @property
    def is_on(self):
        """Return True if the switch is pressed."""
        return self._state

    @property
    def should_poll(self):
        """Return False because Centralite pushes updates."""
        return False

    @property
    def extra_state_attributes(self):
        """Return device specific attributes."""
        return {
            ATTR_NUMBER: self._index
        }

    def turn_on(self, **kwargs):
        """Press the switch."""
        self.controller.press_switch(self._index)

    def turn_off(self, **kwargs):
        """Release the switch."""
        self.controller.release_switch(self._index)
