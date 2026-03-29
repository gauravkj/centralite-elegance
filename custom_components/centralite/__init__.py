"""
Centralite Elegance / Elite / Elegance XL integration for Home Assistant.

This component initializes the Centralite controller, builds the device lists
used by the individual platforms, and loads the supported platforms:
light, switch, scene, and fan.
"""

import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_PORT
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DOMAIN = "centralite"

CONF_EXCLUDE_NAMES = "exclude_names"
CONF_INCLUDE_SWITCHES = "include_switches"
CONF_INCLUDE_SCENES = "include_scenes"

CENTRALITE_CONTROLLER = "centralite_system"
CENTRALITE_DEVICES = "centralite_devices"

CENTRALITE_COMPONENTS = [
    "light",
    "switch",
    "scene",
    "fan",
]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_PORT): cv.string,
                vol.Optional(CONF_EXCLUDE_NAMES, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_INCLUDE_SWITCHES, default=False): cv.boolean,
                vol.Optional(CONF_INCLUDE_SCENES, default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, base_config):
    """Set up the Centralite component."""
    from .pycentralite import Centralite

    config = base_config.get(DOMAIN)
    if config is None:
        _LOGGER.error("No Centralite configuration found")
        return False

    hass.data["centralite_config"] = config
    hass.data[CENTRALITE_CONTROLLER] = Centralite(config[CONF_PORT])

    controller = hass.data[CENTRALITE_CONTROLLER]

    centralite_devices = {
        "light": [],
        "switch": [],
        "scene": [],
        "fan": [],
    }

    _LOGGER.debug("Building Centralite light device list")
    for device in controller.loads():
        name = controller.get_load_name(device)
        if not is_ignored(hass, name):
            centralite_devices["light"].append(device)

    if config[CONF_INCLUDE_SCENES]:
        _LOGGER.debug("Building Centralite scene device list")
        for scene_id, scene_name in controller.scenes().items():
            if not is_ignored(hass, scene_name):
                centralite_devices["scene"].append(scene_id)

    if config[CONF_INCLUDE_SWITCHES]:
        _LOGGER.debug("Building Centralite switch device list")
        for switch_id in controller.button_switches():
            name = controller.get_switch_name(switch_id)
            if not is_ignored(hass, name):
                centralite_devices["switch"].append(switch_id)

    if hasattr(controller, "fans"):
        _LOGGER.debug("Building Centralite fan device list")
        for fan_id in controller.fans():
            name = controller.get_load_name(fan_id)
            if not is_ignored(hass, name):
                centralite_devices["fan"].append(fan_id)

    hass.data[CENTRALITE_DEVICES] = centralite_devices

    for platform in CENTRALITE_COMPONENTS:
        if platform == "switch" and not config[CONF_INCLUDE_SWITCHES]:
            continue
        if platform == "scene" and not config[CONF_INCLUDE_SCENES]:
            continue
        discovery.load_platform(hass, platform, DOMAIN, {}, config)

    return True


def is_ignored(hass, name):
    """Determine whether a load, switch, scene, or fan should be ignored."""
    if not name:
        return False

    for prefix in hass.data["centralite_config"].get(CONF_EXCLUDE_NAMES, []):
        if name.startswith(prefix):
            return True
    return False


class LJDevice(Entity):
    """Base class for Centralite entities."""

    def __init__(self, lj_device, controller, lj_device_name):
        """Initialize the base Centralite entity."""
        self.lj_device = lj_device
        self.controller = controller
        self._name = lj_device_name

    def _update_callback(self, _device):
        """Schedule a Home Assistant state update."""
        self.schedule_update_ha_state(True)

    @property
    def name(self):
        """Return the entity display name."""
        return self._name

    @property
    def should_poll(self):
        """Return whether this entity should be polled."""
        return False
