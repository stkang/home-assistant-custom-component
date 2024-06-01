import binascii
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY
from .const import DOMAIN, TITLE, CONF_STATION_NAME
from .coordinator import AirKoreaAPI, AirKoreaError

_LOGGER = logging.getLogger(__name__)

# 사용자 입력 데이터 스키마 정의
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_STATION_NAME): str
    }
)


# API 인증을 검증하는 비동기 함수
async def async_validate_auth(api: AirKoreaAPI) -> dict[str, Any]:
    """사용자 입력을 검증하여 연결할 수 있는지 확인합니다.
    Data는 STEP_USER_DATA_SCHEMA로부터 키 값을 갖고 있습니다.
    """

    errors = {}
    try:
        await api.async_get()
    except AirKoreaError:
        errors["base"] = "invalid_login"
    finally:
        await api.close_session()
    return errors


class AirKoreaConfigFlow(ConfigFlow, domain=DOMAIN):
    """설정 흐름 클래스 정의"""
    VERSION = 1

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """초기 단계 처리"""

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        api_key = user_input[CONF_API_KEY]
        station_name = user_input[CONF_STATION_NAME]
        api = AirKoreaAPI(api_key, station_name)

        if errors := await async_validate_auth(api):
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )
        hex_station_name = binascii.hexlify(station_name.encode()).decode()
        await self.async_set_unique_id(f"{DOMAIN}_{hex_station_name}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=f"{TITLE} - {station_name}", data=user_input)
