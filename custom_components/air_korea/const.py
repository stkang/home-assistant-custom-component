from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "air_korea"
TITLE = "에어 코리아"
MODEL = "Air Korea"

CONF_STATION_NAME = "station_name"

PLATFORMS: list[Platform] = [Platform.SENSOR]

AIR_KOREA_API_URL = 'http://apis.data.go.kr/B552584'

COORDINATOR_UPDATE_INTERVAL = timedelta(minutes=3)
