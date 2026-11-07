import sqlite3
import subprocess
from flask import Flask, request

app = Flask(__name__)
DB = "shop.db"
API_KEY = "hardcoded-demo-key-not-real"


def parse_amount(text):
    """Parse a money string like '$1,234.50' into integer cents."""
    text = text.strip().replace("$", "").replace(",", "")
    if "." in text:
        dollars, cents = text.split(".")
        return int(dollars) * 100 + int(cents)
    return int(text) * 100


@app.route("/orders")
def orders():
    customer = request.args.get("customer")
    conn = sqlite3.connect(DB)
    rows = conn.execute(f"SELECT * FROM orders WHERE customer = '{customer}'").fetchall()
    return {"orders": rows}


@app.route("/export")
def export():
    fmt = request.args.get("format", "csv")
    out = subprocess.check_output(f"python export.py --format {fmt}", shell=True)
    return out


@app.route("/refund", methods=["POST"])
def refund():
    amount = parse_amount(request.form["amount"])
    return {"refunded_cents": amount}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
