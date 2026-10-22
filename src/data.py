"""Henter og rydder data for et børsnotert selskap fra Yahoo Finance."""

import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", message=".*inplace keyword.*")


def hent_rad(tabell, radnavn):
    """Henter én rad fra en regnskapstabell som en tidsserie.

    Returnerer tallene sortert fra eldste til nyeste år, med årstall
    som indeks. Mangler raden, returneres en tom serie.
    """
    if tabell is None or radnavn not in tabell.index:
        return pd.Series(dtype=float)
    rad = tabell.loc[radnavn].dropna()
    rad.index = pd.to_datetime(rad.index).year
    return rad.sort_index().astype(float)


def siste_verdi(serie, standard=0.0):
    """Returnerer siste (nyeste) verdi i en serie, eller en standardverdi."""
    if serie.empty:
        return standard
    return float(serie.iloc[-1])


def hent_valutakurs(fra_valuta, til_valuta):
    """Henter hvor mange enheter av til_valuta én enhet av fra_valuta koster."""
    if fra_valuta == til_valuta:
        return 1.0
    kurser = yf.Ticker(f"{fra_valuta}{til_valuta}=X").history(period="5d")["Close"]
    return float(kurser.iloc[-1])


def hent_selskap(ticker):
    """Samler alt DCF-modellen trenger om ett selskap i en ordbok."""
    aksje = yf.Ticker(ticker)
    info = aksje.info

    regnskapsvaluta = info.get("financialCurrency", "NOK")
    handelsvaluta = info.get("currency", "NOK")

    kontantstrom = aksje.cashflow
    resultat = aksje.income_stmt
    balanse = aksje.balance_sheet

    gjeld = siste_verdi(hent_rad(balanse, "Total Debt"))
    kontanter = siste_verdi(hent_rad(balanse, "Cash And Cash Equivalents"))

    return {
        "ticker": ticker,
        "navn": info.get("longName", ticker),
        "regnskapsvaluta": regnskapsvaluta,
        "handelsvaluta": handelsvaluta,
        "valutakurs": hent_valutakurs(regnskapsvaluta, handelsvaluta),
        "aksjekurs": float(aksje.history(period="5d")["Close"].iloc[-1]),
        "antall_aksjer": info.get("sharesOutstanding"),
        "beta": info.get("beta"),
        "fri_kontantstrom": hent_rad(kontantstrom, "Free Cash Flow"),
        "omsetning": hent_rad(resultat, "Total Revenue"),
        "netto_gjeld": gjeld - kontanter,
    }