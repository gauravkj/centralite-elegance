from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_PORT, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


@dataclass
class CentraliteData:
    """Runtime data for the Centralite integration."""

    controller: object


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Centralite."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Centralite from a config entry."""
    from .pycentralite import Centralite

    try:
        controller = Centralite(entry.data[CONF_PORT])
    except Exception as err:
        _LOGGER.error("Failed to connect to Centralite on %s: %s", entry.data[CONF_PORT], err)
        raise ConfigEntryNotReady(
            f"Failed to connect to Centralite on {entry.data[CONF_PORT]}"
        ) from err

    await hass.async_add_executor_job(controller.load_local_names)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = CentraliteData(controller=controller)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Centralite config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
