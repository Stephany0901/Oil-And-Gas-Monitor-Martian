# Oil & Gas Equity Monitor — Streamlit app

A live dashboard over 385 oil & gas names: price screen, peer valuation, historical
valuation, technical analysis (candles + MA/EMA/RSI/MACD/OBV/support-resistance),
crude/nat-gas correlation with a 5-year price-ratio, news, sector return bars, and a
recommendation screen. Data from Financial Modeling Prep (FMP) `/api/v3` (Starter-friendly).

## Run locally
```
pip install -r requirements.txt
# option A: put your key in .streamlit/secrets.toml  (FMP_API_KEY = "xxxx")
# option B: just run and paste the key in the sidebar
streamlit run app.py
```

## Deploy to Streamlit Community Cloud (free, gives a *.streamlit.app URL)
1. Push this `streamlit-app/` folder to a **public GitHub repo** (files: app.py, universe.py,
   requirements.txt, .streamlit/config.toml).  Do NOT commit your real secrets.toml.
2. Go to https://share.streamlit.io → **New app** → pick your repo/branch and set
   **Main file path** = `app.py` (or `streamlit-app/app.py` if the folder is nested).
3. Click **Advanced settings → Secrets** and add:
   ```
   FMP_API_KEY = "your_fmp_api_key_here"
   ```
4. **Deploy**. You'll get a URL like `https://your-app-name.streamlit.app`.

## Notes
- Runs server-side, so there are no browser CORS issues.
- Uses your FMP key; the same Starter-plan limits apply (per-symbol commodity *history*
  is gated, so the crack spread is shown as a live spot value only).
- Educational tool, not investment advice.
