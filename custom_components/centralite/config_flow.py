from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

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
