import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)

takimlar = ["Galatasaray", "Fenerbahce", "Besiktas", "Trabzonspor",
            "Basaksehir", "Adana Demirspor", "Antalyaspor", "Konyaspor",
            "Alanyaspor", "Sivasspor", "Kasimpasa", "Kayserispor"]

guc = {t: np.random.uniform(0.8, 2.2) for t in takimlar}

maclar = []
baslangic = datetime(2022, 8, 1)

for hafta in range(3 * 34):
    np.random.shuffle(takimlar)
    for i in range(0, len(takimlar), 2):
        ev, dep = takimlar[i], takimlar[i + 1]
        ev_gol = np.random.poisson(guc[ev] * 1.3)
        dep_gol = np.random.poisson(guc[dep] * 0.9)
        maclar.append({
            "tarih": (baslangic + timedelta(days=hafta * 7)).strftime("%Y-%m-%d"),
            "sezon": f"2022-{(hafta // 34) + 23}" if hafta // 34 == 0
                     else f"2023-{(hafta // 34) + 23}",
            "hafta": (hafta % 34) + 1,
            "ev_takim": ev,
            "deplasman_takim": dep,
            "ev_gol": ev_gol,
            "dep_gol": dep_gol,
            "sonuc": "Ev" if ev_gol > dep_gol else ("Deplasman" if dep_gol > ev_gol else "Beraberlik"),
            "toplam_gol": ev_gol + dep_gol,
        })

os.makedirs("data", exist_ok=True)
pd.DataFrame(maclar).to_csv("data/maclar.csv", index=False)
print(f"{len(maclar)} mac olusturuldu -> data/maclar.csv")