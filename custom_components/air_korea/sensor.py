"""Support for Air Korea Sensors."""
import logging
from dataclasses import dataclass
from typing import List, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant, DOMAIN, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import AirKoreaCoordinator, AirKoreaConfigEntry
from .const import TITLE, MODEL

_LOGGER = logging.getLogger(__name__)


@dataclass
class MonitoredItem:
    """센서 모니터링 항목 클래스"""
    id: str
    data_name: str
    name: str
    period: Optional[str] = None
    device_class: Optional[SensorDeviceClass] = None
    unit: Optional[str] = None
    icon: Optional[str] = None


MONITORED_ITEMS: List[MonitoredItem] = [
    MonitoredItem(id='data_time',
                  data_name='dataTime',
                  name='측정일시',
                  icon='mdi:clock-outline'),
    MonitoredItem(id='so2',
                  data_name='so2Value',
                  name='아황산가스 농도',
                  device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
                  unit='ppm'),
    MonitoredItem(id='so2_grade',
                  data_name='so2Grade',
                  name='아황산가스 지수'),
    MonitoredItem(id='co',
                  data_name='coValue',
                  name='일산화탄소 농도',
                  device_class=SensorDeviceClass.CO,
                  unit='ppm'),
    MonitoredItem(id='co_grade',
                  data_name='coGrade',
                  name='일산화탄소 지수'),
    MonitoredItem(id='o3',
                  data_name='coValue',
                  name='오존 농도',
                  device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
                  unit='ppm'),
    MonitoredItem(id='o3_grade',
                  data_name='coGrade',
                  name='오존 지수'),
    MonitoredItem(id='no2',
                  data_name='coValue',
                  name='이산화질소 농도',
                  device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
                  unit='ppm'),
    MonitoredItem(id='no2_grade',
                  data_name='coGrade',
                  name='이산화질소 지수'),
    MonitoredItem(id='pm10',
                  data_name='pm10Value',
                  name='미세먼지(PM10) 농도',
                  device_class=SensorDeviceClass.PM10,
                  unit='µg/m³'),
    MonitoredItem(id='pm10_24h',
                  data_name='pm10Value24',
                  name='미세먼지(PM10) 24시간 예측 농도',
                  device_class=SensorDeviceClass.PM10,
                  unit='µg/m³',
                  icon='mdi:chart-bar'),
    MonitoredItem(id='pm10_grade',
                  data_name='pm10Grade',
                  name='미세먼지(PM10) 24시간 등급'),
    MonitoredItem(id='pm10_grade_1h',
                  data_name='pm10Grade1h',
                  name='미세먼지(PM10) 1시간 등급'),
    MonitoredItem(id='pm25',
                  data_name='pm25Value',
                  name='미세먼지(PM25) 농도',
                  device_class=SensorDeviceClass.PM25,
                  unit='µg/m³'),
    MonitoredItem(id='pm25_24h',
                  data_name='pm25Value24',
                  name='미세먼지(PM25) 24시간 예측 농도',
                  device_class=SensorDeviceClass.PM25,
                  unit='µg/m³',
                  icon='mdi:chart-bar'),
    MonitoredItem(id='pm25_grade',
                  data_name='pm25Grade',
                  name='미세먼지(PM25) 24시간 등급'),
    MonitoredItem(id='pm25_grade_1h',
                  data_name='pm25Grade1h',
                  name='미세먼지(PM25) 1시간 등급'),
    MonitoredItem(id='khai',
                  data_name='khaiValue',
                  name='통합대기환경수치'),
    MonitoredItem(id='khai_grade',
                  data_name='khaiGrade',
                  name='통합대기환경지수'),
]


async def async_setup_entry(
        hass: HomeAssistant, entry: AirKoreaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """설정 항목을 사용하여 센서 엔티티를 추가합니다."""
    coord: AirKoreaCoordinator = entry.runtime_data

    await coord.async_config_entry_first_refresh()
    async_add_entities([AirKoreaSensor(coord, item) for item in MONITORED_ITEMS])


def to_float(value):
    """값을 부동 소수점으로 변환합니다."""
    try:
        return float(value)
    except ValueError:
        return 0


class AirKoreaSensor(CoordinatorEntity, SensorEntity):
    """에어 코리아 센서 클래스"""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: AirKoreaCoordinator, item: MonitoredItem):
        super().__init__(coordinator)
        self._item = item
        self.entity_id = f"sensor.{DOMAIN}_{coordinator.station_name}_{item.id}"
        self._attr_unique_id = f"{DOMAIN}-{coordinator.station_name}_{item.id}"
        self._attr_name = item.name
        self._attr_icon = item.icon
        self._attr_state_class = item.device_class
        self._attr_native_unit_of_measurement = item.unit
        self._attr_device_info = DeviceInfo(
            configuration_url='https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15073861',
            identifiers={(DOMAIN, coordinator.station_name)},
            name=TITLE,
            manufacturer=TITLE,
            model=MODEL
        )

    @property
    def available(self) -> bool:
        """디바이스가 사용 가능한지 확인합니다."""
        return bool(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """데이터 업데이트 콜백을 처리합니다."""
        result = self.coordinator.data
        if self._item.data_name not in result:
            return
        state = result[self._item.data_name]
        if 'Time' in self._item.data_name:
            self._attr_native_value = state
            return

        if 'Value' in self._item.data_name:
            self._attr_native_value = to_float(state)
            if not self._attr_icon and self._item.data_name.endswith('Value'):
                data_name = self._item.data_name.replace('Value', 'Grade')
                if data_name in result:
                    self.update_state_icon(result[data_name])
            return
        if 'Grade' in self._item.data_name:
            self.update_state_grade(state)

    async def async_added_to_hass(self) -> None:
        """상태 업데이트 콜백을 등록합니다."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    def update_state_icon(self, grade):
        """상태 아이콘을 업데이트합니다."""
        if grade == '1':
            self._attr_icon = 'mdi:emoticon-excited'
        elif grade == '2':
            self._attr_icon = 'mdi:emoticon-neutral'
        elif grade == '3':
            self._attr_icon = 'mdi:emoticon-sad'
        elif grade == '4':
            self._attr_icon = 'mdi:emoticon-dead'
        else:
            self._attr_icon = 'mdi:emoticon-neutral'

    def update_state_grade(self, grade):
        """상태 등급을 업데이트합니다."""
        if grade == '1':
            self._attr_native_value = '좋음'
            self._attr_icon = 'mdi:numeric-1-box-outline'
        elif grade == '2':
            self._attr_native_value = '보통'
            self._attr_icon = 'mdi:numeric-2-box-outline'
        elif grade == '3':
            self._attr_native_value = '나쁨'
            self._attr_icon = 'mdi:numeric-3-box-outline'
        elif grade == '4':
            self._attr_native_value = '매우 나쁨'
            self._attr_icon = 'mdi:numeric-4-box-outline'
        else:
            self._attr_native_value = '알수 없음'
            self._attr_icon = 'mdi:numeric-0-box-outline'
