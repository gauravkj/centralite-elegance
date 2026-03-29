from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import (
    CONF_INCLUDE_SCENES,
    CONF_INCLUDE_SWITCHES,
    CONF_PORT,
    DOMAIN,
)


class CentraliteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Centralite."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_PORT])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Centralite Elegance ({user_input[CONF_PORT].split('/')[-1]})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT): str,
                    vol.Optional(CONF_INCLUDE_SWITCHES, default=False): bool,
                    vol.Optional(CONF_INCLUDE_SCENES, default=False): bool,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return CentraliteOptionsFlow(config_entry)


class CentraliteOptionsFlow(OptionsFlow):
    """Handle Centralite options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_switches = self.config_entry.options.get(
            CONF_INCLUDE_SWITCHES,
            self.config_entry.data.get(CONF_INCLUDE_SWITCHES, False),
        )
        current_scenes = self.config_entry.options.get(
            CONF_INCLUDE_SCENES,
            self.config_entry.data.get(CONF_INCLUDE_SCENES, False),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_INCLUDE_SWITCHES, default=current_switches): bool,
                    vol.Optional(CONF_INCLUDE_SCENES, default=current_scenes): bool,
                }
            ),
        )
