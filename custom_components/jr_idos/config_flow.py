"""Config flow for Spoje IDOS."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult


from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_SOURCE,
    CONF_DESTINATION,
    CONF_CONNECTIONS,
    CONF_OFFSET,
    DEFAULT_CONNECTIONS,
    DEFAULT_OFFSET,
    CONF_REGION,
    REGION_OPTIONS,
)

from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)

CONNECTIONS_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=2,
        max=10,
        step=1,
        mode=NumberSelectorMode.SLIDER,
    )
)

OFFSET_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=1,
        max=60,
        step=1,
        mode=NumberSelectorMode.SLIDER,
        unit_of_measurement="min",
    )
)


class JrIdosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:

        errors = {}

        if user_input is not None:

            await self.async_set_unique_id(
                (
                    f"{user_input[CONF_SOURCE]}"
                    f":"
                    f"{user_input[CONF_DESTINATION]}"
                )
                .lower()
                .strip()
            )

            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                    ): str,

                    vol.Required(
                        CONF_REGION,
                        default="idsjmk",
                    ): SelectSelector(SelectSelectorConfig(options=REGION_OPTIONS)),

                    vol.Required(
                        CONF_SOURCE,
                    ): str,

                    vol.Required(
                        CONF_DESTINATION,
                    ): str,

                    vol.Optional(
                        CONF_CONNECTIONS,
                        default=DEFAULT_CONNECTIONS,
                    ): CONNECTIONS_SELECTOR,

                    vol.Optional(
                        CONF_OFFSET,
                        default=DEFAULT_OFFSET,
                    ): OFFSET_SELECTOR,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):

        return JrIdosOptionsFlowHandler(config_entry)


class JrIdosOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:

        if user_input is not None:

            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_OFFSET,
                        default=self._config_entry.options.get(
                            CONF_OFFSET,
                            self._config_entry.data.get(CONF_OFFSET, DEFAULT_OFFSET),
                        ),
                    ): OFFSET_SELECTOR,
                }
            ),
        )