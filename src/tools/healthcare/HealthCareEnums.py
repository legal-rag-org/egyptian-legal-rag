from enum import Enum


class HealthCareEnums(Enum):

    NAME = "healthcare_search"

    DESCRIPTION = """
        Find nearby hospitals, clinics, pharmacies or doctors.
        If the user's real GPS location is available, it's used
        automatically. Otherwise, extract the place name the user
        mentioned and pass it as 'location_text'.
    """

    DEFAULT_RADIUS = 5000