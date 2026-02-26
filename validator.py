import pandas as pd
from unidecode import unidecode
from rapidfuzz import process, fuzz
from collections import defaultdict

def normalize(text):
    if text is None:
        return ""
    return unidecode(str(text).strip().lower())

class AddressValidator:
    def __init__(self, csv_path):
        df = pd.read_csv(csv_path, dtype=str).fillna("")

        df["city_n"] = df["city"].apply(normalize)
        df["street_n"] = df["street"].apply(normalize)
        df["cp_n"] = df["cp"].apply(normalize)
        df["co_n"] = df["co"].apply(normalize)

        self.df = df

        self.cities = sorted(df["city_n"].unique())
        self.psc_by_city = defaultdict(set)
        self.streets_by_city_psc = defaultdict(set)
        self.cp_by_city_psc_street = defaultdict(set)
        self.co_by_full = defaultdict(set)

        for _, row in df.iterrows():
            c, p, s, cp, co = row["city_n"], row["psc"], row["street_n"], row["cp_n"], row["co_n"]

            self.psc_by_city[c].add(p)
            self.streets_by_city_psc[(c, p)].add(s)
            self.cp_by_city_psc_street[(c, p, s)].add(cp)
            self.co_by_full[(c, p, s, cp)].add(co)

    def fuzzy_best(self, query, choices, threshold):
        if not query:
            return None
        match, score, _ = process.extractOne(query, choices, scorer=fuzz.WRatio)
        return match if score >= threshold else None

    def validate(self, city, psc, street, cp, co):
        city_n = normalize(city)
        psc_n = normalize(psc)
        street_n = normalize(street)
        cp_n = normalize(cp)
        co_n = normalize(co)

        # 1) město
        if city_n not in self.cities:
            best_city = self.fuzzy_best(city_n, self.cities, 90)
            if not best_city:
                return {"valid": False, "reason": "Město neexistuje."}
            city_n = best_city

        # 2) PSČ
        valid_psc = self.psc_by_city[city_n]
        if psc_n not in valid_psc:
            if len(valid_psc) == 1:
                psc_n = list(valid_psc)[0]
            else:
                return {"valid": False, "reason": "PSČ neodpovídá městu.", "suggest_psc": list(valid_psc)}

        # 3) ulice
        streets = self.streets_by_city_psc[(city_n, psc_n)]
        if street_n not in streets:
            best_street = self.fuzzy_best(street_n, streets, 85)
            if not best_street:
                return {"valid": False, "reason": "Ulice neexistuje.", "suggest_streets": list(streets)}
            street_n = best_street

        # 4) číslo popisné
        cps = self.cp_by_city_psc_street[(city_n, psc_n, street_n)]
        if cp_n not in cps:
            return {"valid": False, "reason": "Číslo popisné neexistuje.", "suggest_cp": list(cps)}

        # 5) číslo orientační
        cos = self.co_by_full[(city_n, psc_n, street_n, cp_n)]
        if co_n and co_n not in cos:
            return {"valid": False, "reason": "Číslo orientační neexistuje.", "suggest_co": list(cos)}

        return {
            "valid": True,
            "normalized_address": {
                "city": city_n,
                "psc": psc_n,
                "street": street_n,
                "cp": cp_n,
                "co": co_n
            }
        }
