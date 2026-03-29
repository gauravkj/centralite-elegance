from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_EXCLUDE_NAMES, CONF_INCLUDE_SWITCHES, DOMAIN

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
    """Set up Centralite switch entities from a config entry."""
    if not entry.data.get(CONF_INCLUDE_SWITCHES, False):
        return

    data = hass.data[DOMAIN][entry.entry_id]
    controller = data.controller
    excluded_prefixes = entry.data.get(CONF_EXCLUDE_NAMES, [])

    entities = []
    for device in controller.button_switches():
        name = controller.get_switch_name(device)
        if not _is_ignored(name, excluded_prefixes):
            entities.append(CentraliteSwitch(device, controller))

    async_add_entities(entities, True)


class CentraliteSwitch(SwitchEntity):
    """Representation of a single Centralite switch."""

    _attr_has_entity_name = True

    def __init__(self, sw_device: int, controller) -> None:
        """Initialize a Centralite switch."""
        self._index = sw_device
        self.controller = controller
        self._state = False
        self._attr_name = controller.get_switch_name(sw_device)
        self._attr_unique_id = f"elegance.switch.{sw_device}"

        controller.on_switch_pressed(sw_device, self._on_switch_pressed)
        controller.on_switch_released(sw_device, self._on_switch_released)

    def _on_switch_pressed(self, *args):
        """Handle switch press event."""
        self._state = True
        self.schedule_update_ha_state()

    def _on_switch_released(self, *args):
        """Handle switch release event."""
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
        return {ATTR_NUMBER: self._index}

    def turn_on(self, **kwargs):
        """Press the switch."""
        self.controller.press_switch(self._index)

    def turn_off(self, **kwargs):
        """Release the switch."""
        self.controller.release_switch(self._index)
