import hashlib
import logging
from typing import Dict, List, Optional

import aiohttp

from .const import KITURAMI_API_URL

_LOGGER = logging.getLogger(__name__)


class KrbError(Exception):
    """귀뚜라미 예외의 기본 클래스"""


class KrbClient:
    """귀뚜라미 Client"""

    def __init__(self, username, password):
        self.username = username
        self._password = password
        self.auth_key = ''

    async def _async_request(self, url, args):
        """API 요청을 보냅니다."""
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(url, headers={'Content-Type': 'application/json; charset=UTF-8',
                                                            'AUTH-KEY': self.auth_key}, json=args, timeout=10)
                _LOGGER.debug('JSON Response: %s', await response.text())
                return response
        except Exception as ex:
            _LOGGER.error('Failed to Kiturami API status Error: %s', ex)
            raise

    async def async_post(self, url, args):
        """API 요청을 보냅니다."""
        response = await self._async_request(url, args)
        if (response.status != 200 or not await response.text()) \
                and await self.async_login():
            response = await self._async_request(url, args)

        return await response.json(content_type='text/json')

    async def async_login(self):
        """로그인을 수행합니다."""
        url = f'{KITURAMI_API_URL}/member/login'
        password = hashlib.sha256(self._password.encode('utf-8'))
        args = {
            'memberId': self.username,
            'password': password.hexdigest()
        }
        response = await self._async_request(url, args)
        result = await response.json(content_type='text/json')
        self.auth_key = result['authKey']
        return self.auth_key

    async def async_get_device_list(self) -> List[Dict]:
        """장치 목록을 가져옵니다."""
        url = f'{KITURAMI_API_URL}/member/getMemberNormalDeviceList'
        args = {
            'parentId': '1'
        }
        response = await self.async_post(url, args)
        return response['memberDeviceList']


class KrbAPI:
    """귀뚜라미 API"""

    def __init__(self, client: KrbClient):
        self.client: KrbClient = client

    async def async_get_alive(self, parent_id: str, node_id: str):
        """장치가 살아 있는지 확인합니다."""
        url = f'{KITURAMI_API_URL}/device/isAliveNormal'
        args = {
            'nodeId': node_id,
            'parentId': parent_id,
        }
        return await self.client.async_post(url, args)

    async def async_get_device_info(self, node_id: str):
        """장치 정보를 가져옵니다."""
        url = f'{KITURAMI_API_URL}/device/getDeviceInfo'
        args = {
            'nodeId': node_id,
            'parentId': '1'
        }
        return await self.client.async_post(url, args)

    async def async_device_mode_info(self, parent_id: str, node_id: str, action_id='0102'):
        """장치 모드 정보를 가져옵니다."""
        url = f'{KITURAMI_API_URL}/device/getDeviceModeInfo'
        args = {
            'nodeId': node_id,
            'actionId': action_id,
            'parentId': parent_id,
            'slaveId': '01'
        }
        return await self.client.async_post(url, args)

    async def async_device_control(self, node_id: str, message_id, message_body):
        """장치를 제어합니다."""
        url = f'{KITURAMI_API_URL}/device/deviceControl'
        args = {
            'nodeIds': [node_id],
            'messageId': message_id,
            'messageBody': message_body
        }
        return await self.client.async_post(url, args)

    async def async_turn_on(self, node_id: str):
        """장치를 켭니다."""
        await self.async_device_control(node_id, '0101', '010000000001')

    async def async_turn_off(self, node_id: str):
        """장치를 끕니다."""
        await self.async_device_control(node_id, '0101', '010000000002')

    async def async_mode_heat(self, parent_id: str, node_id: str, target_temp: Optional[str] = None):
        """장치를 난방 모드로 설정합니다."""
        if not target_temp:
            response = await self.async_device_mode_info(parent_id, node_id, '0102')
            target_temp = response['value']
        body = f'01000000{target_temp}00'
        await self.async_device_control(node_id, '0102', body)

    async def async_mode_bath(self, parent_id: str, node_id: str):
        """장치를 목욕 모드로 설정합니다."""
        response = await self.async_device_mode_info(parent_id, node_id, '0105')
        value = response['value']
        body = f'00000000{value}00'
        await self.async_device_control(node_id, '0105', body)

    async def async_mode_reservation(self, parent_id: str, node_id: str):
        """장치를 예약 모드로 설정합니다."""
        response = await self.async_device_mode_info(parent_id, node_id, '0107')
        body = f'01{response['value']}'
        await self.async_device_control(node_id, '0107', body)

    async def async_mode_reservation_repeat(self, parent_id: str, node_id: str):
        """장치를 반복 예약 모드로 설정합니다."""
        response = await self.async_device_mode_info(parent_id, node_id, '0108')
        body = f'01000000{response['value']}{response['option1']}'
        await self.async_device_control(node_id, '0108', body)

    async def async_mode_away(self, node_id: str):
        """장치를 외출 모드로 설정합니다."""
        await self.async_device_control(node_id, '0106', '010200000000')
