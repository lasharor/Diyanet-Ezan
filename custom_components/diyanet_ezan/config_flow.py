"""UI setup: pick country, city and district from Diyanet's own lists."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import DiyanetApi, DiyanetApiError
from .const import (
    CONF_CITY,
    CONF_COUNTRY,
    CONF_DISTRICT,
    CONF_DISTRICT_ID,
    CONF_DISTRICT_NAME,
    DOMAIN,
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
