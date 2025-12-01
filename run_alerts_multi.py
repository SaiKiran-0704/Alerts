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
    customer_param = request.args.get("customer")
    timeframe = request.args.get("timeframe")  # "24h", "7d", "30d"

    # If nothing is selected, show empty page with only form
    if not customer_param or not timeframe:
        return html_page.replace("{html_table}", "<p>Please select a customer and timeframe.</p>")

    customer_num = int(customer_param)
    customer = CUSTOMERS[customer_num]

    # Timeframe mapping
    now = int(time.time())

    if timeframe == "24h":
        start_ts = now - 24*3600
    elif timeframe == "7d":
        start_ts = now - 7*24*3600
    else:
        start_ts = now - 30*24*3600

    alerts = fetch_all_alerts_for_account(
        customer["api_key"], 
        customer["account_id"], 
        start_ts=start_ts,
        end_ts=now
    )

    html_table = analyze_alerts(alerts)
    html_page = f"""
    <html>
        <head>
            <title>Alerts Dashboard</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
        </head>
        <body style="padding: 20px;">
            <h1>Alerts for {customer['name']}</h1>
            <form method="get" class="mb-3">

                <!-- Customer dropdown -->
                <label class="form-label">Select Customer:</label>
                <select name="customer" class="form-select" required>
                    <option value="">-- Select a customer --</option>
                    {''.join([f'<option value="{k}" {"selected" if str(k)==request.args.get("customer") else ""}>{v["name"]}</option>' for k,v in CUSTOMERS.items()])}
                </select>

                <br>

                <!-- Timeframe dropdown -->
                <label class="form-label">Select Time Frame:</label>
                <select name="timeframe" class="form-select" required>
                    <option value="">-- Select timeframe --</option>
                    <option value="24h" {"selected" if request.args.get("timeframe")=="24h" else ""}>Last 24 hours</option>
                    <option value="7d" {"selected" if request.args.get("timeframe")=="7d" else ""}>Last 7 days</option>
                    <option value="30d" {"selected" if request.args.get("timeframe")=="30d" else ""}>Last 30 days</option>
                </select>
                <br>
                <button class="btn btn-primary" type="submit">Submit</button>
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