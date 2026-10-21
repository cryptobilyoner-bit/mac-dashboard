import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Mac Analiz Paneli", page_icon="⚽", layout="wide")


@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/gercek_maclar.csv", parse_dates=["tarih"])
    return df


# Sidebar'a dosya yükleme alanı
st.sidebar.header("Veri Kaynağı")
yuklenen_dosya = st.sidebar.file_uploader("CSV dosyası yükle (opsiyonel)", type=["csv"])

if yuklenen_dosya is not None:
    df = pd.read_csv(yuklenen_dosya, parse_dates=["tarih"])
    st.sidebar.success(f"{len(df)} maç yüklendi")
else:
    df = veri_yukle()
    st.sidebar.info("Örnek veri kullanılıyor")

# ---------- SIDEBAR / FILTRELER ----------
st.sidebar.header("Filtreler")

sezonlar = ["Tumu"] + sorted(df["sezon"].unique().tolist())
secili_sezon = st.sidebar.selectbox("Sezon", sezonlar)

tum_takimlar = sorted(set(df["ev_takim"]) | set(df["deplasman_takim"]))
secili_takim = st.sidebar.multiselect("Takimlar (bos = tumu)", tum_takimlar)

fdf = df.copy()
if secili_sezon != "Tumu":
    fdf = fdf[fdf["sezon"] == secili_sezon]
if secili_takim:
    fdf = fdf[fdf["ev_takim"].isin(secili_takim) | fdf["deplasman_takim"].isin(secili_takim)]

# ---------- BASLIK ----------
st.title("⚽ Mac Analiz Dashboard'u")
st.caption(f"Goruntulenen mac sayisi: {len(fdf)}")

# ---------- UST KARTLAR ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Toplam Mac", len(fdf))
c2.metric("Ortalama Gol", round(fdf["toplam_gol"].mean(), 2) if len(fdf) else 0)
c3.metric("Ev Sahibi Galibiyeti",
          f"%{(fdf['sonuc']=='Ev').mean()*100:.1f}" if len(fdf) else "%0")
c4.metric("Beraberlik",
          f"%{(fdf['sonuc']=='Beraberlik').mean()*100:.1f}" if len(fdf) else "%0")

st.divider()

# ---------- GRAFIKLER ----------
sol, sag = st.columns(2)


def takim_puanlari(team, data):
    t = data[(data["ev_takim"] == team) | (data["deplasman_takim"] == team)].copy()
    t["puan"] = t.apply(
        lambda r: 3 if (r.ev_takim == team and r.sonuc == "Ev")
                  or (r.deplasman_takim == team and r.sonuc == "Deplasman")
                  else (1 if r.sonuc == "Beraberlik" else 0),
        axis=1,
    )
    return t.sort_values("tarih")


with sol:
    st.subheader("Takim Formu (son 10 mac)")
    sec_takim = st.selectbox("Takim sec", tum_takimlar, key="form_takim")
    tdf = takim_puanlari(sec_takim, fdf).tail(10)
    if len(tdf):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=tdf["tarih"],
                y=tdf["puan"].cumsum(),
                mode="lines+markers",
                name="Kumulatif Puan",
                line=dict(color="#00CC96", width=3),
            )
        )
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Bu takim icin veri yok.")

with sag:
    st.subheader("Gol Dagilimi")
    fig = px.histogram(fdf, x="toplam_gol", nbins=15,
                       color_discrete_sequence=["#EF553B"])
    fig.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Mactaki Toplam Gol",
        yaxis_title="Mac Sayisi",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- PUAN TABLOSU ----------
st.subheader("Puan Tablosu")


def puan_tablosu(data):
    rows = []
    for takim in tum_takimlar:
        ev = data[data["ev_takim"] == takim]
        dep = data[data["deplasman_takim"] == takim]
        oynanan = len(ev) + len(dep)
        galibiyet = (ev["sonuc"] == "Ev").sum() + (dep["sonuc"] == "Deplasman").sum()
        beraberlik = (ev["sonuc"] == "Beraberlik").sum() + (dep["sonuc"] == "Beraberlik").sum()
        maglubiyet = oynanan - galibiyet - beraberlik
        atilan = ev["ev_gol"].sum() + dep["dep_gol"].sum()
        yenilen = ev["dep_gol"].sum() + dep["ev_gol"].sum()
        puan = galibiyet * 3 + beraberlik
        rows.append(
            {
                "Takim": takim, "O": oynanan, "G": galibiyet, "B": beraberlik,
                "M": maglubiyet, "A": atilan, "Y": yenilen,
                "AV": atilan - yenilen, "P": puan,
            }
        )
    return pd.DataFrame(rows).sort_values(["P", "AV"], ascending=False).reset_index(drop=True)


tablo = puan_tablosu(fdf)
tablo.index = tablo.index + 1
st.dataframe(tablo, use_container_width=True, height=420)

st.divider()

# ---------- SON MACLAR ----------
st.subheader("Son Maclar")
son = fdf.sort_values("tarih", ascending=False).head(20)[
    ["tarih", "ev_takim", "ev_gol", "dep_gol", "deplasman_takim", "sonuc"]
].copy()
son["tarih"] = son["tarih"].dt.strftime("%d.%m.%Y")
son.columns = ["Tarih", "Ev", "Ev Gol", "Dep Gol", "Deplasman", "Sonuc"]
st.dataframe(son, use_container_width=True, hide_index=True)