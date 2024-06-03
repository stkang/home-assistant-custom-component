"""동행 복권 통합 모듈"""

import logging
from dataclasses import dataclass
from typing import Optional, List

import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant, ServiceResponse, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady
from .client.dh_lottery_client import DhLotteryClient, DhLotteryError
from .client.dh_lotto_645 import DhLotto645SelMode, DhLotto645
from .const import DOMAIN, PLATFORMS, CONF_LOTTO_645, BUY_LOTTO_645_SERVICE_NAME, REFRESH_LOTTERY_SERVICE_NAME
from .coordinator import DhLotto645Coordinator, DhLotteryCoordinator

_LOGGER = logging.getLogger(__name__)

type DhLotteryConfigEntry = ConfigEntry[DhLotteryData]  # noqa: F821


@dataclass
class DhLotteryData:
    """DH Lottery data class."""
    lottery_coord: DhLotteryCoordinator = None
    lotto_645_coord: Optional[DhLotto645Coordinator] = None


BUY_LOTTO_645_SCHEMA = vol.Schema({
    vol.Required("game_1"): str,
    vol.Optional("game_2"): str,
    vol.Optional("game_3"): str,
    vol.Optional("game_4"): str,
    vol.Optional("game_5"): str,
})


async def async_setup_entry(hass: HomeAssistant, entry: DhLotteryConfigEntry) -> bool:
    """설정 항목을 설정합니다."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    client = DhLotteryClient(username, password)
    try:
        await client.async_login()
    except DhLotteryError as ex:
        raise ConfigEntryNotReady(f"동행 복권 로그인 실패: {ex}") from ex

    data = DhLotteryData(DhLotteryCoordinator(hass, client))
    if entry.data[CONF_LOTTO_645]:
        data.lotto_645_coord = DhLotto645Coordinator(hass, client)
    entry.runtime_data = data

    await _async_setup_service(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DhLotteryConfigEntry) -> bool:
    """설정 항목을 언로드합니다."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """업데이트 리스너"""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_setup_service(hass: HomeAssistant, entry: DhLotteryConfigEntry) -> None:
    """서비스를 설정합니다."""
    data: DhLotteryData = entry.runtime_data

    async def _async_lottery_refresh(call: ServiceCall) -> ServiceResponse:
        """로또 정보를 새로고침합니다."""
        await data.lottery_coord.async_clear_refresh()
        if entry.data[CONF_LOTTO_645]:
            await data.lotto_645_coord.async_clear_refresh()

    async def _async_buy_lotto_645(call: ServiceCall) -> ServiceResponse:
        """로또 6/45를 구매합니다."""
        try:
            items: List[DhLotto645.Slot] = []
            for i in range(1, 6):
                if f"game_{i}" in call.data:
                    texts = call.data[f"game_{i}"].strip().split(',')
                    sel_mode = DhLotto645SelMode(texts[0])
                    if sel_mode == DhLotto645SelMode.AUTO:
                        items.append(DhLotto645.Slot(DhLotto645SelMode.AUTO))
                    else:
                        items.append(DhLotto645.Slot(sel_mode, [int(text) for text in texts[1:]]))
            result = await data.lotto_645_coord.lotto_645.async_buy(items)
            message = (
                f"제 {result.round_no}회\n"
                f"발행일: {result.issue_dt}\n"
                f"바코드: {result.barcode}\n"
                f"번호:\n"
                "\n".join([f"{game.slot} {game.mode} {' '.join(map(str, game.numbers))}" for game in result.games])
            )
            persistent_notification.async_create(hass, message, "로또 6/45 구매", call.context.id)
            return {
                'result': 'success',
                'value': result.to_dict(),
            }
        except Exception as e:
            persistent_notification.async_create(hass, str(e), "로또 6/45 구매 실패", call.context.id)
            return {
                'result': 'fail',
                'message': str(e),
            }
        finally:
            await data.lottery_coord.async_clear_refresh()
            await data.lotto_645_coord.async_clear_refresh()

    hass.services.async_register(
        DOMAIN,
        REFRESH_LOTTERY_SERVICE_NAME,
        _async_lottery_refresh,
    )
    if entry.data[CONF_LOTTO_645]:
        hass.services.async_register(
            DOMAIN,
            BUY_LOTTO_645_SERVICE_NAME,
            _async_buy_lotto_645,
            schema=BUY_LOTTO_645_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
