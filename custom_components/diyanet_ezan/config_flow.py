"""UI setup: pick country, city and district from Diyanet's own lists."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import DiyanetApi, DiyanetApiError
from .const import (
    CONF_ANNOUNCE,
    CONF_CITY,
    CONF_COUNTRY,
    CONF_DISTRICT,
    CONF_DISTRICT_ID,
    CONF_DISTRICT_NAME,
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
    DOMAIN,
    PLAYABLE,
)


def _label(item: dict[str, Any], en_key: str, tr_key: str) -> str:
    return str(item.get(en_key) or item.get(tr_key) or "").strip().title()


def _options(items: list[dict[str, Any]], id_key: str, en_key: str, tr_key: str) -> list[SelectOptionDict]:
    options = [
        SelectOptionDict(value=str(item[id_key]), label=_label(item, en_key, tr_key))
        for item in items
        if id_key in item
    ]
    return sorted(options, key=lambda o: o["label"])


def _select(options: list[SelectOptionDict]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN, sort=False)
    )


class DiyanetConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DiyanetOptionsFlow:
        return DiyanetOptionsFlow()

    def __init__(self) -> None:
        self._api: DiyanetApi | None = None
        self._city_id: str | None = None
        self._districts: dict[str, str] = {}

    @property
    def api(self) -> DiyanetApi:
        if self._api is None:
            self._api = DiyanetApi(async_get_clientsession(self.hass))
        return self._api

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await self._async_after_country(user_input[CONF_COUNTRY])

        try:
            countries = await self.api.countries()
        except DiyanetApiError:
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_COUNTRY): _select(_options(countries, "UlkeID", "UlkeAdiEn", "UlkeAdi"))}
            ),
        )

    async def _async_after_country(self, country_id: str) -> ConfigFlowResult:
        try:
            cities = await self.api.cities(country_id)
        except DiyanetApiError:
            return self.async_abort(reason="cannot_connect")
        if not cities:
            return self.async_abort(reason="no_locations")
        if len(cities) == 1:
            # Several countries (e.g. the Netherlands) have a single "city" level.
            return await self._async_after_city(str(cities[0]["SehirID"]))

        self._cities_options = _options(cities, "SehirID", "SehirAdiEn", "SehirAdi")
        return await self.async_step_city()

    async def async_step_city(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await self._async_after_city(user_input[CONF_CITY])
        return self.async_show_form(
            step_id="city",
            data_schema=vol.Schema({vol.Required(CONF_CITY): _select(self._cities_options)}),
        )

    async def _async_after_city(self, city_id: str) -> ConfigFlowResult:
        self._city_id = city_id
        try:
            districts = await self.api.districts(city_id)
        except DiyanetApiError:
            return self.async_abort(reason="cannot_connect")
        if not districts:
            return self.async_abort(reason="no_locations")

        options = _options(districts, "IlceID", "IlceAdiEn", "IlceAdi")
        self._districts = {o["value"]: o["label"] for o in options}
        self._district_options = options
        return await self.async_step_district()

    async def async_step_district(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            district_id = user_input[CONF_DISTRICT]
            await self.async_set_unique_id(district_id)
            self._abort_if_unique_id_configured()

            try:
                times = await self.api.prayer_times(district_id)
            except DiyanetApiError:
                times = []
            if times:
                name = self._districts.get(district_id, district_id)
                return self.async_create_entry(
                    title=name,
                    data={CONF_DISTRICT_ID: district_id, CONF_DISTRICT_NAME: name},
                )
            errors["base"] = "no_times"

        return self.async_show_form(
            step_id="district",
            data_schema=vol.Schema({vol.Required(CONF_DISTRICT): _select(self._district_options)}),
            errors=errors,
        )


def _suggested(options: dict[str, Any], key: str) -> dict[str, Any]:
    """Pre-fill a field without forcing a value (lets the user clear it)."""
    value = options.get(key)
    return {"suggested_value": value} if value not in (None, "", []) else {}


def _minutes(maximum: int) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(min=0, max=maximum, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="min")
    )


class DiyanetOptionsFlow(OptionsFlow):
    """Optional ezan playback. Leave the speakers empty to keep it off."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        options = dict(self.config_entry.options)

        if user_input is not None:
            if user_input.get(CONF_MEDIA_PLAYERS) and not (user_input.get(CONF_MEDIA) or "").strip():
                errors[CONF_MEDIA] = "media_required"
            else:
                return self.async_create_entry(data=user_input)
            options = user_input

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MEDIA_PLAYERS, description=_suggested(options, CONF_MEDIA_PLAYERS)
                ): EntitySelector(EntitySelectorConfig(domain="media_player", multiple=True)),
                vol.Optional(CONF_MEDIA, description=_suggested(options, CONF_MEDIA)): TextSelector(),
                vol.Optional(CONF_VOLUME, description=_suggested(options, CONF_VOLUME)): NumberSelector(
                    NumberSelectorConfig(min=0, max=100, step=5, mode=NumberSelectorMode.SLIDER, unit_of_measurement="%")
                ),
                vol.Required(CONF_PRAYERS, default=options.get(CONF_PRAYERS, DEFAULT_PRAYERS)): SelectSelector(
                    SelectSelectorConfig(
                        options=list(PLAYABLE),
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                        translation_key="prayers",
                    )
                ),
                vol.Required(
                    CONF_SABAH_OFFSET, default=options.get(CONF_SABAH_OFFSET, DEFAULT_SABAH_OFFSET)
                ): _minutes(180),
                vol.Required(CONF_ONLY_HOME, default=options.get(CONF_ONLY_HOME, True)): BooleanSelector(),
                vol.Required(CONF_ANNOUNCE, default=options.get(CONF_ANNOUNCE, True)): BooleanSelector(),
                vol.Required(CONF_SAHUR_OFFSET, default=options.get(CONF_SAHUR_OFFSET, 0)): _minutes(180),
                vol.Optional(CONF_SAHUR_MEDIA, description=_suggested(options, CONF_SAHUR_MEDIA)): TextSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
