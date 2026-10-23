from src.data import hent_selskap
from src.dcf import egenkapitalkostnad, wacc, verdsett

# ---------- FORUTSETNINGER (endre disse) ----------
TICKER = "EQNR.OL"
RISIKOFRI_RENTE = 0.04       # 10-årig statsrente i regnskapsvalutaen
MARKEDSRISIKOPREMIE = 0.05   # ekstra avkastning investorer krever for aksjer
BETA = 1.0                   # egen forutsetning, se forklaring
GJELDSKOSTNAD = 0.05         # rente selskapet betaler på gjeld
SKATTESATS = 0.22
VEKST = 0.02                 # årlig vekst i prognoseperioden
ANTALL_AR = 5                # lengde på prognoseperioden
LANGSIKTIG_VEKST = 0.01      # årlig vekst etter prognoseperioden
# --------------------------------------------------

selskap = hent_selskap(TICKER)
valuta = selskap["regnskapsvaluta"]

# Markedsverdi av egenkapitalen, omregnet til regnskapsvalutaen
markedsverdi = selskap["aksjekurs"] / selskap["valutakurs"] * selskap["antall_aksjer"]

ke = egenkapitalkostnad(RISIKOFRI_RENTE, BETA, MARKEDSRISIKOPREMIE)
diskonteringsrente = wacc(markedsverdi, selskap["netto_gjeld"], ke, GJELDSKOSTNAD, SKATTESATS)

fcf = selskap["fri_kontantstrom"]
scenarier = {
    "Siste år": fcf.iloc[-1],
    "Snitt siste 3 år": fcf.iloc[-3:].mean(),
}

print(f"=== {selskap['navn']} ({TICKER}) ===")
print(f"Netto gjeld: {selskap['netto_gjeld'] / 1e9:,.1f} mrd {valuta}")
print(f"Egenkapitalkostnad: {ke:.2%}")
print(f"WACC: {diskonteringsrente:.2%}")
print(f"Aksjekurs i dag: {selskap['aksjekurs']:,.2f} {selskap['handelsvaluta']}")

for navn, start in scenarier.items():
    resultat = verdsett(
        start_kontantstrom=start,
        vekst=VEKST,
        antall_ar=ANTALL_AR,
        diskonteringsrente=diskonteringsrente,
        langsiktig_vekst=LANGSIKTIG_VEKST,
        netto_gjeld=selskap["netto_gjeld"],
        antall_aksjer=selskap["antall_aksjer"],
        valutakurs=selskap["valutakurs"],
    )
    oppside = resultat["verdi_per_aksje"] / selskap["aksjekurs"] - 1

    print(f"\n--- Scenario: {navn} ---")
    print(f"Start-FCF: {start / 1e9:,.1f} mrd {valuta}")
    print(f"Selskapsverdi: {resultat['selskapsverdi'] / 1e9:,.1f} mrd {valuta}")
    print(f"Andel fra terminalverdi: {resultat['andel_terminalverdi']:.0%}")
    print(f"Verdi per aksje: {resultat['verdi_per_aksje']:,.2f} {selskap['handelsvaluta']}")
    print(f"Oppside/nedside mot kurs: {oppside:+.1%}")