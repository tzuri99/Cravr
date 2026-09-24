import csv
import re
from pathlib import Path
import time

import requests
from django.core.management.base import BaseCommand

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "Cravr-student-project/1.0"}

# The four no. are: south, west, north, east
AREAS = {
    "Central KL": (3.10, 101.68, 3.18, 101.73),
    "Bangsar and Mid Valley": (3.10, 101.65, 3.14, 101.68),
    "Mont Kiara and Sri Hartamas": (3.15, 101.62, 3.20, 101.67),
    "Cheras": (3.05, 101.71, 3.12, 101.76),
    "Setapak and Wangsa Maju": (3.18, 101.71, 3.23, 101.77),
    "Bukit Jalil and Sri Petaling": (3.03, 101.66, 3.09, 101.71),
    "Ampang": (3.13, 101.74, 3.19, 101.79),
    "Cyberjaya": (2.90,101.62,2.95,101.68)
}

COLUMNS = ["name", "latitude", "longitude", "address", "cuisine", "opening_time", "closing_time"]

MAX_ATTEMPTS = 3
PAUSE_BETWEEN_AREAS = 10


def parse_hours(text):
    match = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", text or "")
    if match:
        return match.group(1), match.group(2)
    return "", ""


class Command(BaseCommand):
    help = "Fetch restaurants for every area from OpenStreetMap into data/restaurants.csv"

    def handle(self, *args, **options):
        seen_ids = set()
        rows = []
        areas = list(AREAS.items())

        for index, (area_name, (south, west, north, east)) in enumerate(areas):
            self.stdout.write(f"Fetching {area_name}...")

            query = f"""
            [out:json][timeout:180];
            node["amenity"="restaurant"]({south},{west},{north},{east});
            out body;
            """

            response = None
            for attempt in range(MAX_ATTEMPTS):
                try:
                    response = requests.post(
                        OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=200
                    )
                    response.raise_for_status()
                    break
                except requests.RequestException as exc:
                    response = None
                    if attempt < MAX_ATTEMPTS - 1:
                        wait = 15 * (attempt + 1)
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Attempt {attempt + 1} failed ({exc}), retrying in {wait}s"
                            )
                        )
                        time.sleep(wait)
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"  Giving up on {area_name}: {exc}")
                        )

            if response is None:
                continue

            count = 0
            for element in response.json()["elements"]:
                if element["id"] in seen_ids:
                    continue

                tags = element.get("tags", {})
                name = tags.get("name")
                if not name:
                    continue

                seen_ids.add(element["id"])

                house = tags.get("addr:housenumber", "")
                street = tags.get("addr:street", "")
                address = " ".join(part for part in [house, street] if part)

                opening, closing = parse_hours(tags.get("opening_hours", ""))

                rows.append({
                    "name": name,
                    "latitude": element["lat"],
                    "longitude": element["lon"],
                    "address": address,
                    "cuisine": tags.get("cuisine", ""),
                    "opening_time": opening,
                    "closing_time": closing,
                })
                count += 1

            self.stdout.write(f"  Added {count} from {area_name}")

            if index < len(areas) - 1:
                self.stdout.write(f"  Pausing {PAUSE_BETWEEN_AREAS}s before the next area")
                time.sleep(PAUSE_BETWEEN_AREAS)

        csv_path = Path("data/restaurants.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows)} restaurants to {csv_path}"))