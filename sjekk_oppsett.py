import yfinance as yf

eqnr = yf.Ticker("EQNR.OL")

print("=== Sluttkurser siste 5 dager ===")
print(eqnr.history(period="5d")[["Close"]])

print("\n=== Kontantstrømoppstilling (utdrag) ===")
print(eqnr.cashflow.head())
