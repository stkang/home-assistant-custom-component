"""동행 복권 통합 모듈"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from .const import CONF_STATION_NAME, PLATFORMS
from .coordinator import AirKoreaAPI, AirKoreaError, AirKoreaCoordinator

_LOGGER = logging.getLogger(__name__)

type AirKoreaConfigEntry = ConfigEntry[AirKoreaCoordinator]  # noqa: F821


async def async_setup_entry(hass: HomeAssistant, entry: AirKoreaConfigEntry) -> bool:
    """설정 항목을 설정합니다."""
    api_key = entry.data[CONF_API_KEY]
    station_name = entry.data[CONF_STATION_NAME]
    api = AirKoreaAPI(api_key, station_name)
    try:
        await api.async_get()
    except AirKoreaError as ex:
        raise ConfigEntryNotReady(str(ex)) from ex

    entry.runtime_data = AirKoreaCoordinator(hass, api, station_name)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AirKoreaConfigEntry) -> bool:
    """설정 항목을 언로드합니다."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """업데이트 리스너"""
    await hass.config_entries.async_reload(entry.entry_id)
