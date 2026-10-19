"""Optional ezan playback on media players, configured through the options flow."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_ANNOUNCE,
    CONF_MEDIA,
    CONF_MEDIA_PLAYERS,
    CONF_ONLY_HOME,
    CONF_PRAYERS,
    CONF_SABAH_OFFSET,
    CONF_SAHUR_MEDIA,
    CONF_SAHUR_OFFSET,
    CONF_VOLUME,
    DEFAULT_PRAYERS,
    DEFAULT_SABAH_OFFSET,
    LOGGER,
)

if TYPE_CHECKING:
    from .coordinator import DiyanetCoordinator


def ezan_schedule(
    times: Mapping[str, datetime],
    prayers: list[str],
    sabah_offset: int,
    sahur_offset: int,
    ramadan: bool,
) -> list[tuple[str, datetime]]:
    """Which (reason, moment) pairs should play today. Pure, so it is easy to test."""
    plan: list[tuple[str, datetime]] = []
    for prayer in prayers:
        if prayer == "sabah":
            if "gunes" in times:
                plan.append(("sabah", times["gunes"] - timedelta(minutes=sabah_offset)))
        elif prayer in times:
            plan.append((prayer, times[prayer]))
    if ramadan and sahur_offset > 0 and "imsak" in times:
        plan.append(("sahur", times["imsak"] - timedelta(minutes=sahur_offset)))
    return plan


class EzanPlayer:
    """Plays the ezan on the configured speakers at the configured times."""

    def __init__(self, hass: HomeAssistant, coordinator: DiyanetCoordinator, options: Mapping[str, Any]) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.players: list[str] = list(options.get(CONF_MEDIA_PLAYERS) or [])
        self.media: str = (options.get(CONF_MEDIA) or "").strip()
        self.sahur_media: str = (options.get(CONF_SAHUR_MEDIA) or "").strip() or self.media
        volume = options.get(CONF_VOLUME)
        self.volume: float | None = None if volume in (None, "") else float(volume) / 100
        self.prayers: list[str] = list(options.get(CONF_PRAYERS, DEFAULT_PRAYERS))
        self.sabah_offset = int(options.get(CONF_SABAH_OFFSET, DEFAULT_SABAH_OFFSET))
        self.sahur_offset = int(options.get(CONF_SAHUR_OFFSET, 0))
        self.only_home: bool = options.get(CONF_ONLY_HOME, True)
        self.announce: bool = options.get(CONF_ANNOUNCE, True)
        # Toggled by the playback switch; restored from its last state on startup.
        self.enabled = True
        self._last_minute: datetime | None = None

    @property
    def configured(self) -> bool:
        return bool(self.players and self.media)

    def _someone_home(self) -> bool:
        state = self.hass.states.get("zone.home")
        if state is None:
            return True  # no zone.home: don't block playback
        try:
            return int(float(state.state)) > 0
        except ValueError:
            return True

    @callback
    def async_minute_tick(self, now: datetime) -> None:
        if not self.configured or not self.enabled:
            return
        minute = now.replace(second=0, microsecond=0)
        if minute == self._last_minute:
            return
        times = self.coordinator.times(now)
        today = self.coordinator.today(now)
        if not times or today is None:
            return

        plan = ezan_schedule(times, self.prayers, self.sabah_offset, self.sahur_offset, today.is_ramadan)
        for reason, moment in plan:
            if moment.replace(second=0, microsecond=0) != minute:
                continue
            self._last_minute = minute
            if self.only_home and not self._someone_home():
                LOGGER.debug("Skipping %s ezan: nobody home", reason)
                return
            media = self.sahur_media if reason == "sahur" else self.media
            self.hass.async_create_task(self.async_play(media, reason))
            return

    async def async_play(self, media: str | None = None, reason: str = "manual") -> None:
        media = media or self.media
        if not self.players or not media:
            raise HomeAssistantError("No speakers or ezan audio configured")
        LOGGER.debug("Playing ezan (%s) on %s", reason, self.players)

        if self.volume is not None:
            try:
                await self.hass.services.async_call(
                    "media_player",
                    "volume_set",
                    {"entity_id": self.players, "volume_level": self.volume},
                    blocking=True,
                )
            except HomeAssistantError as err:
                # Some players (e.g. groups) can't set volume; still try to play.
                LOGGER.warning("Could not set ezan volume: %s", err)

        data: dict[str, Any] = {
            "entity_id": self.players,
            "media_content_id": media,
            "media_content_type": "music",
        }
        if self.announce:
            data["announce"] = True
        try:
            await self.hass.services.async_call("media_player", "play_media", data, blocking=True)
        except HomeAssistantError as err:
            LOGGER.error("Could not play ezan on %s: %s", self.players, err)
            if reason == "manual":
                raise
