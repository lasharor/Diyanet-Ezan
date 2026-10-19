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

# Optional ezan playback (options flow)
CONF_MEDIA_PLAYERS = "media_players"
CONF_MEDIA = "media"
CONF_VOLUME = "volume"
CONF_PRAYERS = "prayers"
CONF_SABAH_OFFSET = "sabah_offset"
CONF_ONLY_HOME = "only_when_home"
CONF_ANNOUNCE = "announce"
CONF_SAHUR_OFFSET = "sahur_offset"
CONF_SAHUR_MEDIA = "sahur_media"

# "sabah" is the morning ezan, played a set number of minutes before Güneş.
PLAYABLE = ("imsak", "sabah", "ogle", "ikindi", "aksam", "yatsi")
DEFAULT_PRAYERS = ["sabah", "ogle", "ikindi", "aksam", "yatsi"]
DEFAULT_SABAH_OFFSET = 35
