"""Automatiske tester av DCF-formlene.

Hver test regner ut et svar vi kjenner fra før (regnet for hånd),
og sjekker at koden gir det samme. Kjør alle med: pytest
"""

import pandas as pd
import pytest

from src.data import hent_rad, siste_verdi
from src.dcf import (
    egenkapitalkostnad,
    fremskriv_kontantstrom,
    naverdi,
    sensitivitet,
    terminalverdi,
    verdsett,
    wacc,
)


# ---------- CAPM og WACC ----------

def test_egenkapitalkostnad_capm():
    # 4 % + 1,2 * 5 % = 10 %
    assert egenkapitalkostnad(0.04, 1.2, 0.05) == pytest.approx(0.10)


def test_wacc_med_gjeld():
    # 60 % EK til 10 %, 40 % gjeld til 5 % etter 22 % skatt
    # 0,6 * 10 % + 0,4 * 5 % * 0,78 = 6 % + 1,56 % = 7,56 %
    assert wacc(60, 40, 0.10, 0.05, 0.22) == pytest.approx(0.0756)


def test_wacc_uten_gjeld_er_lik_egenkapitalkostnad():
    assert wacc(100, 0, 0.09, 0.05, 0.22) == pytest.approx(0.09)


def test_wacc_netto_kontanter_gir_ingen_gjeldsvekt():
    # Negativ netto gjeld skal ikke gi negativ vekt
    assert wacc(100, -20, 0.09, 0.05, 0.22) == pytest.approx(0.09)


# ---------- Kontantstrømmer og nåverdi ----------

def test_fremskriv_kontantstrom():
    assert fremskriv_kontantstrom(100, 0.10, 3) == pytest.approx([110, 121, 133.1])


def test_naverdi_ett_ar():
    # 110 om ett år med 10 % rente er verdt 100 i dag
    assert naverdi([110], 0.10) == pytest.approx(100)


def test_naverdi_flere_ar():
    # 110/1,1 + 121/1,21 = 100 + 100
    assert naverdi([110, 121], 0.10) == pytest.approx(200)


# ---------- Terminalverdi ----------

def test_terminalverdi_gordon():
    # 100 * 1,02 / (0,10 - 0,02) = 1275
    assert terminalverdi(100, 0.10, 0.02) == pytest.approx(1275)


def test_terminalverdi_uten_vekst_er_evig_annuitet():
    # 100 / 0,10 = 1000
    assert terminalverdi(100, 0.10, 0.0) == pytest.approx(1000)


def test_terminalverdi_feiler_hvis_vekst_er_hoyere_enn_rente():
    with pytest.raises(ValueError):
        terminalverdi(100, 0.03, 0.05)


# ---------- Hele verdsettelsen ----------

def test_verdsett_konstant_kontantstrom():
    # Uten vekst er selskapet en evig annuitet: 100 / 0,10 = 1000.
    # Minus netto gjeld 200 = 800, delt på 10 aksjer = 80 per aksje.
    resultat = verdsett(
        start_kontantstrom=100,
        vekst=0.0,
        antall_ar=5,
        diskonteringsrente=0.10,
        langsiktig_vekst=0.0,
        netto_gjeld=200,
        antall_aksjer=10,
    )
    assert resultat["selskapsverdi"] == pytest.approx(1000)
    assert resultat["egenkapitalverdi"] == pytest.approx(800)
    assert resultat["verdi_per_aksje"] == pytest.approx(80)


def test_verdsett_valutaomregning():
    felles = dict(start_kontantstrom=100, vekst=0.0, antall_ar=5,
                  diskonteringsrente=0.10, langsiktig_vekst=0.0,
                  netto_gjeld=200, antall_aksjer=10)
    i_dollar = verdsett(**felles)["verdi_per_aksje"]
    i_kroner = verdsett(**felles, valutakurs=10)["verdi_per_aksje"]
    assert i_kroner == pytest.approx(i_dollar * 10)


def test_hoyere_wacc_gir_lavere_verdi():
    felles = dict(start_kontantstrom=100, vekst=0.02, antall_ar=5,
                  langsiktig_vekst=0.01, netto_gjeld=0, antall_aksjer=10)
    lav = verdsett(diskonteringsrente=0.08, **felles)["verdi_per_aksje"]
    hoy = verdsett(diskonteringsrente=0.12, **felles)["verdi_per_aksje"]
    assert lav > hoy


# ---------- Sensitivitet ----------

def test_sensitivitet_hopper_over_ugyldige_kombinasjoner():
    tabell = sensitivitet(
        [0.02, 0.10], [0.0, 0.03],
        start_kontantstrom=100, vekst=0.0, antall_ar=5,
        netto_gjeld=0, antall_aksjer=10,
    )
    assert pd.isna(tabell.loc[0.02, 0.03])          # rente < vekst
    assert tabell.loc[0.10, 0.0] == pytest.approx(100)  # 1000 / 10 aksjer


# ---------- Datarydding ----------

def test_hent_rad_sorterer_og_fjerner_tomme_ar():
    tabell = pd.DataFrame(
        {
            pd.Timestamp("2025-12-31"): [5.0],
            pd.Timestamp("2024-12-31"): [7.0],
            pd.Timestamp("2021-12-31"): [None],
        },
        index=["Free Cash Flow"],
    )
    rad = hent_rad(tabell, "Free Cash Flow")
    assert list(rad.index) == [2024, 2025]
    assert list(rad.values) == [7.0, 5.0]


def test_hent_rad_som_mangler_gir_tom_serie():
    tabell = pd.DataFrame({pd.Timestamp("2025-12-31"): [1.0]}, index=["A"])
    assert hent_rad(tabell, "Finnes ikke").empty
    assert siste_verdi(hent_rad(tabell, "Finnes ikke")) == 0.0