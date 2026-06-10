from math import radians, sin, cos, sqrt, atan2

EARTH_RADIUS = 6371


def haversine(lat1, lon1, lat2, lon2):

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS * c


def nearest_hotspot(lat, lon, hotspots):

    if not hotspots:
        return None

    nearest = None
    min_distance = float("inf")

    for hotspot in hotspots:

        distance = haversine(
            lat,
            lon,
            hotspot["latitude"],
            hotspot["longitude"]
        )

        if distance < min_distance:
            min_distance = distance
            nearest = hotspot

    return {
        "distance_km": round(min_distance, 2),
        "rank": nearest["rank"],
        "incident_count": nearest["incident_count"],
        "top_categories": nearest["top_categories"]
    }