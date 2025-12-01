from flask import Flask, render_template, request
from run_alerts_multi import CUSTOMERS, fetch_all_alerts_for_account, analyze_alerts_for_web
import pandas as pd

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    selected_customer = None
    table_html = None

    if request.method == "POST":
        customer_id = int(request.form.get("customer"))
        if customer_id in CUSTOMERS:
            customer = CUSTOMERS[customer_id]
            selected_customer = customer["name"]
            # Fetch alerts
            alerts = fetch_all_alerts_for_account(customer["api_key"], customer["account_id"])
            # Convert alerts to HTML table
            table_html = analyze_alerts_for_web(alerts)

    return render_template("index.html",
                           customers=CUSTOMERS,
                           selected_customer=selected_customer,
                           table_html=table_html)

if __name__ == "__main__":
    app.run(debug=True)
