"""
Support for kiturami Component.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/kiturami/
"""
import hashlib
import logging
import requests
import voluptuous as vol

from datetime import timedelta
import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import (
    ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT, HVAC_MODE_OFF, SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE)
from homeassistant.const import (
    CONF_NAME, CONF_USERNAME, CONF_PASSWORD, TEMP_CELSIUS, ATTR_TEMPERATURE)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

KITURAMI_API_URL = 'https://igs.krb.co.kr/api'
DEFAULT_NAME = 'Kiturami'

MAX_TEMP = 45
MIN_TEMP = 10
HVAC_MODE_BATH = '목욕'
STATE_HEAT = '난방'
STATE_BATH = '목욕'
STATE_RESERVATION = '24시간 예약'
STATE_RESERVATION_REPEAT = '반복 예약'
STATE_AWAY = '외출'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a kiturami."""

    name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    krb_api = KrbAPI(username, password)
    if not krb_api.login():
        _LOGGER.error("Failed to login Kiturami")
        raise PlatformNotReady

    node_id = krb_api.node_id()
    if not node_id:
        _LOGGER.error("Failed to no Kiturami")
        raise PlatformNotReady

    device = [Kiturami(name, DeviceAPI(krb_api, node_id))]

    add_entities(device, True)


class KrbAPI:
    """Kiturami Member API."""

    def __init__(self, username, password):
        """Initialize the Kiturami Member API.."""
        self.username = username
        self.password = password
        self.auth_key = ''

    def request(self, url, args):
        headers = {'Content-Type': 'application/json; charset=UTF-8',
                   'AUTH-KEY': self.auth_key}
        try:
            response = requests.post(url, headers=headers, json=args,
                                     timeout=10)
            response.raise_for_status()
            _LOGGER.debug('JSON Response: %s',
                          response.content.decode('utf8'))
            return response
        except Exception as ex:
            _LOGGER.error('Failed to Kiturami API status Error: %s', ex)
            raise

    def post(self, url, args):
        response = self.request(url, args)
        if response.status_code != 200 or not response.content.decode('utf8'):
            if self.login():
                response = self.request(url)

        return response.json()

    def login(self):
        url = '{}/member/login'.format(KITURAMI_API_URL)
        password = hashlib.sha256(self.password.encode('utf-8'))
        args = {
            'memberId': self.username,
            'password': password.hexdigest()
        }
        self.auth_key = self.post(url, args)['authKey']
        return self.auth_key

    def node_id(self):
        url = '{}/member/getMemberNormalDeviceList'.format(KITURAMI_API_URL)
        args = {
            'parentId': '1'
        }
        response = self.post(url, args)
        return response['memberDeviceList'][0]['nodeId']


class DeviceAPI:
    """Kiturami Device API."""

    def __init__(self, krb, node_id):
        """Initialize the Kiturami Member API.."""
        self.krb = krb
        self.node_id = node_id
        self.alive = {}
        self.is_alive = Throttle(MIN_TIME_BETWEEN_UPDATES)(self.is_alive)

    def is_alive(self):
        url = '{}/device/isAliveNormal'.format(KITURAMI_API_URL)
        args = {
            'nodeId': self.node_id,
            'parentId': '1'
        }
        self.alive = self.krb.post(url, args)

    def device_info(self):
        url = '{}/device/getDeviceInfo'.format(KITURAMI_API_URL)
        args = {
            'nodeId': self.node_id,
            'parentId': '1'
        }
        return self.krb.post(url, args)

    def device_mode_info(self, action_id = '0102'):
        url = '{}/device/getDeviceModeInfo'.format(KITURAMI_API_URL)
        args = {
            'nodeId': self.node_id,
            'actionId': action_id,
            'parentId': '1',
            'slaveId': '01'
        }
        return self.krb.post(url, args)

    def device_control(self, message_id, message_body):
        url = '{}/device/deviceControl'.format(KITURAMI_API_URL)
        args = {
            'nodeIds': [self.node_id],
            'messageId': message_id,
            'messageBody': message_body
        }
        return self.krb.post(url, args)

    def turn_on(self):
        self.device_control('0101', '010000000001')

    def turn_off(self):
        self.device_control('0101', '010000000002')

    def mode_heat(self, target_temp = ''):
        if not target_temp:
            target_temp = self.device_mode_info('0102')['value']
        body = '01000000{}00'.format(target_temp)
        self.device_control('0102', body)

    def mode_bath(self):
        value = self.device_mode_info('0105')['value']
        body = '00000000{}00'.format(value)
        self.device_control('0105', body)

    def mode_reservation(self):
        response = self.device_mode_info('0107')
        body = '01{}'.format(response['value'])
        self.device_control('0107', body)

    def mode_reservation_repeat(self):
        response = self.device_mode_info('0108')
        body = '01000000{}{}'.format(response['value'], response['option1'])
        self.device_control('0108', body)

    def mode_away(self):
        self.device_control('0106', '010200000000')


class Kiturami(ClimateDevice):

    def __init__(self, name, device):
        """Initialize the thermostat."""
        self._name = name
        self.device = device
        self.result = {}

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self.device.node_id

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            'node_id': self.device.node_id,
            'device_alias': self.result['deviceAlias']
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return {
            'node_id': self.device.node_id,
            'device_mode': self.result['deviceMode']
        }

    @property
    def supported_features(self):
        """Return the list of supported features."""
        features = 0
        if self.is_on:
            features |= SUPPORT_PRESET_MODE
        if self.preset_mode == STATE_HEAT:
            features |= SUPPORT_TARGET_TEMPERATURE
        return features

    @property
    def available(self):
        """Return True if entity is available."""
        alive = self.device.alive
        if not alive:
            return False
        return alive['deviceStat'] == True \
               and alive['deviceStatus'] == True \
               and alive['isAlive'] == True

    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return TEMP_CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def is_on(self):
        """Return true if heater is on."""
        return self.result['deviceMode'] != '0101'

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return int(self.result['currentTemp'], 16)

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return int(self.result['value'], 16)

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self.is_on:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT]

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if self.is_on is False:
            self.device.turn_on()
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self.device.mode_heat('{:X}'.format(int(temperature)))

    @property
    def preset_modes(self):
        """Return a list of available preset modes.
        Requires SUPPORT_PRESET_MODE.
        """
        return [STATE_HEAT, STATE_BATH, STATE_RESERVATION,
                STATE_RESERVATION_REPEAT, STATE_AWAY]
    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.
        Requires SUPPORT_PRESET_MODE.
        """
        operation_mode = self.result['deviceMode']
        if operation_mode == '0102':
            return STATE_HEAT
        elif operation_mode == '0105':
            return STATE_BATH
        elif operation_mode == '0107':
            return STATE_RESERVATION
        elif operation_mode == '0108':
            return STATE_RESERVATION_REPEAT
        elif operation_mode == '0106':
            return STATE_AWAY
        else:
            return STATE_HEAT

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""

        if self.is_on is False:
            self.device.turn_on()
        if preset_mode == STATE_HEAT:
            self.device.mode_heat()
        elif preset_mode == STATE_BATH:
            self.device.mode_bath()
        elif preset_mode == STATE_RESERVATION:
            self.device.mode_reservation()
        elif preset_mode == STATE_RESERVATION_REPEAT:
            self.device.mode_reservation_repeat()
        elif preset_mode == STATE_AWAY:
            self.device.mode_away()
        else:
            _LOGGER.error("Unrecognized operation mode: %s", preset_mode)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            self.device.turn_on()
        elif hvac_mode == HVAC_MODE_OFF:
            self.device.turn_off()

    async def async_update(self):
        """Retrieve latest state."""
        self.device.is_alive()
        self.result = self.device.device_mode_info()