import csv
import requests
from unidecode import unidecode
from rapidfuzz import process, fuzz
from collections import defaultdict

CSV_URL = "https://github.com/radekstursa/validator_of_addresses/releases/download/v1/addresses.csv"


class AddressValidator:
    def __init__(self):
        response = requests.get(CSV_URL, stream=True)
        response.raise_for_status()

        # UTF-8 with BOM safe decode
        lines = (line.decode("utf-8-sig") for line in response.iter_lines())
        reader = csv.DictReader(lines)

        self.cities = set()
        self.streets_by_city = defaultdict(set)
        self.psc_by_city = defaultdict(set)
        self.rows = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

        for row in reader:
            city = row["city"].strip()
            street = row["street"].strip()
            psc = row["psc"].replace(" ", "").strip()
            cp = row["cp"].strip()

            city_norm = self._normalize(city)
            street_norm = self._normalize(street)

            self.cities.add(city_norm)
            self.streets_by_city[city_norm].add(street_norm)
            self.psc_by_city[city_norm].add(psc)
            self.rows[city_norm][street_norm][psc].add(cp)

        self.cities = list(self.cities)

    def _normalize(self, text):
        return unidecode(str(text).strip().lower())

    def validate(self, city, psc, street, cp):
        city_norm = self._normalize(city)
        street_norm = self._normalize(street)
        psc_norm = str(psc).replace(" ", "").strip()

        # cp může být číslo, string nebo "214/4"
        cp_clean = str(cp).split("/")[0].strip()

        # fuzzy match města
        best_city, score_city = process.extractOne(
            city_norm, self.cities, scorer=fuzz.WRatio
        )
        if score_city < 80:
            return {"valid": False, "reason": "City not found"}

        # fuzzy match ulice
        streets = self.streets_by_city.get(best_city, set())
        if not streets:
            return {"valid": False, "reason": "City has no streets in dataset"}

        best_street, score_street = process.extractOne(
            street_norm, list(streets), scorer=fuzz.WRatio
        )
        if score_street < 80:
            return {"valid": False, "reason": "Street not found in city"}

        # kontrola PSČ
        if psc_norm not in self.psc_by_city.get(best_city, set()):
            return {"valid": False, "reason": "Postal code does not match city"}

        # bezpečný přístup – už nikdy KeyError → žádné 500
        cps = self.rows.get(best_city, {}).get(best_street, {}).get(psc_norm, set())
        if cp_clean not in cps:
            return {"valid": False, "reason": "House number not found"}

        return {
            "valid": True,
            "city": city,
            "psc": psc,
            "street": street,
            "cp": cp
        }


