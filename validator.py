import csv
import requests
from unidecode import unidecode
from rapidfuzz import process, fuzz
from collections import defaultdict

CSV_URL = "https://raw.githubusercontent.com/radekstursa/validator_of_addresses/main/addresses_praha.csv"


class AddressValidator:
    def __init__(self):
        print("Downloading Prague CSV...")
        response = requests.get(CSV_URL, stream=True)
        response.raise_for_status()

        print("CSV downloaded, streaming parse...")

        self.cities = set()
        self.streets_by_city = defaultdict(set)
        self.psc_by_city = defaultdict(set)
        self.rows = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

        lines = (line.decode("utf-8") for line in response.iter_lines())
        reader = csv.DictReader(lines)

        for row in reader:
            city = row["city"].strip()
            street = row["street"].strip()
            psc = row["psc"].replace(" ", "")
            cp = row["cp"].strip()

            # Praha má PSČ 10000–19999
            if not (psc.isdigit() and len(psc) == 5 and psc.startswith("1")):
                continue

            city_norm = self._normalize(city)
            street_norm = self._normalize(street)

            self.cities.add(city_norm)
            self.streets_by_city[city_norm].add(street_norm)
            self.psc_by_city[city_norm].add(psc)

            self.rows[city_norm][street_norm][psc].add(cp)

        self.cities = list(self.cities)
        print("Prague dataset loaded.")

    def _normalize(self, text):
        return unidecode(str(text).strip().lower())

    def validate(self, city, psc, street, cp):
        city_norm = self._normalize(city)
        street_norm = self._normalize(street)
        psc_norm = str(psc).replace(" ", "")

        # číslo popisné může být "214/4" → vezmeme jen "214"
        cp_clean = str(cp).split("/")[0].strip()

        # fuzzy match města
        best_city, score_city = process.extractOne(
            city_norm, self.cities, scorer=fuzz.WRatio
        )
        if score_city < 80:
            return {"valid": False, "reason": "City not found in Prague"}

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
        if cp_clean not in self.rows[best_city][best_street][psc_norm]:
            return {"valid": False, "reason": "House number not found"}

        return {
            "valid": True,
            "city": city,
            "street": street,
            "psc": psc,
            "cp": cp,  # vracíme původní formát, i s lomítkem
        }
