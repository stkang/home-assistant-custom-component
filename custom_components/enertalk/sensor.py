"""Support for the EnerTalk Sensor."""

import logging
from datetime import datetime, timedelta

from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from .const import (
    AUTH,
    DOMAIN,
    MANUFACTURER,
    DATA_CONF,
    REAL_TIME_MON_COND,
    BILLING_MON_COND,
    CONF_REAL_TIME_INTERVAL,
    CONF_BILLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Netatmo weather and homecoach platform."""

    data_conf = hass.data[DOMAIN][DATA_CONF]
    monitored_conditions = data_conf[CONF_MONITORED_CONDITIONS]
    real_time_interval = data_conf[CONF_REAL_TIME_INTERVAL]
    billing_interval = data_conf[CONF_BILLING_INTERVAL]

    auth = hass.data[DOMAIN][entry.entry_id][AUTH]

    def find_entities(device):
        """Find all entities."""
        entities = []
        for variable in monitored_conditions:
            if variable in REAL_TIME_MON_COND:
                entities += [
                    EnerTalkRealTimeSensor(
                        device, variable, REAL_TIME_MON_COND[variable],
                        auth, real_time_interval
                    )
                ]

        billing_api = {}
        for variable in monitored_conditions:
            if variable in BILLING_MON_COND:
                billing_type = BILLING_MON_COND[variable][0]
                if billing_type not in billing_api:
                    billing_api[billing_type] = EnerBillingApi(
                        auth, device, billing_type, billing_interval)
                entities += [
                    EnerTalkBillingSensor(
                        device, variable,
                        BILLING_MON_COND[variable], billing_api[billing_type]
                    )
                ]
        return entities

    def get_entities():
        from pytz import timezone
        """Retrieve EnerTalk entities."""
        entities = []

        devices = auth.get('sites')
        for device in devices:
            device['timezone'] = timezone(device['timezone'])
            entities.extend(find_entities(device))

        return entities

    async_add_entities(await hass.async_add_executor_job(get_entities), True)


class EnerTalkSensor(Entity):
    """Representation of a EnerTalk Sensor."""

    def __init__(self, device, variable, variable_info):
        """Initialize the EnerTalk sensor."""
        self._device = device
        self._name = self._device['name'].lower()
        self.var_id = variable
        self.var_period = variable_info[0]
        self.var_type = variable_info[1]
        self.var_units = variable_info[2]
        self.var_icon = variable_info[3]

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f'{DOMAIN}_{self._name}_{self.var_id}'

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return f'{MANUFACTURER} {self.var_period} {self.var_type}'

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
            "identifiers": {(DOMAIN, self._device['id'])},
            'name': f'{MANUFACTURER} ({self._name})',
            'manufacturer': MANUFACTURER,
            'model': self._device['description'],
            'country': self._device['country'],
            'timezone': self._device['timezone'],
            'description': self._device['description']
        }


class EnerBillingApi:
    """Class to interface with EnerTalk Billing API."""

    def __init__(self, api, device, billing_type, interval):
        """Initialize the Billing API wrapper class."""
        self.api = api
        self.site_id = device['id']
        self.timezone = device['timezone']
        self.type = billing_type
        self.result = {}
        self.update = Throttle(interval)(self.update)

    def update(self):
        """Update function for updating api information."""
        param = ''
        today_date = datetime.now(tz=self.timezone) \
            .replace(hour=0, minute=0, second=0, microsecond=0)
        if self.type == 'Today':
            param = f'?period=day&start={today_date.timestamp() * 1000}'
        elif self.type == 'Yesterday':
            param = '?period=day&start={}&end={}'.format(
                (today_date - timedelta(1)).timestamp() * 1000,
                today_date.timestamp() * 1000)
        elif self.type == 'Estimate':
            param = '?timeType=pastToFuture'

        self.result = self.api.get(
            f'sites/{self.site_id}/usages/billing{param}')
        self.result['charge'] = self.result['bill']['charge']


class EnerTalkRealTimeSensor(EnerTalkSensor):
    """Representation of a EnerTalk RealTime Sensor."""

    def __init__(self, device, variable, variable_info, api,
                 interval):
        """Initialize the Real Time Sensor."""
        super().__init__(device, variable, variable_info)
        self.site_id = self._device['id']
        self.api = api
        self.result = {}
        self.update = Throttle(interval)(self.update)

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.result is None:
            return None
        return round(self.result['activePower'] * 0.001, 2)

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        if self.result is None:
            return None
        return {
            'time': datetime.fromtimestamp(
                self.result['timestamp'] / 1000,
                self._device['timezone']).strftime('%Y-%m-%d %H:%M:%S'),
            'current': self.result['current'],
            'active_power': self.result['activePower'],
            'billing_active_power': self.result['billingActivePower'],
            'apparent_power': self.result['apparentPower'],
            'reactive_power': self.result['reactivePower'],
            'power_factor': self.result['powerFactor'],
            'voltage': self.result['voltage'],
            'positive_energy': self.result['positiveEnergy'],
            'negative_energy': self.result['negativeEnergy'],
            'positive_energy_reactive': self.result['positiveEnergyReactive'],
            'negative_energy_reactive': self.result['negativeEnergyReactive']
        }

    def update(self):
        """Update function for updating api information."""
        self.result = self.api.get(
            f'sites/{self.site_id}/usages/realtime')


class EnerTalkBillingSensor(EnerTalkSensor):
    """Representation of a EnerTalk Billing Sensor."""

    def __init__(self, device, variable, variable_info, api):
        """Initialize the Billing Sensor."""
        super().__init__(device, variable, variable_info)
        self.api = api

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.api.result is None:
            return None
        elif self.var_type == 'Usage':
            return round(self.api.result['usage'] * 0.000001, 2)
        else:
            return round(self.api.result['charge'], 1)

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        if self.api.result is None:
            return
        return {
            'period': self.api.result['period'],
            'start': datetime.fromtimestamp(
                self.api.result['start'] / 1000,
                self._device['timezone']).strftime('%Y-%m-%d %H:%M:%S'),
            'end': datetime.fromtimestamp(
                self.api.result['end'] / 1000,
                self._device['timezone']).strftime('%Y-%m-%d %H:%M:%S')
        }

    def update(self):
        """Get the latest state of the sensor."""
        self.api.update()
