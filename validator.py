import csv
import requests
from unidecode import unidecode
from collections import defaultdict

CSV_URL = "https://raw.githubusercontent.com/radekstursa/validator_of_addresses/main/addresses_praha.csv"


class AddressValidator:
    def __init__(self):
        response = requests.get(CSV_URL, stream=True)
        response.raise_for_status()
        lines = (line.decode("utf-8-sig") for line in response.iter_lines())
        reader = csv.DictReader(lines)

        # key: (city_norm, psc, street_norm) -> set of (cp, co) tuples
        self.addresses = defaultdict(set)

        for row in reader:
            city_norm = self._normalize(row["city"])
            psc = row["psc"].replace(" ", "").strip()
            street_norm = self._normalize(row["street"])
            cp = row["cp"].strip()
            co = row["co"].strip()
            self.addresses[(city_norm, psc, street_norm)].add((cp, co))

    def _normalize(self, text):
        return unidecode(str(text).strip().lower())

    def validate(self, city, psc, street, cp, co=None):
        city_norm = self._normalize(city)
        psc_norm = str(psc).replace(" ", "").strip()
        street_norm = self._normalize(street)
        cp_clean = str(cp).strip()
        co_clean = str(co).strip() if co else None

        key = (city_norm, psc_norm, street_norm)
        entries = self.addresses.get(key)

        if not entries:
            return {"valid": False, "reason": "Address not found"}

        if co_clean:
            match = any(cp_clean == e[0] and co_clean == e[1] for e in entries)
        else:
            match = any(cp_clean == e[0] for e in entries)

        if not match:
            return {"valid": False, "reason": "House number not found"}

        return {
            "valid": True,
            "city": city,
            "psc": psc,
            "street": street,
            "cp": cp,
            "co": co
        }

