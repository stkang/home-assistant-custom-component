"""동행 복권 통합 모듈의 상수"""
from datetime import timedelta

from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN = "dh_lottery"
REFRESH_LOTTERY_SERVICE_NAME = "refresh_lottery"
BUY_LOTTO_645_SERVICE_NAME = "buy_lotto_645"

TITLE = "동행복권"
TITLE_LOTTO = "로또 6/45"
DH_LOTTERY = "DH Lottery"
DH_LOTTO_645 = "DH Lotto 6/45"

BRAND_NAME = "dh"

CONF_LOTTO_645 = "lotto_645"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

COORDINATOR_UPDATE_INTERVAL = timedelta(minutes=1)
LOTTERY_UPDATE_INTERVAL = timedelta(minutes=30)
LOTTO_645_UPDATE_INTERVAL = timedelta(minutes=30)


def get_dh_lottery_device_info(username: str) -> DeviceInfo:
    """동행 복권 엔티티에 대한 디바이스 정보를 반환합니다."""
    return DeviceInfo(
        configuration_url='https://dhlottery.co.kr',
        identifiers={(DOMAIN, username)},
        manufacturer=TITLE,
        model=DH_LOTTERY,
        name=TITLE,
    )


def get_dh_lotto_645_device_info(username: str) -> DeviceInfo:
    """Lotto 6/45 엔티티에 대한 디바이스 정보를 반환합니다."""
    return DeviceInfo(
        configuration_url='https://dhlottery.co.kr',
        identifiers={(DOMAIN, f"{username}_{CONF_LOTTO_645}")},
        manufacturer=TITLE,
        model=DH_LOTTO_645,
        name=TITLE_LOTTO,
    )
