import pandas as pd
from unidecode import unidecode
from rapidfuzz import process, fuzz
from collections import defaultdict
import requests
from io import StringIO


# URL k tvému CSV souboru z GitHub Releases (nahraď vlastní)
CSV_URL = "https://github.com/radekstursa/validator_of_addresses/releases/download/v1/addresses.csv"


class AddressValidator:
    def __init__(self):
        # stáhne CSV z GitHubu
        response = requests.get(CSV_URL)
        response.raise_for_status()

        csv_text = response.text
        df = pd.read_csv(StringIO(csv_text), dtype=str).fillna("")

        # normalizace textu
        df["city_norm"] = df["city"].apply(self._normalize)
        df["street_norm"] = df["street"].apply(self._normalize)
        df["psc_norm"] = df["psc"].astype(str).str.replace(" ", "")

        # indexy pro rychlé vyhledávání
        self.cities = df["city_norm"].unique().tolist()
        self.streets_by_city = defaultdict(list)
        self.psc_by_city = defaultdict(list)

        for _, row in df.iterrows():
            self.streets_by_city[row["city_norm"]].append(row["street_norm"])
            self.psc_by_city[row["city_norm"]].append(row["psc_norm"])

        self.df = df

    def _normalize(self, text):
        return unidecode(str(text).strip().lower())

    def validate(self, city, psc, street, cp):
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
            street_norm, self.streets_by_city[best_city], scorer=fuzz.WRatio
        )

        if score_street < 80:
            return {"valid": False, "reason": "Street not found in city"}

        # kontrola PSČ
        if psc_norm not in self.psc_by_city[best_city]:
            return {"valid": False, "reason": "Postal code does not match city"}

        # kontrola čísla popisného
        row = self.df[
            (self.df["city_norm"] == best_city)
            & (self.df["street_norm"] == best_street)
            & (self.df["cp"].astype(str) == str(cp))
        ]

        if row.empty:
            return {"valid": False, "reason": "House number not found"}

        return {
            "valid": True,
            "city": row.iloc[0]["city"],
            "street": row.iloc[0]["street"],
            "psc": row.iloc[0]["psc"],
            "cp": row.iloc[0]["cp"],
        }
