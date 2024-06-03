from typing import List

from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import DhLotteryData, DhLotteryConfigEntry, CONF_LOTTO_645, \
    DOMAIN
from .client.dh_lottery_client import DhLotteryClient
from .client.dh_lotto_645 import DhLotto645Error
from .const import BRAND_NAME, get_dh_lottery_device_info, \
    get_dh_lotto_645_device_info, BUY_LOTTO_645_SERVICE_NAME, REFRESH_LOTTERY_SERVICE_NAME


async def async_setup_entry(
        hass: HomeAssistant, entry: DhLotteryConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """설정 항목을 사용하여 버튼 엔티티를 추가합니다."""
    data: DhLotteryData = entry.runtime_data

    refresh_button = DhLotteryRefreshButton(data.lottery_coord.client)
    entities: List[Entity] = [refresh_button]
    if entry.data[CONF_LOTTO_645]:
        entities.append(DHLotto645Buy1Button(hass, data.lotto_645_coord.client))
        entities.append(DHLotto645BuyAllButton(hass, data.lotto_645_coord.client))
    async_add_entities(entities)


class DhButton(ButtonEntity):
    """동행복권 버튼 엔티티입니다."""

    def __init__(self, client: DhLotteryClient, button_id):
        self._client = client
        self.entity_id = f"button.{BRAND_NAME}_{client.username}_{button_id}"
        self._attr_unique_id = f"{BRAND_NAME}-{client.username}-{button_id}"

    @property
    def available(self) -> bool:
        """디바이스가 사용 가능한지 확인합니다."""
        return self._client.logged_in


class DhLotteryRefreshButton(DhButton):
    """동행복권 새로고침 버튼 엔티티입"""
    _attr_device_class = ButtonDeviceClass.UPDATE
    _attr_name = f"새로고침"
    _attr_icon = "mdi:refresh"

    def __init__(self, client: DhLotteryClient):
        super().__init__(client, 'refresh')
        self._attr_device_info = get_dh_lottery_device_info(client.username)

    async def async_press(self) -> None:
        """버튼을 누릅니다."""
        await self.hass.services.async_call(DOMAIN, REFRESH_LOTTERY_SERVICE_NAME)


class DHLotto645Buy1Button(DhButton):
    """로또 645 1게임 자동 구매 버튼 엔티티."""
    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_name = "1개 자동 구매"
    _attr_icon = "mdi:numeric-positive-1"

    def __init__(self, hass: HomeAssistant, client: DhLotteryClient):
        super().__init__(client, 'lotto_645_buy_1')
        self.hass = hass
        self._attr_device_info = get_dh_lotto_645_device_info(client.username)

    async def async_press(self) -> None:
        """버튼을 누릅니다."""
        result = await self.hass.services.async_call(DOMAIN, BUY_LOTTO_645_SERVICE_NAME, {
            "game_1": "자동",
        }, blocking=True, return_response=True)
        if result['result'] == 'fail':
            raise DhLotto645Error(result['message'])


class DHLotto645BuyAllButton(DhButton):
    """로또 645 모두 자동 구매 버튼 엔티티입니다."""
    """"""
    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_name = "모두 자동 구매"
    _attr_icon = "mdi:numeric"

    def __init__(self, hass: HomeAssistant, client: DhLotteryClient):
        super().__init__(client, 'lotto_645_buy_all')
        self.hass = hass
        self._attr_device_info = get_dh_lotto_645_device_info(client.username)

    async def async_press(self) -> None:
        """버튼을 누릅니다."""

        result = await self.hass.services.async_call(DOMAIN, BUY_LOTTO_645_SERVICE_NAME, {
            "game_1": "자동",
            "game_2": "자동",
            "game_3": "자동",
            "game_4": "자동",
            "game_5": "자동",
        }, blocking=True, return_response=True)
        if result['result'] == 'fail':
            raise DhLotto645Error(result['message'])
