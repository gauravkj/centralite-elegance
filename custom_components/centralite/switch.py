from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_INCLUDE_SWITCHES, DOMAIN

ATTR_NUMBER = "number"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Centralite switch entities from a config entry."""
    if not entry.options.get(
        CONF_INCLUDE_SWITCHES,
        entry.data.get(CONF_INCLUDE_SWITCHES, False),
    ):
        return

    data = hass.data[DOMAIN][entry.entry_id]
    controller = data.controller

    entities = [CentraliteSwitch(device, controller) for device in controller.button_switches()]
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

    def _on_switch_pressed(self, *args) -> None:
        """Handle switch press event."""
        self._state = True
        self.schedule_update_ha_state()

    def _on_switch_released(self, *args) -> None:
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
        """Return switch specific attributes."""
        return {ATTR_NUMBER: self._index}

    def turn_on(self, **kwargs):
        """Press the switch."""
        self.controller.press_switch(self._index)

    def turn_off(self, **kwargs):
        """Release the switch."""
        self.controller.release_switch(self._index)
