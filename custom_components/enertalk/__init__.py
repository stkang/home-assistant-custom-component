"""The Enertalk integration."""
import asyncio
import logging

import voluptuous as vol

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
)
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow, \
    config_validation as cv

from . import api, config_flow
from .const import (
    AUTH,
    MONITORED_CONDITIONS,
    CONF_REAL_TIME_INTERVAL,
    CONF_BILLING_INTERVAL,
    DATA_CONF,
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
)

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
                vol.Optional(
                    CONF_REAL_TIME_INTERVAL, default=timedelta(seconds=10)
                ): vol.All(cv.time_period, cv.positive_timedelta),
                vol.Optional(
                    CONF_BILLING_INTERVAL, default=timedelta(seconds=1800)
                ): vol.All(cv.time_period, cv.positive_timedelta),
                vol.Optional(CONF_MONITORED_CONDITIONS):
                    vol.All(cv.ensure_list, [vol.In(MONITORED_CONDITIONS)]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the EnerTalk component."""
    hass.data[DOMAIN] = {
        DATA_CONF: config[DOMAIN]
    }

    if DOMAIN not in config:
        return True

    config_flow.EnerTalkFlowHandler.async_register_implementation(
        hass,
        config_entry_oauth2_flow.LocalOAuth2Implementation(
            hass,
            DOMAIN,
            config[DOMAIN][CONF_CLIENT_ID],
            config[DOMAIN][CONF_CLIENT_SECRET],
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up EnerTalk from a config entry."""
    impl = await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass, entry
    )

    hass.data[DOMAIN][entry.entry_id] = {
        AUTH: api.ConfigEntryEnerTalkAuth(hass, entry, impl)
    }

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    await asyncio.gather(
        hass.config_entries.async_forward_entry_unload(entry, "sensor")
    )
    hass.data[DOMAIN].pop(entry.entry_id)

    return True
