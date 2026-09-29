from ..ToolInterface import ToolInterface
from .OverpassClient import OverpassClient
from services.AgentService import AgentContext
from .GeocodingClient import GeocodingClient

import logging

class HealthcareTool(ToolInterface):

    def __init__(self):
        self.client = OverpassClient()
        self.geocoder = GeocodingClient()

        self.logger = logging.getLogger("uvicorn")

    @property
    def name(self) -> str:
        return "healthcare_search"

    @property
    def description(self) -> str:
        return (
            "Find nearby hospitals, clinics, pharmacies or doctors. "
            "If the user's real GPS location is available, it's used "
            "automatically. Otherwise, extract the place name the user "
            "mentioned and pass it as 'location_text'."
        )

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_text": {
                            "type": "string",
                            "description": (
                                "اسم المكان أو المنطقة اللي المستخدم ذكرها "
                                "في سؤاله (مثلاً 'قويسنا، المنوفية'). "
                                "استخدم القيمة دي لو المستخدم كتب مكان بالنص "
                                "ومفيش إحداثيات GPS متاحة."
                            ),
                        },
                        "radius": {
                            "type": "integer",
                            "description": "Search radius in meters.",
                            "default": 5000,
                        }
                    },
                    "required": [],
                },
            },
        }

    async def execute(self, latitude: float, longitude: float, radius: int = 5000):
        RADIUS_ESCALATION = [radius, radius * 2, radius * 4]

        for r in RADIUS_ESCALATION:
            self.logger.info(
                "Searching healthcare facilities at (%.5f, %.5f) within %dm radius",
                latitude, longitude, r,
            )

            result = await self.client.search_healthcare(
                latitude=latitude, longitude=longitude, radius=r,
            )

            if result:
                self.logger.info("Found %d result(s) at radius %dm", len(result), r)
                return result

        self.logger.info("No results found even after radius escalation")
        return []

    async def execute_with_context(self, arguments: dict, context: "AgentContext") -> dict:
        latitude = context.latitude
        longitude = context.longitude

        if latitude is None or longitude is None:
            location_text = arguments.pop("location_text", None)

            if not location_text:
                self.logger.warning(
                    "No GPS coordinates and no location_text provided; cannot search."
                )
                return {
                    "error": (
                        "لا يوجد موقع GPS متاح، ولم يتم تحديد اسم "
                        "منطقة في السؤال للبحث عنها."
                    )
                }

            self.logger.info("No GPS available, geocoding location_text: %s", location_text)

            coordinates = await self.geocoder.geocode(location_text)

            if coordinates is None:
                self.logger.warning("Geocoding failed for location_text: %s", location_text)
                return {
                    "error": f"تعذر تحديد إحداثيات المكان: {location_text}"
                }

            latitude, longitude = coordinates
            self.logger.info(
                "Geocoded '%s' to (%.5f, %.5f)", location_text, latitude, longitude
            )
        else:
            self.logger.info("Using GPS coordinates from context: (%.5f, %.5f)", latitude, longitude)

        arguments.pop("location_text", None)
        arguments["latitude"] = latitude
        arguments["longitude"] = longitude

        return await self.execute(**arguments)