"""
Home Assistant Add-on for Diyanet Prayer Times
Interfaces with https://ezanvakti.emushaf.net API
"""

import aiohttp
import asyncio
import json
import logging
from datetime import datetime, timedelta
from aiohttp import web
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CONFIG_PATH = "/data/options.json"
EZAN_API_URL = "https://ezanvakti.emushaf.net/api"

class DiyametEzanAddon:
    def __init__(self):
        self.config = self.load_config()
        self.city = self.config.get("city", "Istanbul")
        self.country = self.config.get("country", "Turkey")
        self.prayer_times = {}
        self.cities_cache = {}

    def load_config(self):
        """Load configuration from Home Assistant"""
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {CONFIG_PATH}, using defaults")
            return {"city": "Istanbul", "country": "Turkey"}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {"city": "Istanbul", "country": "Turkey"}

    async def get_cities(self):
        """Fetch available cities from the API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{EZAN_API_URL}/city") as resp:
                    if resp.status == 200:
                        self.cities_cache = await resp.json()
                        return self.cities_cache
                    else:
                        logger.error(f"Failed to get cities: {resp.status}")
                        return []
        except Exception as e:
            logger.error(f"Error getting cities: {e}")
            return []

    async def get_prayer_times(self):
        """Fetch prayer times for configured city"""
        try:
            # First, get city ID
            cities = await self.get_cities()
            city_id = None
            
            for city_data in cities:
                if city_data.get("name", "").lower() == self.city.lower():
                    city_id = city_data.get("id")
                    break
            
            if not city_id:
                logger.error(f"City '{self.city}' not found in API")
                return None

            # Get prayer times for the city
            today = datetime.now().strftime("%Y-%m-%d")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{EZAN_API_URL}/timezoneByCity/{city_id}",
                    params={"date": today}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.prayer_times = data
                        logger.info(f"Prayer times updated for {self.city}")
                        return data
                    else:
                        logger.error(f"Failed to get prayer times: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting prayer times: {e}")
            return None

    async def handle_prayer_times(self, request):
        """HTTP endpoint to get prayer times"""
        prayer_times = await self.get_prayer_times()
        if prayer_times:
            return web.json_response(prayer_times)
        else:
            return web.json_response({"error": "Failed to fetch prayer times"}, status=500)

    async def handle_cities(self, request):
        """HTTP endpoint to get available cities"""
        cities = await self.get_cities()
        return web.json_response({"cities": cities})

    async def handle_config(self, request):
        """HTTP endpoint to get current configuration"""
        return web.json_response({
            "city": self.city,
            "country": self.country
        })

    async def start_server(self):
        """Start the aiohttp server"""
        app = web.Application()
        app.router.add_get('/api/prayer-times', self.handle_prayer_times)
        app.router.add_get('/api/cities', self.handle_cities)
        app.router.add_get('/api/config', self.handle_config)
        app.router.add_static('/', path='/app/static', name='static')

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()
        
        logger.info(f"Diyanet Ezan add-on started on port 8000")
        logger.info(f"Configured for {self.city}, {self.country}")

    async def periodic_update(self):
        """Periodically update prayer times"""
        while True:
            try:
                await self.get_prayer_times()
                # Update every 6 hours
                await asyncio.sleep(6 * 3600)
            except Exception as e:
                logger.error(f"Error in periodic update: {e}")
                await asyncio.sleep(60)

    async def run(self):
        """Main run function"""
        await asyncio.gather(
            self.start_server(),
            self.periodic_update()
        )

async def main():
    addon = DiyametEzanAddon()
    await addon.run()

if __name__ == "__main__":
    asyncio.run(main())