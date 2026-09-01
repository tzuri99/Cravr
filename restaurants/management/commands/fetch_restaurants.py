import csv
from pathlib import Path

import requests
from django.core.management.base import BaseCommand

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

HEADERS = {"User-Agent": "Cravr-student-project/1.0"}

# The four numbers are: south, west, north, east.
# Currently covers Cyberjaya.
QUERY = """
[out:json][timeout:60];
node["amenity"="restaurant"](2.90,101.62,2.95,101.68);
out body;
"""

MAX_ROWS = 50
COLUMNS = ["name", "latitude", "longitude", "address", "cuisine", "opening_hours"]


class Command(BaseCommand):
    help = "Fetch restaurants from OpenStreetMap and write data/restaurants.csv"

    def handle(self, *args, **options):
        self.stdout.write("Asking OpenStreetMap for restaurants...")

        response = requests.post(OVERPASS_URL, data={"data": QUERY}, headers=HEADERS, timeout=200)
        response.raise_for_status()

        rows = []
        for element in response.json()["elements"]:
            tags = element.get("tags", {})
            name = tags.get("name")
            if not name:
                continue

            house = tags.get("addr:housenumber", "")
            street = tags.get("addr:street", "")
            address = " ".join(part for part in [house, street] if part)

            rows.append({
                "name": name,
                "latitude": element["lat"],
                "longitude": element["lon"],
                "address": address,
                "cuisine": tags.get("cuisine", ""),
                "opening_hours": tags.get("opening_hours", ""),
            })

        rows = rows[:MAX_ROWS]

        csv_path = Path("data/restaurants.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows)} restaurants to {csv_path}"))