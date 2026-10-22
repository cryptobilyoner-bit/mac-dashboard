
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import poisson
import numpy as np
import os

st.set_page_config(page_title="Süper Lig Analiz Paneli", page_icon="⚽", layout="wide")

# ---------- VERİ YÜKLEME ----------
@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/tum_maclar.csv", parse_dates=["tarih"])
    return df

@st.cache_data
def logolari_yukle():
    path = "data/takim_logolari.csv"
    if os.path.exists(path):
        return pd.read_csv(path).set_index("takim")["logo_url"].to_dict()
    return {}

df = veri_yukle()
logo_dict = logolari_yukle()
tum_takimlar = sorted(set(df["ev_takim"]) | set(df["deplasman_takim"]))

# ---------- SIDEBAR / FİLTRELER ----------
st.sidebar.header("Filtreler")
sezonlar = ["Tümü"] + sorted(df["sezon"].unique().tolist())
secili_sezon = st.sidebar.selectbox("Sezon", sezonlar)

secili_takim = st.sidebar.multiselect("Takımlar (boş = tümü)", tum_takimlar)

fdf = df.copy()
if secili_sezon != "Tümü":
    fdf = fdf[fdf["sezon"] == secili_sezon]
if secili_takim:
    fdf = fdf[fdf["ev_takim"].isin(secili_takim) | fdf["deplasman_takim"].isin(secili_takim)]

# ---------- BAŞLIK ----------
st.title("⚽ Süper Lig Analiz Dashboard'u")
st.caption(f"Görüntülenen maç sayısı: **{len(fdf)}**")

# ---------- ÜST KARTLAR ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Toplam Maç", len(fdf))
c2.metric("Ortalama Gol", round(fdf["toplam_gol"].mean(), 2) if len(fdf) else 0)
c3.metric("Ev Sahibi Galibiyeti", f"%{(fdf['sonuc']=='Ev').mean()*100:.1f}" if len(fdf) else "%0")
c4.metric("Beraberlik", f"%{(fdf['sonuc']=='Beraberlik').mean()*100:.1f}" if len(fdf) else "%0")

st.divider()

# ---------- SEKMELER (Tabs) ----------
tab1, tab2 = st.tabs(["📊 Genel İstatistikler", "🔮 Skor Tahmini (Poisson)"])

with tab1:
    # Takım Formu ve Gol Dağılımı
    sol, sag = st.columns(2)

    def takim_puanlari(team, data):
        t = data[(data["ev_takim"] == team) | (data["deplasman_takim"] == team)].copy()
        t["puan"] = t.apply(
            lambda r: 3 if (r.ev_takim == team and r.sonuc == "Ev") or (r.deplasman_takim == team and r.sonuc == "Deplasman")
            else (1 if r.sonuc == "Beraberlik" else 0), axis=1
        )
        return t.sort_values("tarih")

    with sol:
        st.subheader("📈 Takım Formu (son 10 maç)")
        sec_takim = st.selectbox("Takım seç", tum_takimlar, key="form_takim")
        tdf = takim_puanlari(sec_takim, fdf).tail(10)
        if len(tdf):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=tdf["tarih"], y=tdf["puan"].cumsum(), mode="lines+markers",
                                     name="Kümülatif Puan", line=dict(color="#00CC96", width=3)))
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Bu takım için veri yok.")

    with sag:
        st.subheader("🥅 Gol Dağılımı")
        fig = px.histogram(fdf, x="toplam_gol", nbins=15, color_discrete_sequence=["#EF553B"])
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0),
                          xaxis_title="Maçtaki Toplam Gol", yaxis_title="Maç Sayısı")
        st.plotly_chart(fig, width='stretch')

    st.divider()

    # Puan Tablosu (Logolu)
    st.subheader("🏆 Puan Tablosu")
    def puan_tablosu(data):
        rows = []
        for takim in tum_takimlar:
            ev = data[data["ev_takim"] == takim]
            dep = data[data["deplasman_takim"] == takim]
            oynanan = len(ev) + len(dep)
            if oynanan == 0: continue
            galibiyet = (ev["sonuc"] == "Ev").sum() + (dep["sonuc"] == "Deplasman").sum()
            beraberlik = (ev["sonuc"] == "Beraberlik").sum() + (dep["sonuc"] == "Beraberlik").sum()
            maglubiyet = oynanan - galibiyet - beraberlik
            atilan = ev["ev_gol"].sum() + dep["dep_gol"].sum()
            yenilen = ev["dep_gol"].sum() + dep["ev_gol"].sum()
            puan = galibiyet * 3 + beraberlik
            rows.append({"Takım": takim, "O": oynanan, "G": galibiyet, "B": beraberlik, "M": maglubiyet,
                         "A": atilan, "Y": yenilen, "AV": atilan - yenilen, "P": puan})
        return pd.DataFrame(rows).sort_values(["P", "AV"], ascending=False).reset_index(drop=True)

    tablo = puan_tablosu(fdf)
    if not tablo.empty:
        tablo.index = tablo.index + 1
        # Logoları tabloya ekle
        tablo["Logo"] = tablo["Takım"].map(lambda t: logo_dict.get(t, ""))
        # Sütun sırasını düzenle
        tablo = tablo[["Logo", "Takım", "O", "G", "B", "M", "A", "Y", "AV", "P"]]
        st.dataframe(tablo, width='stretch', hide_index=False, height=420,
                     column_config={"Logo": st.column_config.ImageColumn("Logo", width="small")})
    else:
        st.info("Seçili filtrelerde maç verisi yok.")

    st.divider()

    # Son Maçlar
    st.subheader("📋 Son Maçlar")
    son = fdf.sort_values("tarih", ascending=False).head(20)[["tarih", "ev_takim", "ev_gol", "dep_gol", "deplasman_takim", "sonuc"]].copy()
    son["tarih"] = son["tarih"].dt.strftime("%d.%m.%Y")
    son.columns = ["Tarih", "Ev", "Ev Gol", "Dep Gol", "Deplasman", "Sonuç"]
    st.dataframe(son, width='stretch', hide_index=True)

with tab2:
    st.header("🔮 Poisson Modeli ile Skor Tahmini")
    st.caption("Bu bölüm, seçilen iki takımın geçmiş gol istatistiklerine dayanarak olası skorları hesaplar. Bahis tavsiyesi değildir.")

    def takim_gucu(team, data):
        ev = data[data["ev_takim"] == team]
        dep = data[data["deplasman_takim"] == team]
        mac_sayisi = len(ev) + len(dep)
        if mac_sayisi == 0: return 0, 0
        atilan = ev["ev_gol"].sum() + dep["dep_gol"].sum()
        yenilen = ev["dep_gol"].sum() + dep["ev_gol"].sum()
        return atilan / mac_sayisi, yenilen / mac_sayisi

    col_a, col_b = st.columns(2)
    with col_a:
        ev_takim = st.selectbox("Ev Sahibi Takım", tum_takimlar, key="poisson_ev")
    with col_b:
        dep_takim = st.selectbox("Deplasman Takımı", tum_takimlar, key="poisson_dep")

    if ev_takim == dep_takim:
        st.warning("Lütfen iki farklı takım seçin.")
    else:
        lig_ort_gol = fdf["toplam_gol"].mean() / 2 if len(fdf) > 0 else 1.3
        ev_atak, ev_defans = takim_gucu(ev_takim, fdf)
        dep_atak, dep_defans = takim_gucu(dep_takim, fdf)

        # Basit Poisson beklenti golleri (λ)
        # Ev sahibi avantajı için 1.1 çarpanı
        lambda_ev = max(0.1, ev_atak * (dep_defans / lig_ort_gol) * 1.1) if dep_defans > 0 else ev_atak
        lambda_dep = max(0.1, dep_atak * (ev_defans / lig_ort_gol) * 0.9) if ev_defans > 0 else dep_atak

        st.markdown(f"**{ev_takim}** beklenen gol: `{lambda_ev:.2f}` | **{dep_takim}** beklenen gol: `{lambda_dep:.2f}`")

        max_gol = 6
        olasiliklar = []
        for i in range(max_gol + 1):
            for j in range(max_gol + 1):
                olasilik = poisson.pmf(i, lambda_ev) * poisson.pmf(j, lambda_dep)
                olasiliklar.append({"Ev Gol": i, "Dep Gol": j, "Olasılık": olasilik})

        olasilik_df = pd.DataFrame(olasiliklar)
        matris = olasilik_df.pivot(index="Ev Gol", columns="Dep Gol", values="Olasılık").fillna(0)

        st.subheader("Skor Olasılık Matrisi (%)")
        fig_matris = px.imshow(matris * 100, text_auto=".1f", aspect="auto",
                               labels=dict(x=f"{dep_takim} Gol", y=f"{ev_takim} Gol", color="Olasılık (%)"),
                               color_continuous_scale="Blues")
        fig_matris.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_matris, width='stretch')

        ev_galibiyet = matris.values[np.tril_indices_from(matris, k=-1)].sum()
        beraberlik = np.diag(matris.values).sum()
        dep_galibiyet = matris.values[np.triu_indices_from(matris, k=1)].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric(f"{ev_takim} Galibiyeti", f"%{ev_galibiyet*100:.1f}")
        c2.metric("Beraberlik", f"%{beraberlik*100:.1f}")
        c3.metric(f"{dep_takim} Galibiyeti", f"%{dep_galibiyet*100:.1f}")

        en_olasi = olasilik_df.sort_values("Olasılık", ascending=False).head(3)
        st.subheader("En Olası 3 Skor")
        for idx, row in en_olasi.iterrows():
            st.write(f"**{ev_takim} {int(row['Ev Gol'])} - {int(row['Dep Gol'])} {dep_takim}**  →  %{row['Olasılık']*100:.1f}")
