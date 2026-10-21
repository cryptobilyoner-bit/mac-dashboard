import requests
import pandas as pd
import os
import time

API_KEY = "123"
# Popüler Avrupa Ligleri
LIGLER = {
    "4339": "Süper Lig",
    "4328": "Premier League",
    "4335": "La Liga",
    "4332": "Serie A",
    "4331": "Bundesliga",
    "4334": "Ligue 1"
}
SEZONLAR = ["2022-2023", "2023-2024", "2024-2025", "2025-2026"]

tum_maclar = []
logolar = {}

for lig_id, lig_adi in LIGLER.items():
    for sezon in SEZONLAR:
        url = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}/eventsseason.php?id={lig_id}&s={sezon}"
        print(f"İstek gönderiliyor: {lig_adi} - {sezon}...")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            events = response.json().get("events") or []
            
            for e in events:
                if e.get("intHomeScore") is None or e.get("intAwayScore") is None:
                    continue
                ev_gol = int(e["intHomeScore"])
                dep_gol = int(e["intAwayScore"])
                tum_maclar.append({
                    "tarih": e["dateEvent"],
                    "sezon": sezon,
                    "lig": lig_adi,
                    "hafta": e.get("intRound"),
                    "ev_takim": e["strHomeTeam"],
                    "deplasman_takim": e["strAwayTeam"],
                    "ev_gol": ev_gol,
                    "dep_gol": dep_gol,
                    "sonuc": "Ev" if ev_gol > dep_gol else ("Deplasman" if dep_gol > ev_gol else "Beraberlik"),
                    "toplam_gol": ev_gol + dep_gol,
                })
                # Logoları topla
                if e.get("strHomeTeamBadge"): logolar[e["strHomeTeam"]] = e["strHomeTeamBadge"]
                if e.get("strAwayTeamBadge"): logolar[e["strAwayTeam"]] = e["strAwayTeamBadge"]
            
            print(f"  -> {len(events)} etkinlik bulundu.")
        except Exception as ex:
            print(f"  -> Hata: {ex}")
        
        # API limitine takılmamak için her istek arasında 1.5 saniye bekle
        time.sleep(1.5) 

if not tum_maclar:
    print("Hiç maç bulunamadı.")
else:
    os.makedirs("data", exist_ok=True)
    df = pd.DataFrame(tum_maclar)
    df["tarih"] = pd.to_datetime(df["tarih"])
    df = df.sort_values("tarih").reset_index(drop=True)
    df.to_csv("data/tum_maclar.csv", index=False)
    print(f"\n✅ Toplam {len(df)} maç kaydedildi -> data/tum_maclar.csv")

    logo_df = pd.DataFrame(list(logolar.items()), columns=["takim", "logo_url"])
    logo_df.to_csv("data/takim_logolari.csv", index=False)
    print(f"✅ {len(logo_df)} takımın logosu kaydedildi.")