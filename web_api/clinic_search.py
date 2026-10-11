"""Nearby-dentist lookup for the local web API."""
from __future__ import annotations

import logging
import math
from typing import Any

import requests

logger = logging.getLogger("ClinicSearch")
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DentalHelper-local/1.0"


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres."""
    radius_km = 6371.0088
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    if "center" in element:
        return float(element["center"]["lat"]), float(element["center"]["lon"])
    return None


def _address(tags: dict[str, str]) -> str:
    if tags.get("addr:full"):
        return tags["addr:full"]
    street = " ".join(part for part in (tags.get("addr:street"), tags.get("addr:housenumber")) if part)
    locality = tags.get("addr:city") or tags.get("addr:place") or tags.get("addr:district")
    return ", ".join(part for part in (street, locality) if part) or "Адрес не указан в OpenStreetMap"


def _normalise(items: list[dict[str, Any]], latitude: float, longitude: float, radius: int) -> list[dict[str, Any]]:
    unique: dict[tuple[int, int], dict[str, Any]] = {}
    for item in items:
        try:
            lat, lon = float(item["lat"]), float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        distance = haversine(latitude, longitude, lat, lon)
        if distance > radius / 1000:
            continue
        key = (round(lat * 100000), round(lon * 100000))
        candidate = {**item, "lat": lat, "lon": lon, "distance": distance}
        if key not in unique or candidate["distance"] < unique[key]["distance"]:
            unique[key] = candidate
    return sorted(unique.values(), key=lambda item: (item["distance"], item["name"].casefold()))


def _from_overpass(latitude: float, longitude: float, radius: int) -> list[dict[str, Any]]:
    query = f"""[out:json][timeout:20];
    (
      nwr[\"amenity\"=\"dentist\"](around:{radius},{latitude},{longitude});
      nwr[\"healthcare\"=\"dentist\"](around:{radius},{latitude},{longitude});
    );
    out center tags;"""
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(endpoint, data=query, headers={"Content-Type": "text/plain", "User-Agent": USER_AGENT}, timeout=25)
            response.raise_for_status()
            results: list[dict[str, Any]] = []
            for element in response.json().get("elements", []):
                coordinates = _coordinates(element)
                if not coordinates:
                    continue
                tags = element.get("tags", {})
                results.append({"name": tags.get("name") or "Стоматология", "address": _address(tags), "lat": coordinates[0], "lon": coordinates[1]})
            return results
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Overpass endpoint %s unavailable: %s", endpoint, exc)
    return []


def _from_nominatim(latitude: float, longitude: float, radius: int) -> list[dict[str, Any]]:
    """Fallback: collect broadly, then rank only by exact distance."""
    lat_delta = radius / 111_000
    lon_delta = radius / max(111_000 * math.cos(math.radians(latitude)), 1)
    params = {
        "q": "dentist",
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 50,
        "countrycodes": "ru",
        "viewbox": f"{longitude - lon_delta},{latitude + lat_delta},{longitude + lon_delta},{latitude - lat_delta}",
        "bounded": 1,
    }
    try:
        response = requests.get(NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT, "Accept-Language": "ru"}, timeout=15)
        response.raise_for_status()
        return [{"name": place.get("name") or "Стоматология", "address": place.get("display_name") or "Адрес не указан в OpenStreetMap", "lat": place["lat"], "lon": place["lon"]} for place in response.json()]
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Nominatim unavailable: %s", exc)
        return []


def get_nearby_dentists(latitude: float, longitude: float, radius: int = 5000) -> list[dict[str, Any]]:
    """Return at most seven closest clinics, sorted by exact distance."""
    primary = _from_overpass(latitude, longitude, radius)
    ranked = _normalise(primary, latitude, longitude, radius)
    if len(ranked) < 7:
        ranked = _normalise(primary + _from_nominatim(latitude, longitude, radius), latitude, longitude, radius)
    return ranked[:7]
