"""
Support for Centralite scenes.
"""

import logging
import re

from homeassistant.components.scene import Scene

from . import CENTRALITE_CONTROLLER, LJDevice

DEPENDENCIES = ["centralite"]

ATTR_NUMBER = "number"

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up scenes for the Centralite platform."""
    controller = hass.data[CENTRALITE_CONTROLLER]

    devices = []

    scenes_dict = controller.scenes()
    for scene_id, name in scenes_dict.items():
        name_on = f"{name}-ON"
        name_off = f"{name}-OFF"

        devices.append(CentraliteScene(controller, scene_id, name_on))
        devices.append(CentraliteScene(controller, scene_id, name_off))

    add_entities(devices)


class CentraliteScene(LJDevice, Scene):
    """Representation of a single Centralite scene."""

    def __init__(self, controller, scene_id, name):
        """Initialize the scene."""
        self._lj = controller
        self._index = scene_id
        self._name = name

        match = re.search(r"(ON|OFF)$", self._name, re.IGNORECASE)
        matched_text = match.group(1).upper() if match else ""

        self._attr_unique_id = f"elegance.scene.{self._index}.{matched_text.lower()}"

        _LOGGER.debug("scene init name=%s", self._name)
        _LOGGER.debug("scene init index=%s", self._index)
        _LOGGER.debug("scene init unique_id=%s", self._attr_unique_id)

        super().__init__(scene_id, controller, self._name)

    @property
    def extra_state_attributes(self):
        """Return scene specific attributes."""
        return {
            ATTR_NUMBER: self._index
        }

    def activate(self):
        """Activate the scene."""
        _LOGGER.debug('Activating scene name="%s"', self._name)
        self.controller.activate_scene(self._index, self._name)

    @property
    def should_poll(self):
        """Return False because scenes do not require polling."""
        return False
