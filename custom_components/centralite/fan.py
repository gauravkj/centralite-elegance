"""
Support for Centralite fan entities.

This platform exposes Centralite fan capable loads as Home Assistant fan entities.

For this Centralite integration, we use the panel's practical 0 to 99 level scale.
For 4 step FSCB fans we map HA percentages to Centralite levels as:

    0%   -> 0   Off
    25%  -> 24  Low
    50%  -> 49  Medium
    75%  -> 74  Medium High
    100% -> 99  High

Default power on behavior is High.
"""

import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature

from . import CENTRALITE_CONTROLLER, CENTRALITE_DEVICES, LJDevice

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["centralite"]

ATTR_NUMBER = "number"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up Centralite fan entities."""
    controller = hass.data[CENTRALITE_CONTROLLER]

    _LOGGER.debug("fan.py setup, devices=%s", hass.data[CENTRALITE_DEVICES])

    add_entities(
        [
            CentraliteFan(device, controller)
            for device in hass.data[CENTRALITE_DEVICES]["fan"]
        ],
        True,
    )


class CentraliteFan(LJDevice, FanEntity):
    """Representation of one Centralite fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = 4

    def __init__(self, lj_device, controller):
        """Initialize the fan."""
        _LOGGER.debug("Initializing fan for load %s", lj_device)

        self._percentage = 0
        self._state = False

        self._name = controller.get_load_name(lj_device)
        if self._name == "L051":
            self._name = "Family Room Fan"
        elif self._name.startswith("L"):
            self._name = f"{self._name} Fan"

        self._attr_unique_id = f"elegance.fan.{lj_device}"

        _LOGGER.debug("  fan name=%s", self._name)
        _LOGGER.debug("  unique_id=%s", self._attr_unique_id)

        super().__init__(lj_device, controller, self._name)

        controller.on_load_change(lj_device, self._on_load_changed)

    def _panel_to_percentage(self, panel_level):
        """Convert Centralite 0 to 99 level to HA percentage."""
        level = max(0, min(99, int(panel_level)))

        if level == 0:
            return 0
        if level <= 24:
            return 25
        if level <= 49:
            return 50
        if level <= 74:
            return 75
        return 100

    def _percentage_to_panel(self, percentage):
        """Convert HA percentage to Centralite stepped 0 to 99 level."""
        pct = max(0, min(100, int(percentage)))

        if pct == 0:
            return 0
        if pct <= 25:
            return 24
        if pct <= 50:
            return 49
        if pct <= 75:
            return 74
        return 99

    def _on_load_changed(self, new_level):
        """Handle Centralite load change notification."""
        _LOGGER.debug("Notification update for fan %s", self._name)
        _LOGGER.debug("  panel level=%s", new_level)

        self._percentage = self._panel_to_percentage(new_level)
        self._state = self._percentage != 0

        _LOGGER.debug("  new HA percentage=%s", self._percentage)
        self.schedule_update_ha_state()

    @property
    def is_on(self):
        """Return True if the fan is on."""
        return self._state

    @property
    def percentage(self):
        """Return current fan percentage."""
        return self._percentage

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

    def turn_on(self, percentage=None, preset_mode=None, **kwargs):
        """Turn on the fan."""
        if percentage is None:
            panel_level = 99
            self._percentage = 100
        else:
            panel_level = self._percentage_to_panel(percentage)
            self._percentage = self._panel_to_percentage(panel_level)

        _LOGGER.debug(
            "turn_on fan=%s requested_pct=%s panel_level=%s",
            self._name,
            percentage,
            panel_level,
        )

        if panel_level == 0:
            self.controller.deactivate_load(self.lj_device)
            self._percentage = 0
            self._state = False
        else:
            self.controller.activate_load_at(self.lj_device, panel_level, 1)
            self._state = True

        self.schedule_update_ha_state()

    def set_percentage(self, percentage):
        """Set fan speed percentage."""
        panel_level = self._percentage_to_panel(percentage)

        _LOGGER.debug(
            "set_percentage fan=%s requested_pct=%s panel_level=%s",
            self._name,
            percentage,
            panel_level,
        )

        if panel_level == 0:
            self.controller.deactivate_load(self.lj_device)
            self._percentage = 0
            self._state = False
        else:
            self.controller.activate_load_at(self.lj_device, panel_level, 1)
            self._percentage = self._panel_to_percentage(panel_level)
            self._state = True

        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off the fan."""
        _LOGGER.debug("turn_off fan=%s", self._name)
        self.controller.deactivate_load(self.lj_device)
        self._percentage = 0
        self._state = False
        self.schedule_update_ha_state()

    def update(self):
        """Read the current fan level from Centralite."""
        _LOGGER.debug("Updating fan %s load %s", self._name, self.lj_device)

        level = int(self.controller.get_load_level(self.lj_device))
        self._percentage = self._panel_to_percentage(level)
        self._state = self._percentage != 0

        _LOGGER.debug(
            "update fan=%s panel_level=%s percentage=%s",
            self._name,
            level,
            self._percentage,
        )
