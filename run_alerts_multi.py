from flask import Flask, render_template_string, request
import pandas as pd
import requests
import time, datetime, ast
import os
app = Flask(__name__)

# ----------------------------
# Customer config (placeholder)
# ----------------------------
CUSTOMERS = {
    1: {"name": "tm_prod", "account_id": 4511194, "api_key": os.environ.get("TM_KEY")},
    2: {"name": "aha_prod", "account_id": 6591476, "api_key": os.environ.get("AHA_KEY")},
    3: {"name": "Univision", "account_id": 4511207, "api_key": os.environ.get("UNIVISION_KEY")},
    4: {"name": "CANELA", "account_id": 4355238, "api_key": os.environ.get("CANELA_KEY")},
    5: {"name": "GAME", "account_id": 4401497, "api_key": os.environ.get("GAME_KEY")},
    6: {"name": "AMD", "account_id": 3673752, "api_key": os.environ.get("AMD_KEY")},
    7: {"name": "PLIVE", "account_id": 3759602, "api_key": os.environ.get("PLIVE_KEY")},
    8: {"name": "CIGNAL", "account_id": 3504913, "api_key": os.environ.get("CIGNAL_KEY")},
}


BASE_URL = "https://api.newrelic.com/v2/alerts_violations.json"
NOW = int(time.time())
THIRTY_DAYS_AGO = NOW - (30 * 24 * 3600)

# ----------------------------
# Helpers (from your script)
# ----------------------------
def fetch_all_alerts_for_account(api_key, account_id, start_ts=THIRTY_DAYS_AGO, end_ts=NOW, page_limit=100):
    headers = {"Api-Key": api_key, "Accept": "application/json"}
    url = f"{BASE_URL}?start_time={start_ts}&end_time={end_ts}&limit={page_limit}"
    all_alerts = []
    while url:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"❌ HTTP {r.status_code} fetching {url}")
            break
        data = r.json()
        violations = data.get("violations", []) or []
        all_alerts.extend(violations)
        next_url = data.get("links", {}).get("next")
        url = next_url if next_url else None
    return all_alerts

def safe_extract_entity_name(x):
    if isinstance(x, dict):
        return x.get("name") or x.get("id") or "unknown"
    if isinstance(x, str) and x.startswith("{") and x.endswith("}"):
        try:
            d = ast.literal_eval(x)
            if isinstance(d, dict):
                return d.get("name") or d.get("id") or x
        except:
            return x
    return str(x)

def safe_to_datetime_unix(x):
    try:
        xi = int(float(x))
        if 1000000000 < xi < 2000000000:
            return pd.to_datetime(xi, unit="s", utc=True)
    except:
        pass
    return pd.NaT

def analyze_alerts(alerts):
    if not alerts:
        return "<p>No alerts found.</p>"
    df = pd.DataFrame(alerts)
    if "entity" in df.columns:
        df["entity_name"] = df["entity"].apply(safe_extract_entity_name)
    else:
        df["entity_name"] = "unknown"
    for col in ["opened_at", "closed_at"]:
        if col in df.columns:
            df[col] = df[col].apply(safe_to_datetime_unix)
    if {"opened_at", "closed_at"}.issubset(df.columns):
        df["duration_minutes"] = (df["closed_at"] - df["opened_at"]).dt.total_seconds() / 60.0
    grouped_condition = (
        df.groupby(["condition_name", "entity_name"], dropna=False)
        .size()
        .reset_index(name="Alert_Count")
        .sort_values(by="Alert_Count", ascending=False)
    )
    return grouped_condition.to_html(index=False, classes="table table-striped")

# ----------------------------
# Flask routes
# ----------------------------
@app.route("/", methods=["GET"])
def home():
    customer_num = int(request.args.get("customer", 1))
    customer = CUSTOMERS.get(customer_num, list(CUSTOMERS.values())[0])
    alerts = fetch_all_alerts_for_account(customer["api_key"], customer["account_id"])
    html_table = analyze_alerts(alerts)
    html_page = f"""
    <html>
        <head>
            <title>Alerts Dashboard</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
        </head>
        <body style="padding: 20px;">
            <h1>Alerts for {customer['name']}</h1>
            <form method="get">
                <label>Select Customer:</label>
                <select name="customer">
                    {''.join([f'<option value="{k}" {"selected" if k==customer_num else ""}>{v["name"]}</option>' for k,v in CUSTOMERS.items()])}
                </select>
                <button type="submit">View Alerts</button>
            </form>
            <hr/>
            {html_table}
        </body>
    </html>
    """
    return html_page

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # Use Render's PORT
    app.run(host="0.0.0.0", port=port)
