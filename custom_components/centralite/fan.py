from __future__ import annotations

import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_NUMBER = "number"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Centralite fan entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    controller = data.controller

    entities = [CentraliteFan(device, controller) for device in controller.fans()]
    async_add_entities(entities, False)


class CentraliteFan(FanEntity):
    """Representation of one Centralite fan."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = 4
    _attr_should_poll = False

    def __init__(self, lj_device: int, controller) -> None:
        self.lj_device = lj_device
        self.controller = controller
        self._percentage = 0
        self._state = False

        self._attr_name = controller.get_fan_name(lj_device)
        self._attr_unique_id = f"elegance.fan.{lj_device}"

        controller.on_load_change(lj_device, self._on_load_changed)

    def _panel_to_percentage(self, panel_level: int) -> int:
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

    def _percentage_to_panel(self, percentage: int) -> int:
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

    def _on_load_changed(self, new_level) -> None:
        self._percentage = self._panel_to_percentage(new_level)
        self._state = self._percentage != 0
        self.schedule_update_ha_state()

    @property
    def is_on(self):
        return self._state

    @property
    def percentage(self):
        return self._percentage

    @property
    def speed_count(self):
        return 4

    @property
    def extra_state_attributes(self):
        return {ATTR_NUMBER: self.lj_device}

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        try:
            if percentage is None:
                panel_level = 99
            else:
                panel_level = self._percentage_to_panel(percentage)

            await self.hass.async_add_executor_job(
                self.controller.activate_load_at,
                self.lj_device,
                panel_level,
                1,
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed turning on Centralite fan %s: %s",
                self.lj_device,
                err,
            )

    async def async_set_percentage(self, percentage):
        try:
            panel_level = self._percentage_to_panel(percentage)

            if panel_level == 0:
                await self.hass.async_add_executor_job(
                    self.controller.deactivate_load,
                    self.lj_device,
                )
            else:
                await self.hass.async_add_executor_job(
                    self.controller.activate_load_at,
                    self.lj_device,
                    panel_level,
                    1,
                )
        except Exception as err:
            _LOGGER.warning(
                "Failed setting Centralite fan %s percentage: %s",
                self.lj_device,
                err,
            )

    async def async_turn_off(self, **kwargs):
        try:
            await self.hass.async_add_executor_job(
                self.controller.deactivate_load,
                self.lj_device,
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed turning off Centralite fan %s: %s",
                self.lj_device,
                err,
            )
