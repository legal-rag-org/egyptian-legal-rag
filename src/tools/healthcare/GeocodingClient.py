# stores/geocoding/GeocodingClient.py
import aiohttp

class GeocodingClient:

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    async def geocode(self, location_text: str) -> tuple[float, float] | None:
        params = {
            "q": location_text,
            "format": "json",
            "limit": 1,
        }
        headers = {
            "User-Agent": "insurance-rag-app/1.0"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()

                if not data:
                    return None

                return float(data[0]["lat"]), float(data[0]["lon"])