import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import poisson
import numpy as np
import os

st.set_page_config(page_title="Dünya Futbolu Analizi", page_icon="⚽", layout="wide")

# ---------- VERİ YÜKLEME ----------
@st.cache_data
def veri_yukle():
    return pd.read_csv("data/tum_maclar.csv", parse_dates=["tarih"])

@st.cache_data
def logolari_yukle():
    path = "data/takim_logolari.csv"
    if os.path.exists(path):
        return pd.read_csv(path).set_index("takim")["logo_url"].to_dict()
    return {}

df = veri_yukle()
logo_dict = logolari_yukle()

# ---------- SIDEBAR FİLTRELERİ ----------
st.sidebar.header("🎛️ Filtreler")

# 1. Lig Filtresi
secilen_ligler = st.sidebar.multiselect(
    "Ligler", sorted(df["lig"].unique()), default=sorted(df["lig"].unique())
)

# 2. Sezon Filtresi
secilen_sezonlar = st.sidebar.multiselect(
    "Sezonlar", sorted(df["sezon"].unique(), reverse=True), default=sorted(df["sezon"].unique(), reverse=True)
)

# Filtreleme işlemi
fdf = df[df["lig"].isin(secilen_ligler) & df["sezon"].isin(secilen_sezonlar)]

# 3. Takım Filtresi (Seçilen liglere göre güncellenir)
tum_takimlar = sorted(set(fdf["ev_takim"]) | set(fdf["deplasman_takim"]))
secilen_takimlar = st.sidebar.multiselect("Takımlar (boş = tümü)", tum_takimlar)

if secilen_takimlar:
    fdf = fdf[fdf["ev_takim"].isin(secilen_takimlar) | fdf["deplasman_takim"].isin(secilen_takimlar)]

# ---------- BAŞLIK VE METRİKLER ----------
st.title("⚽ Dünya Futbolu Analiz Merkezi")
st.caption(f"Seçili Kriterlerdeki Maç Sayısı: **{len(fdf)}**")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Toplam Maç", len(fdf))
c2.metric("Ortalama Gol", round(fdf["toplam_gol"].mean(), 2) if len(fdf) else 0)
c3.metric("Ev Sahibi Galibiyeti", f"%{(fdf['sonuc']=='Ev').mean()*100:.1f}" if len(fdf) else "%0")
c4.metric("Deplasman Galibiyeti", f"%{(fdf['sonuc']=='Deplasman').mean()*100:.1f}" if len(fdf) else "%0")

st.divider()

# ---------- SEKMELER (TABS) ----------
tab1, tab2, tab3 = st.tabs(["📊 Genel İstatistikler", "⚔️ Kafa Kafaya (H2H)", "🔮 Skor Tahmini (Poisson)"])

# ================= TAB 1: GENEL İSTATİSTİKLER =================
with tab1:
    sol, sag = st.columns([1, 1])
    
    with sol:
        st.subheader("🏆 Puan Tablosu")
        # Lig bazlı puan tablosu seçimi
        lig_secim_tablo = st.selectbox("Puan tablosu için lig seçin", secilen_ligler)
        tablo_fdf = fdf[fdf["lig"] == lig_secim_tablo]
        
        def puan_tablosu(data):
            rows = []
            for takim in sorted(set(data["ev_takim"]) | set(data["deplasman_takim"])):
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
                rows.append({"Logo": logo_dict.get(takim, ""), "Takım": takim, "O": oynanan, "G": galibiyet, 
                             "B": beraberlik, "M": maglubiyet, "A": atilan, "Y": yenilen, "AV": atilan - yenilen, "P": puan})
            return pd.DataFrame(rows).sort_values(["P", "AV"], ascending=False).reset_index(drop=True)

        tablo = puan_tablosu(tablo_fdf)
        if not tablo.empty:
            tablo.index = tablo.index + 1
            st.dataframe(tablo, use_container_width=True, height=400,
                         column_config={"Logo": st.column_config.ImageColumn("", width="small")})
        else:
            st.info("Bu ligde veri bulunmuyor.")

    with sag:
        st.subheader("🥅 Gol Dağılımı")
        fig_hist = px.histogram(fdf, x="toplam_gol", nbins=15, color="lig", barmode="overlay",
                                labels={"toplam_gol": "Toplam Gol", "lig": "Lig"})
        fig_hist.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.subheader("📋 Son Oynanan Maçlar")
        son = fdf.sort_values("tarih", ascending=False).head(10)[["tarih", "lig", "ev_takim", "ev_gol", "dep_gol", "deplasman_takim"]].copy()
        son["tarih"] = son["tarih"].dt.strftime("%d.%m.%Y")
        son.columns = ["Tarih", "Lig", "Ev", "Ev Gol", "Dep Gol", "Deplasman"]
        st.dataframe(son, use_container_width=True, hide_index=True, height=200)

# ================= TAB 2: KAFA KAFAYA (H2H) =================
with tab2:
    st.header("⚔️ Kafa Kafaya Karşılaştırma")
    st.caption("İki takım seçin, aralarındaki geçmiş maçları inceleyin.")
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        takim_a = st.selectbox("1. Takım", tum_takimlar, index=0)
    with col_h2:
        takim_b = st.selectbox("2. Takım", tum_takimlar, index=1 if len(tum_takimlar)>1 else 0)
        
    if takim_a == takim_b:
        st.warning("Lütfen iki farklı takım seçin.")
    else:
        h2h_df = fdf[((fdf["ev_takim"] == takim_a) & (fdf["deplasman_takim"] == takim_b)) | 
                     ((fdf["ev_takim"] == takim_b) & (fdf["deplasman_takim"] == takim_a))]
        
        if len(h2h_df) == 0:
            st.info("Seçili filtrelerde bu iki takım arasında oynanmış maç bulunamadı.")
        else:
            a_galibiyet = len(h2h_df[(h2h_df["ev_takim"] == takim_a) & (h2h_df["sonuc"] == "Ev")]) + \
                          len(h2h_df[(h2h_df["deplasman_takim"] == takim_a) & (h2h_df["sonuc"] == "Deplasman")])
            b_galibiyet = len(h2h_df[(h2h_df["ev_takim"] == takim_b) & (h2h_df["sonuc"] == "Ev")]) + \
                          len(h2h_df[(h2h_df["deplasman_takim"] == takim_b) & (h2h_df["sonuc"] == "Deplasman")])
            beraberlik = len(h2h_df[h2h_df["sonuc"] == "Beraberlik"])
            
            fig_pie = px.pie(values=[a_galibiyet, beraberlik, b_galibiyet], 
                             names=[f"{takim_a} Galibiyeti", "Beraberlik", f"{takim_b} Galibiyeti"],
                             color_discrete_sequence=["#00CC96", "#636EFA", "#EF553B"], hole=0.4)
            fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            
            cl, cr = st.columns([1, 1])
            with cl:
                st.plotly_chart(fig_pie, use_container_width=True)
            with cr:
                st.markdown(f"**Toplam Oynanan Maç:** {len(h2h_df)}")
                st.markdown(f"**{takim_a}:** {a_galibiyet} Galibiyet")
                st.markdown(f"**Beraberlik:** {beraberlik}")
                st.markdown(f"**{takim_b}:** {b_galibiyet} Galibiyet")
            
            st.subheader("Son Karşılaşmalar")
            h2h_show = h2h_df.sort_values("tarih", ascending=False)[["tarih", "lig", "ev_takim", "ev_gol", "dep_gol", "deplasman_takim"]].copy()
            h2h_show["tarih"] = h2h_show["tarih"].dt.strftime("%d.%m.%Y")
            st.dataframe(h2h_show, use_container_width=True, hide_index=True)

# ================= TAB 3: POISSON TAHMİNİ =================
with tab3:
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
        st.plotly_chart(fig_matris, use_container_width=True)

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
