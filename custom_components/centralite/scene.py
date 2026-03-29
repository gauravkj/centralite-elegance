from __future__ import annotations

import re

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_INCLUDE_SCENES, DOMAIN

ATTR_NUMBER = "number"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Centralite scene entities from a config entry."""
    if not entry.options.get(
        CONF_INCLUDE_SCENES,
        entry.data.get(CONF_INCLUDE_SCENES, False),
    ):
        return

    data = hass.data[DOMAIN][entry.entry_id]
    controller = data.controller

    entities = []
    for scene_id, name in controller.scenes().items():
        entities.append(CentraliteScene(controller, scene_id, f"{name}-ON"))
        entities.append(CentraliteScene(controller, scene_id, f"{name}-OFF"))

    async_add_entities(entities)


class CentraliteScene(Scene):
    """Representation of a single Centralite scene."""

    _attr_has_entity_name = True

    def __init__(self, controller, scene_id: str, name: str) -> None:
        """Initialize the scene."""
        self.controller = controller
        self._index = scene_id
        self._attr_name = name

        match = re.search(r"(ON|OFF)$", name, re.IGNORECASE)
        matched_text = match.group(1).lower() if match else "unknown"
        self._attr_unique_id = f"elegance.scene.{scene_id}.{matched_text}"

    @property
    def should_poll(self):
        """Return False because scenes do not require polling."""
        return False

    @property
    def extra_state_attributes(self):
        """Return scene specific attributes."""
        return {ATTR_NUMBER: self._index}

    def activate(self):
        """Activate the scene."""
        self.controller.activate_scene(self._index, self.name)
