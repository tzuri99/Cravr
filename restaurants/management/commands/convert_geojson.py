import csv
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand

MAX_ROWS = 50
COLUMNS = ["name", "latitude", "longitude", "address", "cuisine", "opening_time", "closing_time"]


def parse_hours(text):
    match = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", text or "")
    if match:
        return match.group(1), match.group(2)
    return "", ""


class Command(BaseCommand):
    help = "Convert data/export.geojson into data/restaurants.csv"

    def handle(self, *args, **options):
        source = Path("data/export.geojson")
        target = Path("data/restaurants.csv")

        with open(source, encoding="utf-8") as f:
            data = json.load(f)

        rows = []
        for feature in data["features"]:
            props = feature.get("properties", {})
            name = props.get("name")
            if not name:
                continue

            geometry = feature.get("geometry", {})
            if geometry.get("type") != "Point":
                continue

            longitude, latitude = geometry["coordinates"]

            house = props.get("addr:housenumber", "")
            street = props.get("addr:street", "")
            address = " ".join(part for part in [house, street] if part)

            opening, closing = parse_hours(props.get("opening_hours", ""))

            rows.append({
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "address": address,
                "cuisine": props.get("cuisine", ""),
                "opening_time": opening,
                "closing_time": closing,
            })

        rows = rows[:MAX_ROWS]

        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows)} restaurants to {target}"))