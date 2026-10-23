"""Streamlit-app: DCF-verdsettelse av selskaper på Oslo Børs."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.data import hent_selskap
from src.dcf import egenkapitalkostnad, sensitivitet, verdsett, wacc

st.set_page_config(page_title="DCF Oslo Børs", page_icon="📈", layout="wide")


@st.cache_data(ttl=3600, show_spinner="Henter data fra Yahoo Finance ...")
def last_selskap(ticker):
    """Henter selskapsdata, og husker svaret i en time så appen går raskere."""
    return hent_selskap(ticker)


# ---------- Sidepanel: forutsetninger ----------
st.sidebar.header("Selskap")
ticker = st.sidebar.text_input("Ticker", value="EQNR.OL", help="Oslo Børs-aksjer slutter på .OL, f.eks. DNB.OL").strip().upper()

st.sidebar.header("Avkastningskrav")
risikofri = st.sidebar.slider("Risikofri rente (%)", 0.0, 8.0, 4.0, 0.1) / 100
mrp = st.sidebar.slider("Markedsrisikopremie (%)", 3.0, 8.0, 5.0, 0.1) / 100
beta = st.sidebar.slider("Beta", 0.3, 2.0, 1.0, 0.05)
gjeldskostnad = st.sidebar.slider("Gjeldskostnad (%)", 1.0, 10.0, 5.0, 0.1) / 100
skatt = st.sidebar.slider("Skattesats (%)", 0.0, 40.0, 22.0, 1.0) / 100

st.sidebar.header("Kontantstrøm og vekst")
grunnlag = st.sidebar.radio("Start-FCF", ["Snitt siste 3 år", "Siste år"])
vekst = st.sidebar.slider("Vekst i prognoseperioden (%)", -5.0, 15.0, 2.0, 0.5) / 100
antall_ar = st.sidebar.slider("Antall prognoseår", 3, 10, 5)
langsiktig_vekst = st.sidebar.slider("Langsiktig vekst (%)", 0.0, 3.0, 1.0, 0.1) / 100

# ---------- Hent data ----------
st.title("📈 DCF-verdsettelse")

try:
    selskap = last_selskap(ticker)
except Exception:
    st.error(f"Fant ikke data for «{ticker}». Sjekk at tickeren er riktig, f.eks. DNB.OL.")
    st.stop()

fcf = selskap["fri_kontantstrom"]
if fcf.empty or not selskap["antall_aksjer"]:
    st.error("Yahoo Finance mangler fri kontantstrøm eller antall aksjer for dette selskapet.")
    st.stop()

valuta = selskap["regnskapsvaluta"]
handelsvaluta = selskap["handelsvaluta"]
kurs = selskap["aksjekurs"]
start_fcf = fcf.iloc[-1] if grunnlag == "Siste år" else fcf.iloc[-3:].mean()

if start_fcf <= 0:
    st.warning("Start-FCF er negativ. En DCF gir da ingen meningsfull verdi.")

# ---------- Beregning ----------
markedsverdi = kurs / selskap["valutakurs"] * selskap["antall_aksjer"]
ke = egenkapitalkostnad(risikofri, beta, mrp)
diskonteringsrente = wacc(markedsverdi, selskap["netto_gjeld"], ke, gjeldskostnad, skatt)

if diskonteringsrente <= langsiktig_vekst:
    st.error("WACC må være høyere enn langsiktig vekst. Juster forutsetningene.")
    st.stop()

felles = dict(
    start_kontantstrom=start_fcf,
    vekst=vekst,
    antall_ar=antall_ar,
    netto_gjeld=selskap["netto_gjeld"],
    antall_aksjer=selskap["antall_aksjer"],
    valutakurs=selskap["valutakurs"],
)
resultat = verdsett(diskonteringsrente=diskonteringsrente, langsiktig_vekst=langsiktig_vekst, **felles)
verdi = resultat["verdi_per_aksje"]
oppside = verdi / kurs - 1

# ---------- Nøkkeltall ----------
st.subheader(f"{selskap['navn']} ({ticker})")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Verdi per aksje", f"{verdi:,.0f} {handelsvaluta}", f"{oppside:+.1%} mot kurs")
k2.metric("Aksjekurs i dag", f"{kurs:,.0f} {handelsvaluta}")
k3.metric("WACC", f"{diskonteringsrente:.2%}")
k4.metric("Andel fra terminalverdi", f"{resultat['andel_terminalverdi']:.0%}")

if valuta != handelsvaluta:
    st.info(
        f"Regnskapet er i {valuta}, aksjen handles i {handelsvaluta}. "
        f"Verdien er regnet om med kurs {selskap['valutakurs']:.2f}. "
        f"Risikofri rente bør derfor være statsrenten i {valuta}."
    )

# ---------- Kontantstrømmer ----------
venstre, hoyre = st.columns(2)

with venstre:
    st.markdown(f"**Fri kontantstrøm (mrd {valuta})**")
    siste_ar = int(fcf.index[-1])
    historikk = pd.Series(fcf.values / 1e9, index=fcf.index.astype(str))
    prognose = pd.Series(
        np.array(resultat["kontantstrommer"]) / 1e9,
        index=[str(siste_ar + i) for i in range(1, antall_ar + 1)],
    )
    st.bar_chart(pd.DataFrame({"Historisk": historikk, "Prognose": prognose}))

with hoyre:
    st.markdown(f"**Fra selskapsverdi til verdi per aksje (mrd {valuta})**")
    bro = pd.DataFrame(
        {
            "Mrd": [
                resultat["nv_kontantstrommer"] / 1e9,
                resultat["nv_terminalverdi"] / 1e9,
                resultat["selskapsverdi"] / 1e9,
                -selskap["netto_gjeld"] / 1e9,
                resultat["egenkapitalverdi"] / 1e9,
            ]
        },
        index=[
            "Nåverdi prognoseår",
            "Nåverdi terminalverdi",
            "= Selskapsverdi",
            "− Netto gjeld",
            "= Egenkapitalverdi",
        ],
    )
    st.dataframe(bro.style.format("{:,.1f}"), width="stretch")

# ---------- Sensitivitet ----------
st.markdown(f"**Sensitivitet: verdi per aksje ({handelsvaluta})**")
renter = np.round(diskonteringsrente + np.array([-0.02, -0.01, 0.0, 0.01, 0.02]), 4)
vekstrater = np.round(langsiktig_vekst + np.array([-0.01, -0.005, 0.0, 0.005, 0.01]), 4)
vekstrater = vekstrater[vekstrater >= 0]
tabell = sensitivitet(renter, vekstrater, **felles)

fig, ax = plt.subplots(figsize=(7, 4))
bilde = ax.imshow(tabell.values / kurs - 1, cmap="RdYlGn", vmin=-0.5, vmax=0.5)
ax.set_xticks(range(len(vekstrater)), [f"{g:.1%}" for g in vekstrater])
ax.set_yticks(range(len(renter)), [f"{r:.1%}" for r in renter])
ax.set_xlabel("Langsiktig vekst")
ax.set_ylabel("WACC")
for i in range(tabell.shape[0]):
    for j in range(tabell.shape[1]):
        celle = tabell.values[i, j]
        if not np.isnan(celle):
            ax.text(j, i, f"{celle:.0f}", ha="center", va="center")
fig.colorbar(bilde, ax=ax, label="Oppside/nedside")
fig.tight_layout()
kol, _ = st.columns([3, 2])
kol.pyplot(fig)

st.caption(
    "Data fra Yahoo Finance. Modellen er laget for læring og er ikke investeringsråd. "
    "Resultatet er aldri bedre enn forutsetningene."
)
