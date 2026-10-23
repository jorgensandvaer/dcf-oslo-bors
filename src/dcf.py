"""DCF-modell: regner ut verdien av et selskap fra fremtidige kontantstrømmer."""


def egenkapitalkostnad(risikofri_rente, beta, markedsrisikopremie):
    """Avkastningskravet til eierne etter CAPM: rf + beta * MRP."""
    return risikofri_rente + beta * markedsrisikopremie


def wacc(egenkapitalverdi, gjeld, egenkapitalkostnad, gjeldskostnad, skattesats):
    """Vektet gjennomsnittlig kapitalkostnad (WACC).

    Gjeldskostnaden er etter skatt, fordi renter er fradragsberettiget.
    Negativ netto gjeld (netto kontanter) gir gjeldsvekt null.
    """
    gjeld = max(gjeld, 0.0)
    total = egenkapitalverdi + gjeld
    vekt_ek = egenkapitalverdi / total
    vekt_gjeld = gjeld / total
    return vekt_ek * egenkapitalkostnad + vekt_gjeld * gjeldskostnad * (1 - skattesats)


def fremskriv_kontantstrom(start, vekst, antall_ar):
    """Lager en liste med fremtidige kontantstrømmer som vokser med fast rate."""
    return [start * (1 + vekst) ** ar for ar in range(1, antall_ar + 1)]


def naverdi(kontantstrommer, diskonteringsrente):
    """Neddiskonterer kontantstrømmer for år 1, 2, 3 ... til dagens verdi."""
    return sum(
        kontantstrom / (1 + diskonteringsrente) ** ar
        for ar, kontantstrom in enumerate(kontantstrommer, start=1)
    )


def terminalverdi(siste_kontantstrom, diskonteringsrente, langsiktig_vekst):
    """Verdien av alle kontantstrømmer etter prognoseperioden (Gordons vekstmodell)."""
    if diskonteringsrente <= langsiktig_vekst:
        raise ValueError("Diskonteringsrenten må være høyere enn den langsiktige veksten.")
    return siste_kontantstrom * (1 + langsiktig_vekst) / (diskonteringsrente - langsiktig_vekst)


def verdsett(start_kontantstrom, vekst, antall_ar, diskonteringsrente,
             langsiktig_vekst, netto_gjeld, antall_aksjer, valutakurs=1.0):
    """Kjører hele DCF-beregningen og returnerer resultatene i en ordbok."""
    kontantstrommer = fremskriv_kontantstrom(start_kontantstrom, vekst, antall_ar)
    nv_kontantstrommer = naverdi(kontantstrommer, diskonteringsrente)

    tv = terminalverdi(kontantstrommer[-1], diskonteringsrente, langsiktig_vekst)
    nv_terminalverdi = tv / (1 + diskonteringsrente) ** antall_ar

    selskapsverdi = nv_kontantstrommer + nv_terminalverdi
    egenkapitalverdi = selskapsverdi - netto_gjeld
    verdi_per_aksje = egenkapitalverdi / antall_aksjer

    return {
        "kontantstrommer": kontantstrommer,
        "nv_kontantstrommer": nv_kontantstrommer,
        "nv_terminalverdi": nv_terminalverdi,
        "andel_terminalverdi": nv_terminalverdi / selskapsverdi,
        "selskapsverdi": selskapsverdi,
        "egenkapitalverdi": egenkapitalverdi,
        "verdi_per_aksje": verdi_per_aksje * valutakurs,
    }

def sensitivitet(diskonteringsrenter, langsiktige_vekstrater, **forutsetninger):
    """Lager en tabell med verdi per aksje for ulike kombinasjoner av WACC og vekst.

    Radene er diskonteringsrenter, kolonnene er langsiktig vekst.
    Kombinasjoner der renten ikke er høyere enn veksten, blir stående tomme.
    """
    import pandas as pd

    tabell = pd.DataFrame(index=diskonteringsrenter, columns=langsiktige_vekstrater, dtype=float)
    for rente in diskonteringsrenter:
        for vekst in langsiktige_vekstrater:
            if rente <= vekst:
                continue
            resultat = verdsett(diskonteringsrente=rente, langsiktig_vekst=vekst, **forutsetninger)
            tabell.loc[rente, vekst] = resultat["verdi_per_aksje"]
    return tabell