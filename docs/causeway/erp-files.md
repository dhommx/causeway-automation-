# Causeway: ERP upload files

Every condition the portal applies when it builds a file for PACT, with where it came from. When
someone asks "why is this here?", the answer should be on this page. Add to it whenever a condition
is added or changed, with the date and who asked for it.

Files are produced per tab of the Causeway Sales Reconciliation result. The download button for a
tab's file shows on that tab. Planned: a "Download all" button outside the tabs.

| Tab | File | Status |
|---|---|---|
| Credit Note (Variance) | `CreditNoteJV-.xlsx` | Done (29 Oct 2026) |
| Receipt (Cash) | `RECEIPTS.xlsx` (sheet `RECEIPTS`) | Done (29 Oct 2026) |
| Receipt (AFS) | waiting for the format | Planned |
| Receipt (PIE) | waiting for the format | Planned |
| Direct Sales Invoice | not yet | Later (user's decision, 29 Oct 2026) |
| Credit Note EVD + KFC | not yet | Later (user's decision, 29 Oct 2026) |

## Credit Note (Variance): `CreditNoteJV-.xlsx`

Code: `backend/app/workflows/finance/causeway_sales/variance_note.py` (`erp_rows`, `erp_file`).
Template: `backend/app/workflows/finance/causeway_sales/templates/CreditNoteJV-.xlsx`, taken from
the file the user downloaded from PACT on 29 Oct 2026. The sample rows were removed and one empty
styled row was kept. Changeable values are in the rule `variance_credit_note` (keys starting
`erp_`).

| Column | Value | Why |
|---|---|---|
| File name | `CreditNoteJV-.xlsx` | Same name as the PACT file (user, 29 Oct 2026). Each run has its own folder, so the same name never clashes. Rule `erp_file_name`. |
| Doc Date | The sales date of the run | The date the reconciliation was done for (user, 29 Oct 2026). Stored as a real date, shown `mm-dd-yy` like the template. |
| DocPrefix | `YQ-<yy>-<mm>` from the sales date, e.g. 21/10/2026 → `YQ-26-10` | As in PACT (user, 29 Oct 2026). Rule `erp_doc_prefix`. |
| Doc No | Empty, yellow | Typed in PACT by the accountant (user, 29 Oct 2026). |
| Account Code / Name, line 1 | `160700-1` / `CAUSEWAY`, credit = the whole variance | From the user's PACT file. On screen the line shows `CAUSEWAY` / `Causeway Cash Sales`, as the PACT entry screen shows it. Rules `erp_credit_account_code`, `erp_credit_account_name`. |
| Line 2 | `201002004001` / `Batelco marketing fund`, debit = its part | From the user's PACT file and screenshot. |
| Line 3 | `501002056` / `Business Promotion`, debit = its part | From the user's PACT screenshot (29 Oct 2026). |
| Zero lines | A debit line with 0.000 is left out of the file | The PACT file for an all-to-marketing-fund day has only 2 lines. The screen tab still shows all 3 lines. |
| Debit / Credit | Numbers, 3 decimals, accounting format; the unused side is left empty, not 0 | As in the template. |
| Terminal ID | Empty | Empty in the template. |
| Narration and Remarks | `Causeway Cash Sales Marketing fund against sales date dd/mm/yyyy` | From the user's PACT file. Used for every split, including Business Promotion, until told otherwise. Rule `erp_narration`. |
| Business Unit | `YQ` | From the template. Rule `erp_business_unit`. |

When the file is made:
- Only when the variance is above zero. With no variance there is no credit note and no file.
- Right after the run, with all of the variance on the Batelco marketing fund. Confirming or
  changing the split in the popup rebuilds the file. The earlier file is kept in the run's folder
  and linked to the run as "replaced", for audit.

## Receipt (Cash): `RECEIPTS.xlsx`

Code: `backend/app/workflows/finance/causeway_sales/receipts.py` (`cash_erp_rows`, `cash_erp_file`).
Template: `backend/app/workflows/finance/causeway_sales/templates/RECEIPTS.xlsx`, from the user's
PACT file "RECEIPTS -AUTOMATION.xlsx" (29 Oct 2026), sample row cleared. Changeable values are in
the rule `receipts` (keys starting `cash_erp_`).

| Column | Value | Why |
|---|---|---|
| File / sheet name | `RECEIPTS.xlsx`, sheet `RECEIPTS` | User, 29 Oct 2026: the PACT name without "-AUTOMATION"; sheet as in the template. Rule `cash_erp_file_name`. |
| Doc Date | The cash deposit date entered for the run | "The date registered for the cash" (user, 29 Oct 2026). |
| DocPrefix | `YQ-<yy>-<mm>-` from the cash deposit date, e.g. 25/10/2026 → `YQ-26-10-` | Same pattern as the credit note, with the trailing dash the receipts template has. The template's sample said `YQ-26-09-` for a 25/10/2026 date; month taken from the Doc Date until told otherwise. Rule `cash_erp_doc_prefix`. |
| Doc No | Empty | Typed in PACT by the accountant. |
| Business Unit | `YQ` | Template. |
| Cash/Bank GL Code / Name | `101001004021` / `AUB BHD Account 0016-525530-001` | Template: the bank account the cash is deposited into. |
| Account Code / Name | `101001001001` / `Cash in Hand - Bahraini Dinars` | Template. |
| Property, Unit, Terminal ID | `-` | Template. |
| Amount | The cash amount entered for the run | User, 29 Oct 2026. Stored exactly (3 decimals); the template's display format `#,##0.00` is kept. |
| Reference | `CASH DEPOSIT` | Template. |
| Description | `Causeway Cash sales dd/mm/yyyy` with the **sales** date | Template ("Causeway Cash sales 21/10/2026" next to Doc Date 25/10/2026). |
| CHEQUE DATE | Formula `=A<row>` | Template formula: the Doc Date. |
| CHEQUE NUMBER | Formula `=CONCATENATE(N," ",TEXT(O,"DD/MM/YYYY")," ",C)` | Template formula. It includes Doc No, so it completes when the accountant types Doc No in Excel. The file is marked to recalculate on open. |

When the file is made: every run with a cash amount above zero. No cash, no file.
