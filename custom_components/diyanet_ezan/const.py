"""Constants for the Diyanet Ezan integration."""

from __future__ import annotations

import logging
from datetime import timedelta

DOMAIN = "diyanet_ezan"
LOGGER = logging.getLogger(__package__)

CONF_COUNTRY = "country"
CONF_CITY = "city"
CONF_DISTRICT = "district"
CONF_DISTRICT_ID = "district_id"
CONF_DISTRICT_NAME = "district_name"

# The API returns roughly a month of days per call, so a refresh twice a day
# is plenty. Times are cached to disk, so a temporary API outage is harmless.
UPDATE_INTERVAL = timedelta(hours=12)

EVENT_PRAYER = f"{DOMAIN}_prayer"
