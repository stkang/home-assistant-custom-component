import binascii
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import AIR_KOREA_API_URL, COORDINATOR_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AirKoreaError(Exception):
    """에어 코리아 예외의 기본 클래스"""


class AirKoreaAPI:
    """에어 코리아 API"""

    def __init__(self, api_key, station_name):
        """에어 코리아 API 초기화"""
        self._api_key = api_key
        self._station_name = station_name

    async def async_get(self):
        """API 정보 업데이트를 위한 업데이트 함수"""
        try:
            url = f'{AIR_KOREA_API_URL}/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty'
            async with aiohttp.ClientSession(headers={'Content-type': 'application/json'}) as session:
                response = await session.get(url, params={
                    'pageNo': '1',
                    'numOfRows': '1',
                    'ver': '1.3',
                    'dataTerm': 'daily',
                    'serviceKey': self._api_key,
                    'stationName': self._station_name,
                    'returnType': 'json',
                }, timeout=10)
                response.raise_for_status()
                res_json = await response.json()
                _LOGGER.debug('JSON Response: type %s, %s', type(res_json), res_json)
                return res_json['response']['body']['items'][0]
        except Exception as ex:
            _LOGGER.error('AirKorea API 상태 업데이트 실패 오류: %s', ex)
            raise AirKoreaError(ex) from ex


class AirKoreaCoordinator(DataUpdateCoordinator):
    """에어 코리아 데이터 업데이트 코디네이터입니다."""

    def __init__(self, hass: HomeAssistant, api: AirKoreaAPI, station_name: str):
        super().__init__(
            hass,
            _LOGGER,
            name="AirKoreaCoordinator",
            update_interval=COORDINATOR_UPDATE_INTERVAL,
        )
        self._api: AirKoreaAPI = api
        self.station_name: str = binascii.hexlify(station_name.encode()).decode()
        self._last_updated: Optional[datetime] = None

    async def _async_update_data(self) -> dict[str, Any]:
        """API 정보 업데이트를 위한 업데이트 함수"""
        try:
            if self._async_check_update():
                async with async_timeout.timeout(10):
                    result = await self._api.async_get()
                    self._last_updated = self._convert_last_updated(result['dataTime'])
                    return result
            return {}
        except AirKoreaError as err:
            raise UpdateFailed(str(err)) from err

    @staticmethod
    def _convert_last_updated(last_updated: str) -> datetime:
        """마지막 업데이트 시간을 설정합니다."""
        if '24:' in last_updated:
            return (datetime.strptime(last_updated.replace('24:', '23:'), "%Y-%m-%d %H:%M")
                    + timedelta(hours=1))
        return datetime.strptime(last_updated, "%Y-%m-%d %H:%M")

    def _async_check_update(self) -> bool:
        """마지막 업데이트 시간을 확인하여 업데이트 여부를 결정합니다. 매시 15분 내외로 업데이트합니다."""
        if not self._last_updated:
            return True
        now = datetime.now()
        return now.hour != self._last_updated.hour
