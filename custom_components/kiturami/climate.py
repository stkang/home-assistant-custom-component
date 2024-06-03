import asyncio
import datetime
import logging
from datetime import timedelta
from enum import StrEnum
from typing import Optional

from homeassistant.components.climate import (
    ClimateEntity)
from homeassistant.components.climate.const import (
    HVACMode, ClimateEntityFeature)
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import KituramiConfigEntry, KrbAPI, DOMAIN
from .const import TITLE, MODEL, MIN_TEMP, MAX_TEMP

_LOGGER = logging.getLogger(__name__)


class PresetMode(StrEnum):
    """Preset modes."""
    HEAT = "난방"
    BATH = "목욕"
    RESERVATION = "24시간 예약"
    RESERVATION_REPEAT = "반복 예약"
    AWAY = "외출"


async def async_setup_entry(
        hass: HomeAssistant, entry: KituramiConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """설정 항목을 사용하여 플랫폼을 설정합니다."""
    api: KrbAPI = entry.runtime_data
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    devices = await api.client.async_get_device_list()

    async_add_entities([KituramiClimate(api, device["parentId"], device["nodeId"], device["deviceAlias"], scan_interval)
                        for device in devices], True)


class KituramiClimate(ClimateEntity):
    """ 귀뚜라미 Climate 클래스"""
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, api: KrbAPI, parent_id: str, node_id: str, name: str, _min_time_between_updates: int):
        self._api: KrbAPI = api
        self._min_time_between_updates: datetime.timedelta = timedelta(minutes=_min_time_between_updates)
        self._parent_id = parent_id
        self._node_id = node_id
        self.entity_id = f"climate.{DOMAIN}_{node_id.replace(':', '_')}"
        self._attr_unique_id = f"{DOMAIN}-{node_id}"
        self._attr_name = f'{TITLE} {name}'
        self._attr_device_info = DeviceInfo(
            configuration_url='https://krb.co.kr',
            identifiers={(DOMAIN, node_id)},
            name=TITLE,
            manufacturer=TITLE,
            model=MODEL,
        )
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_preset_modes = [PresetMode.HEAT, PresetMode.BATH, PresetMode.RESERVATION,
                                   PresetMode.RESERVATION_REPEAT, PresetMode.AWAY]
        self._attr_precision = 1
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP
        self._attr_target_temperature_step = 1
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        self._req_mode: Optional[str] = None
        self._alive = {}
        self._result = {}
        self._last_updated: Optional[datetime.datetime] = None

    @property
    def device_state_attributes(self):
        """장치의 상태 속성을 반환합니다."""
        return {
            'parent_id': self._parent_id,
            'node_id': self._node_id,
            "user_name": self._api.client.username,
            'device_mode': self._result['deviceMode'],
            'last_updated': self._last_updated,
        }

    @property
    def supported_features(self):
        """지원되는 기능 목록을 반환합니다."""
        features = 0
        if self.is_on:
            features |= ClimateEntityFeature.PRESET_MODE
        if self.preset_mode == PresetMode.HEAT:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        return features

    @property
    def available(self):
        """장치가 사용 가능한지 확인합니다."""
        return self._alive['deviceStat'] and self._alive['deviceStatus'] and self._alive['isAlive']

    @property
    def is_on(self):
        """히터가 켜져 있으면 true를 반환합니다."""
        return self._result['deviceMode'] != '0101'

    @property
    def current_temperature(self):
        """현재 온도를 반환합니다."""
        return int(self._result['currentTemp'], 16)

    @property
    def target_temperature(self):
        """히터가 도달하려고 하는 온도를 반환합니다."""
        return int(self._result['value'], 16)

    @property
    def hvac_mode(self):
        """현재 hvac 모드를 반환합니다."""
        if self.is_on:
            return HVACMode.HEAT
        return HVACMode.OFF

    async def async_set_temperature(self, **kwargs):
        """새 목표 온도를 설정합니다."""
        if self.is_on is False:
            await self._api.async_turn_on(self._node_id)
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        self._req_mode = '0102'
        await self._api.async_mode_heat(self._parent_id, self._node_id, '{:X}'.format(int(temperature)))

    @property
    def preset_mode(self):
        """현재 프리셋 모드를 반환합니다."""
        operation_mode = self._result['deviceMode']
        if operation_mode == '0102':
            return PresetMode.HEAT
        elif operation_mode == '0105':
            return PresetMode.BATH
        elif operation_mode == '0107':
            return PresetMode.RESERVATION
        elif operation_mode == '0108':
            return PresetMode.RESERVATION_REPEAT
        elif operation_mode == '0106':
            return PresetMode.AWAY
        else:
            return PresetMode.HEAT

    async def async_set_preset_mode(self, preset_mode):
        """새로운 목표 프리셋 모드를 설정합니다."""
        if self.is_on is False:
            self._req_mode = '0102'
            await self._api.async_turn_on(self._node_id)
            await asyncio.sleep(1)
        if preset_mode == PresetMode.HEAT:
            self._req_mode = '0102'
            await self._api.async_mode_heat(self._parent_id, self._node_id)
        elif preset_mode == PresetMode.BATH:
            self._req_mode = '0105'
            await self._api.async_mode_bath(self._parent_id, self._node_id)
        elif preset_mode == PresetMode.RESERVATION:
            self._req_mode = '0107'
            await self._api.async_mode_reservation(self._parent_id, self._node_id)
        elif preset_mode == PresetMode.RESERVATION_REPEAT:
            self._req_mode = '0108'
            await self._api.async_mode_reservation_repeat(self._parent_id, self._node_id)
        elif preset_mode == PresetMode.AWAY:
            self._req_mode = '0106'
            await self._api.async_mode_away(self._node_id)
        else:
            _LOGGER.error(f"알 수 없는 작업 모드: {preset_mode}")

    async def async_set_hvac_mode(self, hvac_mode):
        """새로운 hvac 모드를 설정합니다."""
        if hvac_mode == HVACMode.HEAT:
            self._req_mode = '0102'
            await self._api.async_turn_on(self._node_id)
        elif hvac_mode == HVACMode.OFF:
            self._req_mode = '0101'
            await self._api.async_turn_off(self._node_id)
        await asyncio.sleep(1)

    async def async_update(self):
        """최신 상태를 업데이트 합니다.
         {'studyYn': 'Y', 'code': '100', 'deviceAlias': '보일러 1', 'message': 'Success.','slaveId': '01', 'deviceMode': '0101', 'slaveAlias': 'st-kiturami',
         'option3': '01', 'actionId': '0102', 'option1': '00', 'currentTemp': '18', 'option2': '00', 'nodeId': '12010100:12:005321', 'value': '18'}
        """
        now = datetime.datetime.now()
        if not self._req_mode and self._last_updated and now - self._last_updated < self._min_time_between_updates:
            return
        self._alive = await self._api.async_get_alive(self._parent_id, self._node_id)
        for try_cnt in range(3):
            self._result = await self._api.async_device_mode_info(self._parent_id, self._node_id)
            if not self._req_mode or self._result['deviceMode'] == self._req_mode:
                self._last_updated = now
                break
            await asyncio.sleep(1)

        self._req_mode = None
