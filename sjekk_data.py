from src.data import hent_selskap

selskap = hent_selskap("EQNR.OL")

for navn, verdi in selskap.items():
    print(f"{navn}: {verdi}")
    print()