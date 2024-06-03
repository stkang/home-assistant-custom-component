import logging
from typing import List, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import DhLotteryConfigEntry, DhLotteryData
from .const import CONF_LOTTO_645, BRAND_NAME, \
    get_dh_lotto_645_device_info, get_dh_lottery_device_info
from .coordinator import DhLotto645Coordinator, DhLotteryCoordinator, DhCoordinator, DhLotto645BuyData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant, entry: DhLotteryConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """설정 항목을 사용하여 센서 엔티티를 추가합니다."""
    data: DhLotteryData = entry.runtime_data

    entities: List[Entity] = [
        DhDepositSensor(data.lottery_coord),
    ]
    await data.lottery_coord.async_config_entry_first_refresh()
    if entry.data[CONF_LOTTO_645]:
        await data.lotto_645_coord.async_config_entry_first_refresh()

        entities.append(DhLotto645WinningSensor(data.lotto_645_coord))
        for i in range(1, 6):
            entities.append(DhLotto645HistorySensor(data.lotto_645_coord, i))
    async_add_entities(entities)


class DhSensor(CoordinatorEntity):
    """기본 동행복권 센서 클래스"""

    def __init__(self, coordinator: DhCoordinator, sensor_id: str):
        super().__init__(coordinator)
        self.entity_id = f"sensor.{BRAND_NAME}_{coordinator.client.username}_{sensor_id}"
        self._attr_unique_id = f"{BRAND_NAME}-{coordinator.client.username}_{sensor_id}"

    @property
    def available(self) -> bool:
        """디바이스가 사용 가능한지 확인합니다."""
        return self.coordinator.client.logged_in

    async def async_added_to_hass(self) -> None:
        """상태 업데이트 콜백을 등록합니다."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()


class DhLotto645HistorySensor(DhSensor, Entity):
    """
    동행복권 구매내역 센서 클래스입니다.

    이 클래스는 동행복권의 구매 내역을 표시하는 센서를 나타냅니다.
    """

    def __init__(self, coordinator: DhLotto645Coordinator, no: int):
        super().__init__(coordinator, f'lotto_645_history_{no}')
        self._no = no
        self._attr_name = f"게임 {no}"
        self._attr_icon = "mdi:question-box-outline"
        self._attr_device_info = get_dh_lotto_645_device_info(coordinator.client.username)
        self.result: Optional[DhLotto645BuyData] = None

    @property
    def icon(self):
        """프론트엔드에서 사용할 아이콘입니다."""
        if not self.result:
            return 'mdi:close-box-outline'
        if self.result.rank == -1:
            return 'mdi:help-box-outline'
        if self.result.rank in [1, 2, 3, 4, 5]:
            return f'mdi:numeric-{self.result.rank}-box'
        return 'mdi:close-box'

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        코디네이터로부터 업데이트된 데이터를 처리하는 메소드입니다.

        구입 내역 정보를 업데이트합니다.
        """
        buy_history_this_week = self.coordinator.data["buy_history_this_week"]
        if len(buy_history_this_week) < self._no:
            return
        self.result = buy_history_this_week[self._no - 1]
        state = " ".join(map(str, self.result.game.numbers))
        if self._attr_state == state:
            return

        self._attr_name = f"{self.result.round_no}회 {self.result.game.slot}({self.result.game.mode})"
        self._attr_state = " ".join(map(str, self.result.game.numbers))
        self._attr_extra_state_attributes = {
            "추첨 회차": self.result.round_no,
            "바코드": self.result.barcode,
            "슬롯": self.result.game.slot,
            "선택": str(self.result.game.mode),
            "순위": self.result.rank,
        }
        self.async_write_ha_state()


class DhLotto645WinningSensor(DhSensor, Entity):
    """
    동행복권 당첨번호 센서 클래스입니다.

    이 클래스는 동행복권의 최근 당첨번호를 표시하는 센서를 나타냅니다.
    """
    _attr_icon = "mdi:star-circle-outline"

    def __init__(self, coordinator: DhLotto645Coordinator):
        super().__init__(coordinator, 'lotto_645_win_nums')
        self._attr_name = "최근 당첨번호"
        self._attr_device_info = get_dh_lotto_645_device_info(coordinator.client.username)

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        코디네이터로부터 업데이트된 데이터를 처리하는 메소드입니다.

        최근 당첨번호를 업데이트합니다.
        """
        if (result := self.coordinator.data["latest_winning_numbers"]) is None:
            return
        state = f'{" ".join(map(str, result.numbers))} + {result.bonus_num}'
        if self._attr_state == state:
            return

        self._attr_name = f"{result.round_no}회 당첨번호"
        self._attr_state = state
        self._attr_extra_state_attributes = {
            "추첨 회차": result.round_no,
            "추첨일": result.draw_date,
            "보너스 번호": result.bonus_num,
        }
        self.async_write_ha_state()


class DhDepositSensor(DhSensor, SensorEntity):
    """
    동행복권 예치금 센서 클래스입니다.

    이 클래스는 동행복권의 예치금 정보를 표시하는 센서를 나타냅니다.
    """

    _attr_name = "예치금"
    _attr_icon = "mdi:cash"
    _attr_native_unit_of_measurement = "원"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: DhLotteryCoordinator):
        super().__init__(coordinator, 'deposit')
        self._attr_device_info = get_dh_lottery_device_info(coordinator.client.username)

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        코디네이터로부터 업데이트된 데이터를 처리하는 메소드입니다.

        예치금 정보를 업데이트합니다.
        """
        if (balance := self.coordinator.data["balance"]) is None:
            return
        if self._attr_native_value == balance.deposit:
            return
        self._attr_native_value = balance.deposit
        self._attr_extra_state_attributes = {
            "구매 가능 금액": balance.purchase_available,
            "예약 구매 금액": balance.reservation_purchase,
            "출금 신청 중금액": balance.withdrawal_request,
            "구매 불가 금액": balance.purchase_impossible,
            "이번달 누적 구매 금액": balance.this_month_accumulated_purchase,
        }
        self.async_write_ha_state()
