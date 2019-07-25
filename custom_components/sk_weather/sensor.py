"""Support for SK Weather Sensors."""
import logging
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_LATITUDE, CONF_LONGITUDE)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

CONF_APP_KEY = 'app_key'
CONF_SUMMARY_INTERVAL = 'summary_interval'
CONF_MINUTELY_INTERVAL = 'minutely_interval'
CONF_SUMMARY_MON_COND = 'summary_monitored_conditions'
CONF_MINUTELY_MON_COND = 'minutely_monitored_conditions'

SK_WEATHER_API_URL = 'https://api2.sktelecom.com'
DEFAULT_NAME = 'SK Weather'

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)
SCAN_INTERVAL = timedelta(seconds=600)

_SUMMARY_MON_COND = {
    'summary_time': ['Summary', 'Time', '', None, 'mdi:clock-outline'],
    'today_sky': ['Today', 'Sky', '', None, None],
    'today_tmax': ['Today', 'Temperature', 'Max', '°C',
                   'mdi:thermometer-lines'],
    'today_tmin': ['Today', 'Temperature', 'Min', '°C', 'mdi:thermometer'],
    'tomorrow_sky': ['Tomorrow', 'Sky', '', None, None],
    'tomorrow_tmax': ['Tomorrow', 'Temperature', 'Max', '°C',
                      'mdi:thermometer-lines'],
    'tomorrow_tmin': ['Tomorrow', 'Temperature', 'Min', '°C',
                      'mdi:thermometer']
}
_MINUTELY_MON_COND = {
    'minutely_time': ['Minutely', 'Time', '', None, 'mdi:clock-outline'],
    'now_sky': ['Now', 'Sky', '', None, None],
    'now_temp': ['Now', 'Temperature', '', '°C', 'mdi:thermometer'],
    'now_humidity': ['Now', 'Humidity', '', '%', 'mdi:water-percent'],
    'now_wind_direction': ['Now', 'Wind', 'Direction', 'degree',
                           'mdi:sign-direction'],
    'now_wind_speed': ['Now', 'Wind', 'Speed', 'm/s', 'mdi:weather-windy'],
    'now_precipitation': ['Now', 'Precipitation', 'Since On Time', 'mm',
                          'mdi:water'],
    'now_pressure_surface': ['Now', 'Pressure', 'Surface', 'Ps', ''],
    'now_pressure_sea_level': ['Now', 'Pressure', 'Sea Level', 'SLP', ''],
    'now_lightning': ['Now', 'Lightning', '', None, 'mdi:weather-lightning']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_APP_KEY): cv.string,
    vol.Optional(CONF_SUMMARY_INTERVAL, default=timedelta(seconds=600)):
        vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_MINUTELY_INTERVAL, default=timedelta(seconds=600)):
        vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_SUMMARY_MON_COND):
        vol.All(cv.ensure_list, [vol.In(_SUMMARY_MON_COND)]),
    vol.Optional(CONF_MINUTELY_MON_COND):
        vol.All(cv.ensure_list, [vol.In(_MINUTELY_MON_COND)]),
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a SK Weather Sensors."""

    name = config.get(CONF_NAME)
    app_key = config.get(CONF_APP_KEY)
    lat = config.get(CONF_LATITUDE, hass.config.latitude)
    lon = config.get(CONF_LONGITUDE, hass.config.longitude)
    summary_interval = config.get(CONF_SUMMARY_INTERVAL)
    minutely_interval = config.get(CONF_MINUTELY_INTERVAL)
    summary_monitored_conditions = config.get(CONF_SUMMARY_MON_COND)
    minutely_monitored_conditions = config.get(CONF_MINUTELY_MON_COND)

    api = SKWeatherAPI(app_key)

    sensors = []
    if summary_monitored_conditions is not None:
        summary_api = SKWeatherSummaryAPI(lat, lon, api)
        for variable in summary_monitored_conditions:
            sensors += [SKWeatherSummarySensor(
                    name, variable, _SUMMARY_MON_COND[variable],
                    summary_api, summary_interval)]

    if minutely_monitored_conditions is not None:
        url = '/weather/code/grid?version=2&lat={}&lon={}'.format(lat, lon)
        grid = api.get(url)['weather']['grid'][0]
        minutely_api = SKWeatherMinutelyAPI(lat, lon, grid, api)
        for variable in minutely_monitored_conditions:
            sensors += [SKWeatherMinutelySensor(
                name, variable, _MINUTELY_MON_COND[variable],
                grid, minutely_api, minutely_interval)]

    add_entities(sensors, True)


def get_sky_icon(sky_code):
    sky_code = sky_code[4:]
    if sky_code == 'D01' or sky_code == 'M01' or sky_code == 'A01':
        return 'mdi:weather-sunny'
    if sky_code == 'D02' or sky_code == 'M02' or sky_code == 'A02':
        return 'mdi:weather-partlycloudy'
    if sky_code == 'D03' or sky_code == 'M03' or sky_code == 'A03':
        return 'mdi:weather-cloudy'
    if sky_code == 'D04' or sky_code == 'M04' or sky_code == 'A07':
        return 'mdi:weather-fog'
    if sky_code == 'D05' or sky_code == 'M05'\
            or sky_code == 'A04' or sky_code == 'A08':
        return 'mdi:weather-pouring'
    if sky_code == 'D06' or sky_code == 'M06'\
            or sky_code == 'A05' or sky_code == 'A09' or sky_code == 'A13':
        return 'mdi:weather-snowy'
    if sky_code == 'D07' or sky_code == 'M07'\
            or sky_code == 'A06' or sky_code == 'A10' or sky_code == 'A14':
        return 'mdi:weather-snowy-rainy'
    if sky_code == 'A11':
        return 'mdi:weather-lightning'
    if sky_code == 'A12':
        return 'mdi:weather-lightning-rainy'


class SKWeatherAPI:
    """SK Weather API."""
    def __init__(self, app_key):
        """Initialize the SK Weather API.."""
        self.app_key = app_key

    def get(self, url):
        headers = {'appKey': '{}'.format(self.app_key)}
        try:
            response = requests.get(
                '{}{}'.format(SK_WEATHER_API_URL, url),
                headers=headers, timeout=10)
            response.raise_for_status()
            _LOGGER.debug('JSON Response: %s', response.content.decode('utf8'))
            return response.json()
        except Exception as ex:
            _LOGGER.error('Failed to update Weather API status Error: %s', ex)
            raise


class SKWeatherSummaryAPI:
    """Representation of a SK Weather Summary Api."""

    def __init__(self, lat, lon, api):
        """Initialize of a SK Weather Summary Api."""
        self.lat = lat
        self.lon = lon
        self.api = api
        self.result = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update function for updating api information."""
        url = '/weather/summary?version=2&lat={}&lon={}' \
            .format(self.lat, self.lon)
        self.result = self.api.get(url)['weather']['summary'][0]


class SKWeatherMinutelyAPI:
    """Representation of a SK Weather Minutely Api."""

    def __init__(self, lat, lon, grid, api):
        """Initialize of a SK Weather Minutely Api."""
        self.lat = lat
        self.lon = lon
        self.city = grid['city']
        self.county = grid['county']
        self.village = grid['village']
        self.api = api
        self.result = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update function for updating api information."""
        url = '/weather/current/minutely' \
              '?version=2&lat={}&lon={}&city={}&county={}&village={}' \
            .format(self.lat, self.lon, self.city, self.county, self.village)
        self.result = self.api.get(url)['weather']['minutely'][0]


class SKWeatherSensor(Entity):
    """Representation of a SK Weather Sensor."""

    def __init__(self, name, variable, variable_info):
        """Initialize the SK Weather sensor."""
        self._name = name
        self.var_id = variable
        self.var_period = variable_info[0]
        self.var_type = variable_info[1]
        self.var_detail = variable_info[2]
        self.var_units = variable_info[3]
        self.var_icon = variable_info[4]
        self.var_state = None

    @property
    def entity_id(self):
        """Return the entity ID."""
        return 'sensor.{}_{}'.format(self._name, self.var_id)

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return '{} {} {}'.format(self.var_period, self.var_type,
                                 self.var_detail)

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self.var_icon

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self.var_units

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.var_state


class SKWeatherSummarySensor(SKWeatherSensor):
    """Representation of a SK Weather Summary Sensor."""

    def __init__(self, name, variable, variable_info, api, interval):
        """Initialize the SK Weather Summary Sensor."""
        super().__init__(name, variable, variable_info)
        self.api = api
        self.update = Throttle(interval)(self.update)

    def update(self):
        """Get the latest state of the sensor."""
        if self.api is None:
            return
        self.api.update()

        if self.var_type == 'Time':
            self.var_state = self.api.result['timeRelease']
            return

        result = self.api.result[self.var_period.lower()]
        if self.var_type == 'Sky':
            sky = result['sky']
            self.var_state = sky['name']
            self.var_icon = get_sky_icon(sky['code'])
        else:
            temp = result['temperature']
            if self.var_detail == 'Max':
                self.var_state = round(float(temp['tmax']), 1)
            else:
                self.var_state = round(float(temp['tmin']), 1)


class SKWeatherMinutelySensor(SKWeatherSensor):
    """Representation of a SK Weather Minutely Sensor."""

    def __init__(self, name, variable, variable_info, grid, api, interval):
        """Initialize the SK Weather Summary Sensor."""
        super().__init__(name, variable, variable_info)
        self.city = grid['city']
        self.county = grid['county']
        self.village = grid['village']
        self.api = api
        self.update = Throttle(interval)(self.update)

    def update(self):
        """Get the latest state of the sensor."""
        if self.api is None:
            return
        self.api.update()

        if self.var_type == 'Time':
            self.var_state = self.api.result['timeObservation']
            return
        result = self.api.result[self.var_type.lower()]
        if self.var_type == 'Sky':
            self.var_state = result['name']
            self.var_icon = get_sky_icon(result['code'])
        elif self.var_type == 'Temperature':
            self.var_state = round(float(result['tc']), 1)
        elif self.var_type == 'Humidity':
            self.var_state = result
        elif self.var_type == 'Wind':
            if self.var_detail == 'Direction':
                self.var_state = round(float(result['wdir']), 1)
            else:
                self.var_state = round(float(result['wspd']), 1)
        elif self.var_type == 'Precipitation':
            self.var_state = round(float(result['sinceOntime']), 1)
            p_type = result['type']
            if p_type == 0:
                self.var_units = 'mm'
                self.var_icon = 'mdi:weather-sunny'
            elif p_type == 1:
                self.var_units = 'mm'
                self.var_icon = 'mdi:weather-rainy'
            elif p_type == 2:
                self.var_units = 'mm'
                self.var_icon = 'mdi:weather-snowy'
            elif p_type == 3:
                self.var_units = 'cm'
                self.var_icon = 'mdi:weather-snowy-rainy'
        elif self.var_type == 'Pressure':
            if self.var_detail == 'Surface':
                self.var_state = round(float(result['surface']), 1)
            else:
                self.var_state = round(float(result['seaLevel']), 1)
        elif self.var_type == 'Lightning':
            if result == '1':
                self.var_state = 'Exist'
            else:
                self.var_state = 'None'
