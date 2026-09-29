import httpx


class OverpassClient:

    BASE_URL = "https://overpass-api.de/api/interpreter"

    async def search_healthcare(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5000,
    ) -> list[dict]:

        query = f"""
        [out:json][timeout:25];

        (
            node["amenity"="hospital"]
                (around:{radius},{latitude},{longitude});

            way["amenity"="hospital"]
                (around:{radius},{latitude},{longitude});

            node["amenity"="clinic"]
                (around:{radius},{latitude},{longitude});

            way["amenity"="clinic"]
                (around:{radius},{latitude},{longitude});

            node["amenity"="pharmacy"]
                (around:{radius},{latitude},{longitude});

            way["amenity"="pharmacy"]
                (around:{radius},{latitude},{longitude});

            node["amenity"="doctors"]
                (around:{radius},{latitude},{longitude});
        );

        out center;
        """

        headers = {
            "User-Agent": "insurance-pension-rag/1.0",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=30,
            headers=headers,
        ) as client:

            response = await client.post(
                self.BASE_URL,
                data={"data": query},
            )

            if response.status_code != 200:
                print("STATUS:", response.status_code)
                print("RESPONSE:", response.text)

            response.raise_for_status()

        data = response.json()

        return self._normalize(
            data.get("elements", [])
        )

    def _normalize(
        self,
        elements: list[dict],
    ) -> list[dict]:

        results = []

        for element in elements:

            tags = element.get("tags", {})

            latitude = element.get("lat")
            longitude = element.get("lon")

            if latitude is None:
                center = element.get("center", {})
                latitude = center.get("lat")
                longitude = center.get("lon")

            if latitude is None or longitude is None:
                continue

            results.append({
                "name": tags.get("name", "Unknown"),
                "type": tags.get("amenity"),
                "latitude": latitude,
                "longitude": longitude,
                "phone": tags.get("phone"),
                "address": tags.get("addr:full"),
            })

        return results