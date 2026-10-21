import requests
import pandas as pd
import os

API_KEY = "123"
LIG_ID = "4339"
SEZON = "2025-2026"

url = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}/eventsseason.php?id={LIG_ID}&s={SEZON}"
print("Istek gonderiliyor:", url)

response = requests.get(url, timeout=30)
response.raise_for_status()
data = response.json()

events = data.get("events") or []
print(f"{len(events)} etkinlik bulundu.")

maclar = []
for e in events:
    if e.get("intHomeScore") is None or e.get("intAwayScore") is None:
        continue
    ev_gol = int(e["intHomeScore"])
    dep_gol = int(e["intAwayScore"])
    maclar.append({
        "tarih": e["dateEvent"],
        "sezon": SEZON,
        "hafta": e.get("intRound"),
        "ev_takim": e["strHomeTeam"],
        "deplasman_takim": e["strAwayTeam"],
        "ev_gol": ev_gol,
        "dep_gol": dep_gol,
        "sonuc": "Ev" if ev_gol > dep_gol else ("Deplasman" if dep_gol > ev_gol else "Beraberlik"),
        "toplam_gol": ev_gol + dep_gol,
    })

if not maclar:
    print("Oynanmis mac bulunamadi. Sezon parametresini kontrol et.")
else:
    os.makedirs("data", exist_ok=True)
    df = pd.DataFrame(maclar)
    df["tarih"] = pd.to_datetime(df["tarih"])
    df.to_csv("data/gercek_maclar.csv", index=False)
    print(f"{len(df)} mac kaydedildi -> data/gercek_maclar.csv")
    print(df.head())