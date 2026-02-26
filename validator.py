import csv
import requests
from unidecode import unidecode
from rapidfuzz import process, fuzz
from collections import defaultdict
from io import StringIO

CSV_URL = "https://github.com/radekstursa/validator_of_addresses/releases/download/v1/addresses.csv"


class AddressValidator:
    def __init__(self):
        print("Downloading CSV...")
        response = requests.get(CSV_URL, stream=True)
        response.raise_for_status()

        print("CSV downloaded, streaming parse...")

        # příprava struktur
        self.cities = set()
        self.streets_by_city = defaultdict(set)
        self.psc_by_city = defaultdict(set)
        self.rows = []  # uložíme jen malé dicty, ne celý dataframe

        # streamované čtení CSV
        lines = (line.decode("utf-8") for line in response.iter_lines())
        reader = csv.DictReader(lines)

        for row in reader:
            city = row["city"].strip()
            street = row["street"].strip()
            psc = row["psc"].replace(" ", "")
            cp = row["cp"].strip()

            city_norm = self._normalize(city)
            street_norm = self._normalize(street)

            self.cities.add(city_norm)
            self.streets_by_city[city_norm].add(street_norm)
            self.psc_by_city[city_norm].add(psc)

            # uložíme jen to, co potřebujeme pro finální match
            self.rows.append({
                "city_norm": city_norm,
                "street_norm": street_norm,
                "psc": psc,
                "cp": cp,
                "city": city,
                "street": street
            })

        self.cities = list(self.cities)
        print("CSV loaded and indexed.")

    def _normalize(self, text):
        return unidecode(str(text).strip().lower())

    def validate(self, city, psc, street, cp):
        print("Validating address...")

        city_norm = self._normalize(city)
        street_norm = self._normalize(street)
        psc_norm = str(psc).replace(" ", "")

        # fuzzy match města
        best_city, score_city = process.extractOne(
            city_norm, self.cities, scorer=fuzz.WRatio
        )

        if score_city < 80:
            return {"valid": False, "reason": "City not found"}

        # fuzzy match ulice
        best_street, score_street = process.extractOne(
            street_norm, list(self.streets_by_city[best_city]), scorer=fuzz.WRatio
        )

        if score_street < 80:
            return {"valid": False, "reason": "Street not found in city"}

        # kontrola PSČ
        if psc_norm not in self.psc_by_city[best_city]:
            return {"valid": False, "reason": "Postal code does not match city"}

        # kontrola čísla popisného
        for row in self.rows:
            if (
                row["city_norm"] == best_city
                and row["street_norm"] == best_street
                and row["psc"] == psc_norm
                and row["cp"] == str(cp)
            ):
                return {
                    "valid": True,
                    "city": row["city"],
                    "street": row["street"],
                    "psc": row["psc"],
                    "cp": row["cp"],
                }

        return {"valid": False, "reason": "House number not found"}
