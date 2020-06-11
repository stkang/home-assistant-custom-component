"""API for EnerTalk bound to HASS OAuth."""
import logging
from asyncio import run_coroutine_threadsafe
from time import sleep

import requests
from homeassistant import config_entries, core
from homeassistant.helpers import config_entry_oauth2_flow

from .const import API_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class ConfigEntryEnerTalkAuth:
    """Provide EnerTalk authentication tied to an OAuth2 based config entry."""

    def __init__(
            self,
            hass: core.HomeAssistant,
            config_entry: config_entries.ConfigEntry,
            impl: config_entry_oauth2_flow.AbstractOAuth2Implementation,
    ):
        """Initialize EnerTalk Auth."""
        self.hass = hass
        self.session = config_entry_oauth2_flow.OAuth2Session(
            hass, config_entry, impl
        )

    def refresh_tokens(self, ):
        """Refresh new EnerTalk tokens using Home Assistant OAuth2 session."""
        run_coroutine_threadsafe(
            self.session.async_ensure_token_valid(), self.hass.loop
        ).result()

    def request(self, url):
        headers = {
            'Authorization': f"Bearer {self.session.token['access_token']}",
            'accept-version': '2.0.0'
        }
        try:
            response = requests.get(f'{API_ENDPOINT}/{url}',
                                    headers=headers, timeout=10)
            _LOGGER.debug('JSON Response: %s', response.content.decode('utf8'))
            return response
        except Exception as ex:
            _LOGGER.error('Failed to update EnerToken status Error: %s', ex)
            raise

    def get(self, url):
        response = self.request(url)
        if response.status_code == 401:
            error_type = response.json()['type']
            if error_type == 'UnauthorizedError':
                self.refresh_tokens()
                # Sleep for 1 sec to prevent authentication related
                # timeouts after a token refresh.
                sleep(1)
                response = self.request(url)
        return response.json()
