"""Constants used by the Netatmo component."""

DOMAIN = "enertalk"
MANUFACTURER = "EnerTalk"

REAL_TIME_MON_COND = {
    'real_time_usage': ['Real Time', 'Usage', 'W', 'mdi:pulse']
}
BILLING_MON_COND = {
    'today_usage': ['Today', 'Usage', 'kWh', 'mdi:trending-up'],
    'today_charge': ['Today', 'Charge', '원', 'mdi:currency-krw'],
    'yesterday_usage': ['Yesterday', 'Usage', 'kWh', 'mdi:trending-up'],
    'yesterday_charge': ['Yesterday', 'Charge', '원', 'mdi:currency-krw'],
    'month_usage': ['Month', 'Usage', 'kWh', 'mdi:trending-up'],
    'month_charge': ['Month', 'Charge', '원', 'mdi:currency-krw'],
    'estimate_usage': ['Estimate', 'Usage', 'kWh', 'mdi:calendar-question'],
    'estimate_charge': ['Estimate', 'Charge', '원', 'mdi:currency-krw']
}
MONITORED_CONDITIONS = list(REAL_TIME_MON_COND.keys()) + \
                        list(BILLING_MON_COND.keys())

AUTH = "enertalk_auth"
CONF_REAL_TIME_INTERVAL = 'real_time_interval'
CONF_BILLING_INTERVAL = 'billing_interval'

OAUTH2_AUTHORIZE = "https://auth.enertalk.com/authorization"
OAUTH2_TOKEN = "https://auth.enertalk.com/token"
API_ENDPOINT = 'https://api2.enertalk.com'

DATA_CONF = "enertalk_conf"
