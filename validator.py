import csv
import requests
from unidecode import unidecode
from rapidfuzz import process, fuzz
from collections import defaultdict

CSV_URL = "https://raw.githubusercontent.com/radekstursa/validator_of_addresses/main/addresses_praha.csv"

class AddressValidator:
    def __init__(self):
        response = requests.get(CSV_URL, stream=True)
        response.raise_for_status()

        lines = (line.decode("utf-8") for line in response.iter_lines())
        reader = csv.DictReader(lines)

        self.cities = set()
        self.streets_by_city = defaultdict(set)
        self.psc_by_city = defaultdict(set)
        self.rows = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

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
            self.rows[city_norm][street_norm][psc].add(cp)

        self.cities = list(self.cities)

    def _normalize(self, text):
        return unidecode(str(text).strip().lower())

    def validate(self, city, psc, street, cp):
        city_norm = self._normalize(city)
        street_norm = self._normalize(street)
        psc_norm = str(psc).replace(" ", "")

        # 🔥 cp může být číslo, string nebo "214/4"
        cp_clean = str(cp).split("/")[0].strip()

        # fuzzy match města
        best_city, score_city = process.extractOne(
            city_norm, self.cities, scorer=fuzz.WRatio
        )
        if score_city < 80:
            return {"valid": False, "reason": "City not found"}

        # bezpečná kontrola existence
        if best_city not in self.streets_by_city:
            return {"valid": False, "reason": "City not in dataset"}

        # fuzzy match ulice
        best_street, score_street = process.extractOne(
            street_norm, list(self.streets_by_city[best_city]), scorer=fuzz.WRatio
        )
        if score_street < 80:
            return {"valid": False, "reason": "Street not found in city"}

        # kontrola PSČ
        if psc_norm not in self.psc_by_city.get(best_city, set()):
            return {"valid": False, "reason": "Postal code does not match city"}

        # kontrola čísla popisného
        if cp_clean not in self.rows.get(best_city, {}).get(best_street, {}).get(psc_norm, set()):
            return {"valid": False, "reason": "House number not found"}

        return {
            "valid": True,
            "city": city,
            "psc": psc,
            "street": street,
            "cp": cp
        }
