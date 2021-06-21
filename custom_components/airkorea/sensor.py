"""Support for Air Korea Sensors."""
import logging
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_MONITORED_CONDITIONS)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

CONF_SERVICE_KEY = 'service_key'
CONF_STATION_NAME = 'station_name'
CONF_SUMMARY_INTERVAL = 'summary_interval'
CONF_MINUTELY_INTERVAL = 'minutely_interval'
CONF_SUMMARY_MON_COND = 'summary_monitored_conditions'
CONF_MINUTELY_MON_COND = 'minutely_monitored_conditions'

AIR_KOREA_API_URL = 'http://apis.data.go.kr/B552584'
DEFAULT_NAME = 'Air Korea'

MIN_TIME_BETWEEN_API_UPDATES = timedelta(seconds=30)
MIN_TIME_BETWEEN_SENSOR_UPDATES = timedelta(seconds=600)

SCAN_INTERVAL = timedelta(seconds=1800)

_MONITORED_CONDITIONS = {
    'data_time': ['Data', 'Time', '', '', 'mdi:clock-outline'],
    'so2': ['SO2', 'Value', '', 'ppm', None],
    'so2_grade': ['SO2', 'Grade', '', None, None],
    'co': ['CO', 'Value', '', 'ppm', None],
    'co_grade': ['CO', 'Grade', '', None, None],
    'o3': ['O3', 'Value', '', 'ppm', None],
    'o3_grade': ['O3', 'Grade', '', None, None],
    'no2': ['NO2', 'Value', '', 'ppm', None],
    'no2_grade': ['NO2', 'Grade', '', None, None],
    'pm10': ['PM10', 'Value', '', '㎍/㎥', None],
    'pm10_24h': ['PM10', 'Value', '24', '㎍/㎥', 'mdi:chart-bar'],
    'pm10_grade': ['PM10', 'Grade', '', None, None],
    'pm10_grade_1h': ['PM10', 'Grade', '1h', None, None],
    'pm25': ['PM25', 'Value', '', '㎍/㎥', None],
    'pm25_24h': ['PM25', 'Value', '24', '㎍/㎥', 'mdi:chart-bar'],
    'pm25_grade': ['PM25', 'Grade', '', None, None],
    'pm25_grade_1h': ['PM25', 'Grade', '1h', None, None],
    'khai': ['KHAI', 'Value', '', None, None],
    'khai_grade': ['KHAI', 'Grade', '', None, None],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_SERVICE_KEY): cv.string,
    vol.Required(CONF_STATION_NAME): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS):
        vol.All(cv.ensure_list, [vol.In(_MONITORED_CONDITIONS)]),
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a Air Korea Sensors."""

    name = config.get(CONF_NAME)
    service_key = config.get(CONF_SERVICE_KEY)
    station_name = config.get(CONF_STATION_NAME)
    monitored_conditions = config.get(CONF_MONITORED_CONDITIONS)

    sensors = []
    if monitored_conditions is not None:
        real_time_api = AirKoreaAPI(service_key, station_name)
        for variable in monitored_conditions:
            sensors += [AirKoreaSensor(
                name, variable, _MONITORED_CONDITIONS[variable],
                real_time_api)]

    add_entities(sensors, True)


def to_float(value):
    try:
        return float(value)
    except ValueError:
        return 0


class AirKoreaAPI:
    """Air Korea API."""

    def __init__(self, service_key, station_name):
        """Initialize the Air Korea API.."""
        self.service_key = service_key
        self.station_name = station_name
        self.result = {}

    @Throttle(MIN_TIME_BETWEEN_API_UPDATES)
    def update(self):
        """Update function for updating api information."""
        try:
            url = '{}/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty?' \
                  '&pageNo=1&numOfRows=1&ver=1.3&dataTerm=month' \
                  '&ServiceKey={}&stationName={}&returnType=json'
            url = url.format(AIR_KOREA_API_URL, self.service_key,
                             self.station_name)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            res_json = response.json()
            _LOGGER.debug('JSON Response: type %s, %s', type(res_json), res_json)
            self.result = res_json['response']['body']['items'][0]
        except Exception as ex:
            _LOGGER.error('Failed to update AirKorea API status Error: %s', ex)
            raise


class AirKoreaSensor(Entity):
    """Representation of a Air Korea Sensor."""

    def __init__(self, name, variable, variable_info, api):
        """Initialize the Air Korea sensor."""
        self._name = name
        self.var_id = variable
        self.var_name = variable_info[0]
        self.var_type = variable_info[1]
        self.var_period = variable_info[2]
        self.var_units = variable_info[3]
        self.var_icon = variable_info[4]
        self.api = api
        self.var_state = ''
        self.result = ''

    @property
    def entity_id(self):
        """Return the entity ID."""
        return 'sensor.{}_{}'.format(self._name, self.var_id)

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        if self.var_type == 'Value':
            return '{} {}'.format(self.var_name, self.var_period)
        return '{} {} {}'.format(self.var_name, self.var_type, self.var_period)

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self.var_icon

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self.var_units

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {('air_korea', 'quality')},
            'name': 'Air Korea',
            'manufacturer': 'data.go.kr',
            'model': 'air_korea_quality'
        }

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.var_state

    @Throttle(MIN_TIME_BETWEEN_SENSOR_UPDATES)
    def update(self):
        """Get the latest state of the sensor."""
        self.api.update()
        if self.api.result is None:
            return
        name = '{}{}{}'.format(self.var_name.lower(), self.var_type,
                               self.var_period)
        state = self.api.result[name]
        if self.var_type == 'Time':
            self.var_state = state
        elif self.var_type == 'Value':
            self.var_state = to_float(state)
            if self.var_icon is None:
                name = '{}Grade'.format(self.var_name.lower())
                if name in self.api.result:
                    self.update_state_icon(self.api.result[name])
        elif self.var_type == 'Grade':
            self.update_state_grade(state)

    def update_state_icon(self, grade):
        if grade == '1':
            self.var_icon = 'mdi:emoticon-excited'
        elif grade == '2':
            self.var_icon = 'mdi:emoticon-neutral'
        elif grade == '3':
            self.var_icon = 'mdi:emoticon-sad'
        elif grade == '4':
            self.var_icon = 'mdi:emoticon-dead'
        else:
            self.var_icon = 'mdi:emoticon-neutral'

    def update_state_grade(self, grade):
        if grade == '1':
            self.var_state = '좋음'
            self.var_icon = 'mdi:numeric-1-box-outline'
        elif grade == '2':
            self.var_state = '보통'
            self.var_icon = 'mdi:numeric-2-box-outline'
        elif grade == '3':
            self.var_state = '나쁨'
            self.var_icon = 'mdi:numeric-3-box-outline'
        elif grade == '4':
            self.var_state = '매우 나쁨'
            self.var_icon = 'mdi:numeric-4-box-outline'
        else:
            self.var_state = '알수 없음'
            self.var_icon = 'mdi:numeric-0-box-outline'
