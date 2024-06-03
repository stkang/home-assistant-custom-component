from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from .api import KrbAPI, KrbError, KrbClient
from .const import DOMAIN, PLATFORMS

type KituramiConfigEntry = ConfigEntry[KrbAPI]  # noqa: F821


async def async_setup_entry(hass: HomeAssistant, entry: KituramiConfigEntry) -> bool:
    """설정 항목을 설정합니다."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    client = KrbClient(username, password)
    try:
        await client.async_login()
    except KrbError as ex:
        raise ConfigEntryNotReady(f"귀뚜라미 로그인 실패: {ex}") from ex

    entry.runtime_data = KrbAPI(client)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KituramiConfigEntry) -> bool:
    """설정 항목을 언로드합니다."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """업데이트 리스너"""
    await hass.config_entries.async_reload(entry.entry_id)
