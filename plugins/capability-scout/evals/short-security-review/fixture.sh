#!/bin/bash
cat > app.py <<'PY'
import sqlite3, subprocess
from flask import Flask, request
app = Flask(__name__)
API_KEY = "hardcoded-demo-key-not-real"
@app.route("/orders")
def orders():
    c = request.args.get("customer")
    return {"rows": sqlite3.connect("shop.db").execute(f"SELECT * FROM orders WHERE customer = '{c}'").fetchall()}
@app.route("/export")
def export():
    return subprocess.check_output(f"python export.py --format {request.args.get('format')}", shell=True)
PY
