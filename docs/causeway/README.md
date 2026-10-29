# Causeway Sales Reconciliation: every case, check and rule

This is the one place that explains what the Causeway automation does, step by step, and why.
If you are asking "why does it do this?" or "why didn't the popup show?", the answer should be here.

- Column-by-column detail of the ERP upload files: [erp-files.md](erp-files.md).
- Code: `backend/app/workflows/finance/causeway_sales/` (`workflow.py` runs everything; the other
  files are named after their step).
- Changeable values (account codes, rates, names, item types) are **rules**: Rules tab in the portal,
  versioned. The defaults are in the code. Each section below names its rule.

**Keep this file up to date.** Any new condition, popup, calculation or fix is added here in the same
change, with the date and who asked for it (see the change log at the end).

---

## 1. Inputs

| Input | Required | Notes |
|---|---|---|
| AFS settlement report (Excel) | Yes | Password-protected. Its password is typed next to the file. |
| Zoho invoice export (Excel) | Yes | Zoho > Invoices > export. |
| Images | No | Screenshots to read amounts from. Shown only, never processed. Kept with the run. |
| AFS amount from the previous day (BHD) | No (0 if empty) | AFS transactions for this sales date that came in yesterday's report. Typed by hand for now. |
| Sales date | Yes | The day being reconciled. |
| AFS amount for the next day (BHD) | No | Filled in by the AFS check (section 2). Can be changed. |
| Cash amount (BHD) | Yes | From the email report. Cannot be negative. |
| Cash deposit date | Yes | The day the cash went to the bank: the sales date or later. An earlier date is refused. |
| PIE / MSwipe amount (BHD) | Yes | From the email image. Cannot be negative. |

Amounts are BHD with 3 decimals, rounded half-up, worked out as exact decimals (never floats).

## 2. Checks before Run (AFS file)

As soon as the AFS file **and its password** are in, the portal checks it:

1. **Totals check.** Each terminal's transactions (Tran Amt, Commission, VAT, Net) must add up to that
   terminal's Total row. Match: a green tick "Total matches: N transactions = X BHD". Mismatch: red
   message, **Run stays disabled**. The run itself also refuses a file that doesn't add up.
2. **Next-day transactions** (needs the sales date as well). Transactions dated **after** the sales
   date belong to the next day:
   - their total is written into "AFS amount for the next day";
   - a popup, **"AFS transactions for the next day"**, lists them (date, batch, terminal, amount) and
     says if they fall on more than one day.

### When the next-day popup shows, and when it doesn't

| Situation | Popup? | Why |
|---|---|---|
| AFS file + password + sales date are all in, and the file has transactions after the sales date | Yes | Order doesn't matter: date first or file first both work. |
| No transactions after the sales date | No | Nothing to show. The next-day field is filled with 0.000. |
| Password not typed (or wrong) | No | The file can't be opened, so it can't be checked. |
| **Page refreshed, "Keep your previous work" chosen** | No, until the password is typed again | Passwords are never saved (security). Retyping it brings the popup back. |
| Popup closed, same file and same date | No (shown once) | It opens once for what it shows. **Show transactions** (under the next-day field) opens it again. A different date or file shows it again. |

### Changed values
If the user changes a value the check filled in (for example the next-day amount), a warning shows under
the field, in the "Are these values correct?" check and in the result. The run is allowed; it is on the
user's responsibility.

## 3. Run

- **"Are these values correct?"**: before running, a popup lists every typed value. "Yes, run" or
  "Go back and edit".
- **Refresh safety**: the run screen's work is kept in the browser tab, so after a refresh the portal
  asks **"Keep your previous work?"**. Files and values come back, passwords don't (see section 2).

## 4. Calculations

**AFS for the sales date** = AFS file total − AFS for the next day + AFS from the previous day.
**Payments** = Cash + AFS for the sales date + PIE.
**Zoho total** = the Total of each Zoho invoice dated on the sales date, each invoice counted once (every
item line repeats its invoice's Total).
**Variance** = Zoho total − Payments.

Receipt (AFS) and its 2.2% commission still use the **full** AFS file total, not the adjusted one.

Errors that stop the run (shown as they are): no Zoho invoices for the date (the message gives the dates
the file covers); Zoho file missing "Invoice Date", "Invoice Number" or "Total"; AFS file that doesn't add
up; wrong AFS password.

Warnings (the run continues, shown in yellow on the result):
- the AFS file has transactions **before** the sales date (wrong day's report?);
- the next-day amount was changed from what the file shows;
- next-day transactions fall on more than one day;
- **variance is negative** (payments more than Zoho): check before posting. No variance credit note.
- AFS commission at 2.2% differs from the file's Commission + VAT.
- EVD item without a price at the end of its SKU (the Zoho Item Price is used instead), KFC item without a
  terminal number.

## 5. Item types (Zoho lines)

Rule `item_types`, first match wins, on the Item Name:
1. contains "KFC" → **KFC** (so "EVD - KFC 2" is KFC, not EVD)
2. contains "kunooz" → **Kunooz**
3. contains "EVD" → **EVD**
4. anything else → **Normal** product

## 6. Result tabs, in order

| # | Tab | What it shows | Upload file |
|---|---|---|---|
| 1 | Reconciliation | Cash, AFS (with next/previous-day adjustments), PIE, payments, Zoho total, variance | - |
| 2 | How it was worked out | The steps above with the actual numbers | - |
| 3 | AFS terminals | Per terminal: Tran Amt, Commission, VAT, Net | - |
| 4 | Zoho invoices | Invoice, status, total for the date | - |
| 5 | Direct Sales Invoice | Normal products by SKU; VANILASIM (EVD + Kunooz qty, price 0); 0108002 Kunooz commission (2 / 1.1 = 1.818 per unit); ESIM9.5 (Kunooz qty, price from ERP). Rule `direct_sales_invoice` | Later |
| 6-7 | Credit Note EVD + KFC, Credit Note (JV) | Only if the date has EVD/KFC lines. EVD = qty × the price at the end of the SKU; KFC qty is already the amount. Debit CAUSEWAY = total; credit the KFC terminal account. Rule `credit_note` | Later |
| 8 | Receipt (Cash) | CAUSEWAY = cash. Shows the cash deposit date in bold, highlighted if after the sales date | `RECEIPTS.xlsx` (if cash > 0) |
| 9 | Receipt (AFS) | CAUSEWAY = full AFS total, AFS = −2.2%, cheque "AFS <batch>" | Waiting for format |
| 10 | Receipt (PIE) | CAUSEWAY = PIE total, PAYME = −1.65%, cheque "MSWIPE dd/mm/yyyy" | Waiting for format |
| 11 | Credit Note (Variance) | Only if variance > 0. See section 7 | `CreditNoteJV-.xlsx` |

Rule `receipts` holds the receipt accounts and rates.

A tab's upload file is downloaded **from that tab** (button above the table), not from the main
downloads row. Planned: a "Download all" button outside the tabs.

## 7. Variance credit note and the split popup

Lines: 1 = credit CAUSEWAY (Causeway Cash Sales) with the whole variance; 2 = debit 201002004001 Batelco
marketing fund; 3 = debit 501002056 Business Promotion. All three always show on screen (0.000 if
unused) with a Total row. Rule `variance_credit_note`.

**Split popup ("Split the variance")**
- Opens by itself on the **Run tab** right after a run with a variance above zero. On the History tab it
  opens only from the button (both tabs stay loaded, and two popups at once would freeze the page).
- Variance shown at the top (amber). Buttons **All to Batelco marketing fund** / **All to Business
  Promotion**: both plain until clicked; the clicked one turns blue; typing an amount clears it.
- Two amount boxes. The **Total** box at the bottom is green when the two add up to the variance exactly,
  red when not, with "X BHD still to assign" or "X BHD more than the variance".
- **Confirm split** works only when the total matches to the fils. The server checks again.
- **Later** closes it. Until confirmed, all of the variance is on the marketing fund and the tab shows
  "Split not confirmed yet".
- After confirming: the button becomes **Change variance split**; the tab, the reconciliation workbook
  and `CreditNoteJV-.xlsx` are rebuilt. Earlier files stay in the run's folder, linked as "replaced".
  Every split is in the audit trail (`run.split`).

## 8. Output files

| File | When | Where to download |
|---|---|---|
| `causeway_reconciliation_<yyyymmdd>.xlsx` | Every run: one sheet per tab | Main downloads row |
| Zoho file (same name as uploaded) | Every run: the original sheet unchanged + a "Formatted" sheet with the agreed columns (rule `zoho_columns`) and an empty row between dates | Main downloads row |
| `RECEIPTS.xlsx` | Cash > 0 | Receipt (Cash) tab |
| `CreditNoteJV-.xlsx` | Variance > 0; rebuilt on split | Credit Note (Variance) tab |

Each run is saved in `Data/<date>/Causeway Sales Reconciliation - <time>/` with `input/` (copies of the
uploads + the typed values), `output/` and `run.json` (everything an auditor needs).

## 9. Where the two portal addresses differ

- **http://localhost:3500**: the development copy, always the latest code.
- **http://localhost:3501**: the Docker copy, frozen at its last build. It only gets changes after
  `docker compose up -d --build`.
- Old runs keep the tables they were made with. Changes to tabs or files show on **new** runs.

## 10. Open points

- Narration of the variance credit note when Business Promotion is used (same text for now).
- Line 1 code on screen (`CAUSEWAY`) vs in the upload file (`160700-1`).
- RECEIPTS DocPrefix month: taken from the Doc Date (`YQ-26-10-`); the sample showed `-09-`.
- RECEIPTS amount display: 2 decimals as in the template (value stored with 3).
- Formats and names for the Receipt (AFS) and Receipt (PIE) upload files.
- Next-day popup after a refresh: maybe add a "type the password again" hint.

## Change log

| Date | Change | Asked by |
|---|---|---|
| 29 Oct 2026 | AFS totals check, next-day / previous-day calibration and popup, cash deposit date | User |
| 29 Oct 2026 | Variance credit note (3 lines), split popup, last tab after Receipt (PIE) | User |
| 29 Oct 2026 | Split popup: blue selected button, amber variance, green Total box | User |
| 29 Oct 2026 | `CreditNoteJV-.xlsx` upload file on the Credit Note (Variance) tab | User |
| 29 Oct 2026 | `RECEIPTS.xlsx` upload file on the Receipt (Cash) tab | User |
| 29 Oct 2026 | Fix: split popup opened on both Run and History tabs and froze the page | Found in testing |
| 29 Oct 2026 | This document | User |
