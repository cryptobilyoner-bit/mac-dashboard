import pandas as pd
import numpy as np
import os

np.random.seed(42)

LIGLER = {
    "Süper Lig": ["Galatasaray", "Fenerbahçe", "Beşiktaş", "Trabzonspor", "Başakşehir", "Adana Demirspor", "Antalyaspor", "Konyaspor", "Alanyaspor", "Sivasspor"],
    "Premier League": ["Man City", "Arsenal", "Liverpool", "Man United", "Chelsea", "Tottenham", "Newcastle", "Aston Villa", "Brighton", "West Ham"],
    "La Liga": ["Real Madrid", "Barcelona", "Atletico Madrid", "Girona", "Athletic Bilbao", "Real Sociedad", "Real Betis", "Valencia", "Villarreal", "Sevilla"],
    "Serie A": ["Inter", "AC Milan", "Juventus", "Napoli", "Roma", "Lazio", "Atalanta", "Fiorentina", "Bologna", "Torino"],
    "Bundesliga": ["Bayern Munich", "Leverkusen", "Stuttgart", "RB Leipzig", "Dortmund", "Frankfurt", "Freiburg", "Hoffenheim", "Wolfsburg", "Union Berlin"],
    "Ligue 1": ["PSG", "Monaco", "Brest", "Lille", "Nice", "Lens", "Lyon", "Marseille", "Rennes", "Toulouse"]
}

SEZONLAR = ["2022-2023", "2023-2024", "2024-2025", "2025-2026"]

tum_maclar = []
logolar = {}

for lig_adi, takimlar in LIGLER.items():
    for sezon in SEZONLAR:
        # Her takımın gücünü rastgele belirle
        guc = {t: np.random.uniform(1.0, 2.5) for t in takimlar}
        
        # 10 takım olduğu için çift devreli 18 hafta
        for hafta in range(1, 19):
            for i in range(0, len(takimlar), 2):
                ev = takimlar[i]
                dep = takimlar[i+1]
                
                ev_gol = np.random.poisson(guc[ev] * 1.3) # Ev sahibi avantajı
                dep_gol = np.random.poisson(guc[dep] * 0.9)
                
                tum_maclar.append({
                    "tarih": f"2023-{(hafta%12)+1:02d}-{(hafta%28)+1:02d}", # Basit tarih ataması
                    "sezon": sezon,
                    "lig": lig_adi,
                    "hafta": hafta,
                    "ev_takim": ev,
                    "deplasman_takim": dep,
                    "ev_gol": ev_gol,
                    "dep_gol": dep_gol,
                    "sonuc": "Ev" if ev_gol > dep_gol else ("Deplasman" if dep_gol > ev_gol else "Beraberlik"),
                    "toplam_gol": ev_gol + dep_gol,
                })
                # Logolar için rastgele bir URL (Streamlit'te görsel çıkması için)
                if ev not in logolar:
                    logolar[ev] = "https://upload.wikimedia.org/wikipedia/en/thumb/1/1e/Football_icon.svg/100px-Football_icon.svg.png"
                if dep not in logolar:
                    logolar[dep] = "https://upload.wikimedia.org/wikipedia/en/thumb/1/1e/Football_icon.svg/100px-Football_icon.svg.png"

# Veriyi Kaydet
df = pd.DataFrame(tum_maclar)
df["tarih"] = pd.to_datetime(df["tarih"])
df.to_csv("data/tum_maclar.csv", index=False)

# Logoları Kaydet
logo_df = pd.DataFrame(list(logolar.items()), columns=["takim", "logo_url"])
logo_df.to_csv("data/takim_logolari.csv", index=False)

print(f"✅ Harika! {len(df)} maçtan oluşan DEV veri seti oluşturuldu.")
print(f"✅ {len(logo_df)} takım için logo kaydedildi.")