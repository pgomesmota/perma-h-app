#!/usr/bin/env python3
"""Export Portuguese pharmacy records from OpenStreetMap for GreenCare.

This script queries public Overpass API endpoints, normalises pharmacy tags, and
creates:
- an import-ready CSV matching GreenCare's current pharmacy validation;
- an island CSV that becomes import-ready after widening longitude validation;
- a complete review CSV with source and data-quality metadata;
- a JSON summary.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("pharmacy-export")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
]

OVERPASS_QUERY = r"""
[out:json][timeout:900][maxsize:1073741824];
area["ISO3166-1"="PT"][admin_level=2]->.portugal;
(
  node["amenity"="pharmacy"](area.portugal);
  way["amenity"="pharmacy"](area.portugal);
  relation["amenity"="pharmacy"](area.portugal);
);
out center tags;
""".strip()

DB_COLUMNS = [
    "pharmacy_number",
    "pharmacy_group_id",
    "name",
    "address",
    "postal_code",
    "city",
    "latitude",
    "longitude",
    "opening_hours",
    "consultation_rooms",
    "rating",
    "greencare_intake_status",
    "greencare_service_schedule",
]

REVIEW_COLUMNS = DB_COLUMNS + [
    "import_status",
    "data_quality_notes",
    "osm_type",
    "osm_id",
    "source",
    "source_url",
    "phone",
    "email",
    "website",
    "operator",
    "brand",
    "osm_last_checked_at",
]

EMPTY_SCHEDULE = json.dumps(
    {
        "timezone": "Europe/Lisbon",
        "slotMinutes": 30,
        "days": {str(day): [] for day in range(7)},
    },
    ensure_ascii=False,
    separators=(",", ":"),
)


def fetch_overpass() -> tuple[dict[str, Any], str]:
    payload = urllib.parse.urlencode({"data": OVERPASS_QUERY}).encode("utf-8")
    last_error: Exception | None = None

    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(1, 4):
            request = urllib.request.Request(
                endpoint,
                data=payload,
                method="POST",
                headers={
                    "User-Agent": "GreenCare-Portugal-Pharmacy-Seed/1.0 (data import)",
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                },
            )
            try:
                print(f"Querying {endpoint} (attempt {attempt})...", flush=True)
                with urllib.request.urlopen(request, timeout=960) as response:
                    raw = response.read()
                data = json.loads(raw.decode("utf-8"))
                if not isinstance(data.get("elements"), list):
                    raise ValueError("Overpass response does not contain an elements list")
                print(f"Received {len(data['elements'])} OSM elements.", flush=True)
                return data, endpoint
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                print(f"Endpoint attempt failed: {exc}", file=sys.stderr, flush=True)
                time.sleep(5 * attempt)

    raise RuntimeError(f"All Overpass endpoints failed: {last_error}")


def clean(value: Any, max_length: int | None = None) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if max_length is not None:
        return text[:max_length]
    return text


def first_tag(tags: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = clean(tags.get(key))
        if value:
            return value
    return ""


def compose_address(tags: dict[str, Any]) -> str:
    full = first_tag(tags, "addr:full")
    if full:
        return clean(full, 220)

    street = first_tag(tags, "addr:street", "addr:place", "addr:suburb")
    house = first_tag(tags, "addr:housenumber")
    door = first_tag(tags, "addr:door")
    parts = [part for part in [street, house, door] if part]
    return clean(", ".join(parts), 220)


def coordinates(element: dict[str, Any]) -> tuple[float | None, float | None]:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center") or {}
    if "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None, None


def source_url(element_type: str, osm_id: int) -> str:
    return f"https://www.openstreetmap.org/{element_type}/{osm_id}"


def current_schema_ok(row: dict[str, Any]) -> tuple[bool, list[str]]:
    notes: list[str] = []

    if len(row["name"]) < 2:
        notes.append("missing_or_short_name")
    if len(row["address"]) < 3:
        notes.append("missing_address")
    if len(row["postal_code"]) < 3:
        notes.append("missing_postal_code")
    if len(row["city"]) < 2:
        notes.append("missing_city")

    lat = row["latitude"]
    lon = row["longitude"]
    if lat == "" or lon == "":
        notes.append("missing_coordinates")
    else:
        lat_float = float(lat)
        lon_float = float(lon)
        if not (36 <= lat_float <= 43):
            notes.append("latitude_outside_current_validation")
        if not (-10 <= lon_float <= -5):
            notes.append("longitude_outside_current_validation")

    return not notes, notes


def nationally_complete(row: dict[str, Any]) -> bool:
    return (
        len(row["name"]) >= 2
        and len(row["address"]) >= 3
        and len(row["postal_code"]) >= 3
        and len(row["city"]) >= 2
        and row["latitude"] != ""
        and row["longitude"] != ""
        and 32 <= float(row["latitude"]) <= 43
        and -32 <= float(row["longitude"]) <= -5
    )


def normalize_element(element: dict[str, Any], retrieved_at: str) -> dict[str, Any] | None:
    tags = element.get("tags") or {}
    element_type = clean(element.get("type")).lower()
    osm_id = element.get("id")
    if element_type not in {"node", "way", "relation"} or not isinstance(osm_id, int):
        return None

    lat, lon = coordinates(element)
    name = first_tag(tags, "name", "name:pt", "brand", "operator")
    address = compose_address(tags)
    postal_code = first_tag(tags, "addr:postcode")
    city = first_tag(
        tags,
        "addr:city",
        "addr:town",
        "addr:village",
        "addr:municipality",
        "is_in:city",
        "is_in:municipality",
    )

    opening_hours_raw = first_tag(tags, "opening_hours")
    opening_hours = json.dumps(
        {"raw": opening_hours_raw} if opening_hours_raw else {},
        ensure_ascii=False,
        separators=(",", ":"),
    )

    row: dict[str, Any] = {
        "pharmacy_number": f"PT-OSM-{element_type.upper()}-{osm_id}",
        "pharmacy_group_id": "",
        "name": clean(name, 160),
        "address": clean(address, 220),
        "postal_code": clean(postal_code, 20),
        "city": clean(city, 80),
        "latitude": "" if lat is None else f"{lat:.7f}",
        "longitude": "" if lon is None else f"{lon:.7f}",
        "opening_hours": opening_hours,
        "consultation_rooms": 1,
        "rating": 0,
        "greencare_intake_status": "inactive",
        "greencare_service_schedule": EMPTY_SCHEDULE,
        "osm_type": element_type,
        "osm_id": osm_id,
        "source": "OpenStreetMap contributors",
        "source_url": source_url(element_type, osm_id),
        "phone": first_tag(tags, "contact:phone", "phone"),
        "email": first_tag(tags, "contact:email", "email"),
        "website": first_tag(tags, "contact:website", "website"),
        "operator": first_tag(tags, "operator"),
        "brand": first_tag(tags, "brand"),
        "osm_last_checked_at": retrieved_at,
    }

    ready, notes = current_schema_ok(row)
    if ready:
        row["import_status"] = "ready_current_schema"
    elif nationally_complete(row) and "longitude_outside_current_validation" in notes:
        row["import_status"] = "ready_after_longitude_validation_update"
    else:
        row["import_status"] = "needs_data_review"
    row["data_quality_notes"] = ";".join(notes)
    return row


def deduplicate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Keep unique OSM objects, then remove obvious duplicate representations at
    # near-identical coordinates with the same normalized name.
    seen_osm: set[tuple[str, int]] = set()
    seen_place: set[tuple[str, str, str]] = set()
    result: list[dict[str, Any]] = []

    for row in sorted(rows, key=lambda item: (item["name"].casefold(), str(item["osm_id"]))):
        osm_key = (row["osm_type"], int(row["osm_id"]))
        if osm_key in seen_osm:
            continue
        seen_osm.add(osm_key)

        if row["name"] and row["latitude"] and row["longitude"]:
            place_key = (
                row["name"].casefold(),
                f"{float(row['latitude']):.5f}",
                f"{float(row['longitude']):.5f}",
            )
            if place_key in seen_place:
                continue
            seen_place.add(place_key)

        result.append(row)
    return result


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    data, endpoint = fetch_overpass()

    normalized = [
        row
        for element in data["elements"]
        if (row := normalize_element(element, retrieved_at)) is not None
    ]
    rows = deduplicate(normalized)

    ready = [row for row in rows if row["import_status"] == "ready_current_schema"]
    islands = [
        row
        for row in rows
        if row["import_status"] == "ready_after_longitude_validation_update"
    ]
    review = [row for row in rows if row["import_status"] == "needs_data_review"]

    write_csv(OUTPUT_DIR / "greencare_pharmacies_portugal_import_ready.csv", ready, DB_COLUMNS)
    write_csv(OUTPUT_DIR / "greencare_pharmacies_portugal_islands_after_validator_fix.csv", islands, DB_COLUMNS)
    write_csv(OUTPUT_DIR / "greencare_pharmacies_portugal_all_osm_review.csv", rows, REVIEW_COLUMNS)
    write_csv(OUTPUT_DIR / "greencare_pharmacies_portugal_needs_review.csv", review, REVIEW_COLUMNS)

    status_counts = Counter(row["import_status"] for row in rows)
    missing_counts = Counter()
    for row in rows:
        for note in filter(None, row["data_quality_notes"].split(";")):
            missing_counts[note] += 1

    summary = {
        "generated_at": retrieved_at,
        "source": "OpenStreetMap contributors via Overpass API",
        "overpass_endpoint_used": endpoint,
        "osm_elements_received": len(data["elements"]),
        "unique_pharmacy_records": len(rows),
        "status_counts": dict(status_counts),
        "quality_note_counts": dict(missing_counts),
        "current_greenCare_validation": {
            "latitude": "36..43",
            "longitude": "-10..-5",
            "note": "The longitude rule excludes Madeira and the Azores.",
        },
        "defaults": {
            "consultation_rooms": 1,
            "rating": 0,
            "greencare_intake_status": "inactive",
            "service_schedule": "empty; Europe/Lisbon; 30-minute slots",
        },
        "license": "OpenStreetMap data is available under ODbL 1.0; attribution is required.",
    }
    (OUTPUT_DIR / "greencare_pharmacies_portugal_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
