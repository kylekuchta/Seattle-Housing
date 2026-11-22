# Seattle Housing Market Monitor

A simple Streamlit web app that monitors the Seattle housing market using public data from Zillow Research, Redfin, and FRED. Includes buy-timing signals and a basic listing evaluator.

## Features (MVP)
- Seattle metro overview (ZHVI, months of supply, mortgage rate)
- Optional ZIP-level drill-down
- Simple buy-timing notes (months of supply, price momentum, rate trends)
- Listing evaluator (price vs local ZHVI + estimated payment)
- Historical charts
- Optional macro panel (requires free FRED API key)

## Deploy to the web (recommended)
1. Create a new **public** GitHub repository.
2. Upload all files from this folder (`app.py`, `data.py`, `signals.py`, `requirements.txt`, and this README).
3. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
4. Click **New app** → select your repo → main branch → `app.py` as the main file → Deploy.
5. (Optional) In the Streamlit Cloud app settings, add a secret named `FRED_API_KEY` if you want macros. The app also accepts the key in the sidebar for testing.

Your app will be live at `https://<your-app-name>.streamlit.app`.

## Run locally (optional)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## FRED API Key
Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html  
Enter it in the sidebar, or set it as a Streamlit secret for the cloud version.

## Notes
- Data is cached for 6–12 hours. Click the browser refresh or wait for the cache to expire to pull newer files.
- Large ZIP files may take a few seconds on first load.
- This is a monitoring tool, not financial advice.
- Attribute Zillow data when sharing.
