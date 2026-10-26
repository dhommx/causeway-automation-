"""Causeway daily cash sales: step 1, reconcile payments against Zoho."""
import os
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template, request

from readers import MILS, ReadError, read_afs, read_zoho_total

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


def money(value):
    return f"{value:,.3f}"


app.jinja_env.filters["money"] = money


def amount_field(name, label, errors):
    raw = (request.form.get(name) or "").strip()
    try:
        value = Decimal(raw.replace(",", "")).quantize(MILS)
    except InvalidOperation:
        errors.append(f"{label}: enter an amount, e.g. 100.500")
        return None
    if value < 0:
        errors.append(f"{label} cannot be negative.")
        return None
    return value


@app.get("/")
def index():
    return render_template("index.html", form={}, errors=[], result=None)


@app.post("/")
def calculate():
    errors = []
    form = request.form

    try:
        day = date.fromisoformat(form.get("date", ""))
    except ValueError:
        day = None
        errors.append("Choose the sales date.")

    cash = amount_field("cash", "Cash amount", errors)
    pie = amount_field("pie", "PIE (MSwipe) amount", errors)

    afs_file = request.files.get("afs_file")
    zoho_file = request.files.get("zoho_file")
    afs_password = form.get("afs_password", "")
    if not afs_file or not afs_file.filename:
        errors.append("Upload the AFS Excel file.")
    if not afs_password:
        errors.append("Enter the AFS Excel password.")
    if not zoho_file or not zoho_file.filename:
        errors.append("Upload the Zoho invoice Excel file.")

    afs = zoho = None
    if not errors:
        try:
            afs = read_afs(afs_file.read(), afs_password)
        except ReadError as e:
            errors.append(str(e))
        try:
            zoho = read_zoho_total(zoho_file.read(), day)
        except ReadError as e:
            errors.append(str(e))

    if errors:
        return render_template("index.html", form=form, errors=errors, result=None), 400

    warnings = []
    if afs["dates"] and afs["dates"] != [day]:
        shown = ", ".join(f"{d:%d/%m/%Y}" for d in afs["dates"])
        warnings.append(f"The AFS file has transactions dated {shown}, not {day:%d/%m/%Y}. Check that you uploaded the right day's report.")

    payments = cash + afs["tran_amt"] + pie
    fund = zoho["total"] - payments
    if fund < 0:
        warnings.append("Payments are more than the Zoho total. The marketing fund cannot be negative, so check the amounts before posting.")

    result = {
        "date": day,
        "cash": cash,
        "pie": pie,
        "afs": afs,
        "zoho": zoho,
        "payments": payments,
        "fund": fund,
        "warnings": warnings,
        "afs_file": afs_file.filename,
        "zoho_file": zoho_file.filename,
    }
    return render_template("index.html", form=form, errors=[], result=result)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)), debug=False)
