"""동행 복권 통합 모듈을 위한 설정 흐름."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from .client.dh_lottery_client import DhLotteryClient, DhLotteryError
from .const import DOMAIN, TITLE, CONF_LOTTO_645

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_LOTTO_645, default=True): bool,
    }
)


async def async_validate_login(username: str, password: str) -> dict[str, Any]:
    """사용자 입력을 검증하여 연결할 수 있는지 확인합니다.
    Data는 STEP_USER_DATA_SCHEMA로부터 키 값을 갖고 있습니다.
    """
    client = DhLotteryClient(username, password)

    errors = {}
    try:
        await client.async_login()
    except DhLotteryError as ex:
        _LOGGER.exception("동행 복권 로그인 실패: %s", ex)
        errors["base"] = "invalid_login"
    finally:
        await client.session.close()
    return errors


class DhLotteryConfigFlow(ConfigFlow, domain=DOMAIN):
    """동행 복권 설정 흐름을 처리합니다."""

    VERSION = 1

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """초기 단계 처리"""

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]

        if errors := await async_validate_login(username, password):
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors,
            )
        await self.async_set_unique_id(f"{DOMAIN}_{username}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=f"{TITLE} ({username})", data=user_input)
