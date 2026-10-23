import matplotlib.pyplot as plt
import numpy as np

from src.data import hent_selskap
from src.dcf import egenkapitalkostnad, wacc, sensitivitet

# ---------- FORUTSETNINGER (samme som i sjekk_dcf.py) ----------
TICKER = "EQNR.OL"
RISIKOFRI_RENTE = 0.04
MARKEDSRISIKOPREMIE = 0.05
BETA = 1.0
GJELDSKOSTNAD = 0.05
SKATTESATS = 0.22
VEKST = 0.02
ANTALL_AR = 5
# ---------------------------------------------------------------

selskap = hent_selskap(TICKER)
markedsverdi = selskap["aksjekurs"] / selskap["valutakurs"] * selskap["antall_aksjer"]
ke = egenkapitalkostnad(RISIKOFRI_RENTE, BETA, MARKEDSRISIKOPREMIE)
basis_wacc = wacc(markedsverdi, selskap["netto_gjeld"], ke, GJELDSKOSTNAD, SKATTESATS)

# Fem WACC-verdier rundt basisverdien, og fem vekstrater
renter = np.round(basis_wacc + np.array([-0.02, -0.01, 0.0, 0.01, 0.02]), 4)
vekstrater = [0.0, 0.005, 0.01, 0.015, 0.02]

tabell = sensitivitet(
    renter,
    vekstrater,
    start_kontantstrom=selskap["fri_kontantstrom"].iloc[-3:].mean(),
    vekst=VEKST,
    antall_ar=ANTALL_AR,
    netto_gjeld=selskap["netto_gjeld"],
    antall_aksjer=selskap["antall_aksjer"],
    valutakurs=selskap["valutakurs"],
)

# Penere etiketter: prosent i stedet for desimaltall
visning = tabell.copy()
visning.index = [f"{r:.1%}" for r in tabell.index]
visning.columns = [f"{g:.1%}" for g in tabell.columns]

print(f"Verdi per aksje (NOK) - {selskap['navn']}, snitt-FCF siste 3 år")
print(f"Rader: WACC | Kolonner: langsiktig vekst | Kurs i dag: {selskap['aksjekurs']:.2f} NOK\n")
print(visning.round(0))

# ---------- Varmekart ----------
kurs = selskap["aksjekurs"]
fig, ax = plt.subplots(figsize=(7, 5))
bilde = ax.imshow(tabell.values / kurs - 1, cmap="RdYlGn", vmin=-0.5, vmax=0.5)

ax.set_xticks(range(len(visning.columns)), visning.columns)
ax.set_yticks(range(len(visning.index)), visning.index)
ax.set_xlabel("Langsiktig vekst")
ax.set_ylabel("WACC")
ax.set_title(f"{selskap['navn']}: verdi per aksje (NOK) mot kurs {kurs:.0f} kr")

for i in range(tabell.shape[0]):
    for j in range(tabell.shape[1]):
        ax.text(j, i, f"{tabell.values[i, j]:.0f}", ha="center", va="center")

fig.colorbar(bilde, ax=ax, label="Oppside/nedside mot dagens kurs")
fig.tight_layout()
fig.savefig("sensitivitet.png", dpi=150)
print("\nVarmekart lagret som sensitivitet.png")