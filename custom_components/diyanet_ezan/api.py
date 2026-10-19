"""Small client for https://ezanvakti.emushaf.net."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

BASE_URL = "https://ezanvakti.emushaf.net"
TIMEOUT = 20


class DiyanetApiError(Exception):
    """Raised when the API cannot be reached or returns something unusable."""


class DiyanetApi:
    """Wraps the four endpoints the integration needs."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, path: str) -> list[dict[str, Any]]:
        try:
            async with asyncio.timeout(TIMEOUT):
                resp = await self._session.get(f"{BASE_URL}/{path}")
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise DiyanetApiError(f"Request to /{path} failed: {err}") from err
        if not isinstance(data, list):
            raise DiyanetApiError(f"Unexpected response from /{path}")
        return data

    async def countries(self) -> list[dict[str, Any]]:
        return await self._get("ulkeler")

    async def cities(self, country_id: str) -> list[dict[str, Any]]:
        return await self._get(f"sehirler/{country_id}")

    async def districts(self, city_id: str) -> list[dict[str, Any]]:
        return await self._get(f"ilceler/{city_id}")

    async def prayer_times(self, district_id: str) -> list[dict[str, Any]]:
        return await self._get(f"vakitler/{district_id}")
