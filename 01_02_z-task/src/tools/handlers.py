from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import requests

from ..config import HUB_API_KEY, HUB_URL, MODEL, TASK_NAME, WORKERS_PATH, ai


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_point(node: Any) -> tuple[float, float] | None:
    if isinstance(node, (list, tuple)) and len(node) >= 2:
        lat = _to_float(node[0])
        lon = _to_float(node[1])
        if lat is not None and lon is not None:
            return lat, lon

    if isinstance(node, dict):
        lat_keys = ("lat", "latitude", "y")
        lon_keys = ("lon", "lng", "longitude", "x")

        lat = next((_to_float(node.get(k)) for k in lat_keys if k in node), None)
        lon = next((_to_float(node.get(k)) for k in lon_keys if k in node), None)

        if lat is not None and lon is not None:
            return lat, lon

    return None


def _extract_code(node: dict[str, Any]) -> str | None:
    for key in ("code", "powerPlant", "powerPlantCode", "id", "plantCode"):
        value = node.get(key)
        if isinstance(value, str) and value.startswith("PWR") and value.endswith("PL"):
            return value
    return None


def _resolve_city_coords(city_names: list[str]) -> dict[str, tuple[float, float]]:
    """Ask the LLM to return approximate WGS-84 coordinates for a list of city names."""
    prompt = (
        "Return a JSON object where each key is a city name from the list below "
        "and the value is an object with keys \"lat\" and \"lon\" (float, WGS-84). "
        "Use approximate centre-of-city coordinates. "
        "Reply ONLY with the JSON, no markdown, no explanation.\n\n"
        "Cities: " + json.dumps(city_names, ensure_ascii=False)
    )

    response = ai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw_text = response.choices[0].message.content or ""
    # Strip possible markdown code fences
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0]

    data = json.loads(raw_text)
    coords: dict[str, tuple[float, float]] = {}
    for city, point in data.items():
        lat = _to_float(point.get("lat") if isinstance(point, dict) else None)
        lon = _to_float(point.get("lon") if isinstance(point, dict) else None)
        if lat is not None and lon is not None:
            coords[city] = (lat, lon)
    return coords


def _extract_power_plants(raw: Any) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    # Primary format: {"power_plants": {"CityName": {"code": "PWR...", ...}}}
    if isinstance(raw, dict) and "power_plants" in raw:
        plants_dict = raw["power_plants"]
        if isinstance(plants_dict, dict):
            city_names = [c for c in plants_dict if isinstance(plants_dict[c], dict)]
            city_coords = _resolve_city_coords(city_names)

            for city_name in city_names:
                plant_data = plants_dict[city_name]
                code = plant_data.get("code")
                if not isinstance(code, str) or not code.startswith("PWR"):
                    continue
                coords = city_coords.get(city_name)
                if coords:
                    candidates.append({"code": code, "city": city_name, "lat": coords[0], "lon": coords[1]})
            return candidates

    # Fallback: list of dicts or other dict shapes with embedded coordinates
    if isinstance(raw, list):
        iterable = raw
    elif isinstance(raw, dict):
        for key in ("items", "locations", "powerPlants"):
            if isinstance(raw.get(key), list):
                iterable = raw[key]
                break
        else:
            iterable = list(raw.values())
    else:
        iterable = []

    for item in iterable:
        if not isinstance(item, dict):
            continue

        code = _extract_code(item)
        point = _extract_point(item)

        if point is None and isinstance(item.get("coordinates"), (dict, list, tuple)):
            point = _extract_point(item["coordinates"])

        if code and point:
            candidates.append({"code": code, "lat": point[0], "lon": point[1]})

    return candidates


def _extract_locations(raw: Any) -> list[dict[str, float]]:
    points: list[tuple[float, float]] = []

    def walk(node: Any) -> None:
        point = _extract_point(node)
        if point:
            points.append(point)
            return

        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            for child in node.values():
                if isinstance(child, (list, dict, tuple)):
                    walk(child)

    walk(raw)

    unique = []
    seen = set()
    for lat, lon in points:
        key = (round(lat, 8), round(lon, 8))
        if key in seen:
            continue
        seen.add(key)
        unique.append({"lat": lat, "lon": lon})

    return unique


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius_km * c


def get_suspects(_: dict[str, Any] | None = None) -> dict[str, Any]:
    suspects = _load_json(WORKERS_PATH)
    return {"suspects": suspects, "count": len(suspects)}


def get_power_plants(_: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{HUB_URL}/data/{HUB_API_KEY}/findhim_locations.json"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    raw = response.json()
    power_plants = _extract_power_plants(raw)

    if not power_plants:
        raise ValueError("Nie udało się sparsować lokalizacji elektrowni z findhim_locations.json")

    return {"powerPlants": power_plants, "count": len(power_plants)}


def get_person_locations(args: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "apikey": HUB_API_KEY,
        "name": args["name"],
        "surname": args["surname"],
    }
    response = requests.post(f"{HUB_URL}/api/location", json=payload, timeout=30)
    response.raise_for_status()

    raw = response.json()
    locations = _extract_locations(raw)

    if not locations:
        raise ValueError(f"Brak lokalizacji dla osoby {args['name']} {args['surname']}")

    return {"name": args["name"], "surname": args["surname"], "locations": locations, "count": len(locations)}


def find_nearest_power_plant(args: dict[str, Any]) -> dict[str, Any]:
    person_locations = args["personLocations"]
    power_plants = args["powerPlants"]

    if not person_locations:
        raise ValueError("personLocations nie może być puste")
    if not power_plants:
        raise ValueError("powerPlants nie może być puste")

    best: dict[str, Any] | None = None

    for person_loc in person_locations:
        p_lat = float(person_loc["lat"])
        p_lon = float(person_loc["lon"])

        for plant in power_plants:
            distance_km = _haversine_km(p_lat, p_lon, float(plant["lat"]), float(plant["lon"]))
            candidate = {
                "powerPlant": plant["code"],
                "distanceKm": round(distance_km, 6),
                "personLocation": {"lat": p_lat, "lon": p_lon},
                "plantLocation": {"lat": float(plant["lat"]), "lon": float(plant["lon"])},
            }

            if best is None or candidate["distanceKm"] < best["distanceKm"]:
                best = candidate

    return best or {"error": "Nie udało się wyznaczyć najbliższej elektrowni"}


def get_access_level(args: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "apikey": HUB_API_KEY,
        "name": args["name"],
        "surname": args["surname"],
        "birthYear": int(args["birthYear"]),
    }
    response = requests.post(f"{HUB_URL}/api/accesslevel", json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict):
        access_level = data.get("accessLevel", data.get("access_level", data.get("level")))
    else:
        access_level = None

    if access_level is None:
        raise ValueError(f"Nie udało się odczytać accessLevel z odpowiedzi: {data}")

    return {
        "name": args["name"],
        "surname": args["surname"],
        "accessLevel": int(access_level),
    }


def submit_findhim_answer(args: dict[str, Any]) -> dict[str, Any]:
    answer = {
        "name": args["name"],
        "surname": args["surname"],
        "accessLevel": int(args["accessLevel"]),
        "powerPlant": args["powerPlant"],
    }

    payload = {
        "apikey": HUB_API_KEY,
        "task": TASK_NAME,
        "answer": answer,
    }

    response = requests.post(
        f"{HUB_URL}/verify",
        json=payload,
        timeout=30,
        headers={"Content-Type": "application/json"},
    )

    try:
        response_data = response.json()
    except Exception:
        response_data = {"raw": response.text}

    result = {
        "httpStatus": response.status_code,
        "verifyResponse": response_data,
        "answer": answer,
    }

    out_path = WORKERS_PATH.parent / "solution.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return result


handlers = {
    "get_suspects": get_suspects,
    "get_power_plants": get_power_plants,
    "get_person_locations": get_person_locations,
    "find_nearest_power_plant": find_nearest_power_plant,
    "get_access_level": get_access_level,
    "submit_findhim_answer": submit_findhim_answer,
}
