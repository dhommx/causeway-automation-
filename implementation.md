# Implementation Plan: PIE Automation Portal

Each phase below says what it delivers, what it needs before it can start, and how we know it is done. The steps are in plain language; the technical detail lives in `guide.md` and the code.

Status key: **Done**, **Next**, **Planned**.

---

## Phase 1: Foundation and portal shell (Done, 26 Oct 2026)

**Goal:** a working portal that every future automation plugs into, with no business rules yet.

**Delivered**

1. Project set up in one folder with a backend, a frontend, a database and a background worker, all started with one Docker Compose command or run separately for development.
2. Home screen for the Finance department with four boxes, one per automation. Causeway Sales Reconciliation can be opened; the other three are blurred and marked "Coming soon".
3. An automation page with three tabs:
   - **Run**: upload one or more Excel/CSV files and reference images, with a notice showing how many files were added and their formats. Preview any sheet in a spreadsheet grid (first 1,000 rows, with the full row count), fill in manual entries when the automation has any, start the run, see the result and download the output.
   - **History**: every past run with its date, status, files, rule version and duration. Opening a run shows its result and an audit record: who, when, input and output files with their fingerprints, manual entries, the audit trail and the processing log.
   - **Rules**: the automation's current rules, a list of all earlier versions, and saving changes as a new version with a note.
4. Static screens: the page itself never scrolls; only the boxes inside it do. Checked on desktop and phone sizes.
5. Images (screenshots of amounts, for example) can be uploaded and viewed on screen, fitted to the panel or at actual size. They are kept with the run for audit and never processed.
6. The plug-in system: an automation is one file that declares its inputs, manual fields and default rules, and holds its own processing. The portal finds it automatically.
7. Shared tools every automation will use: reading any Excel/CSV including password-protected files, writing new Excel files, editing a copy of an existing workbook, exact money arithmetic with 3-decimal BHD rounding, and a condition engine for filters and labels (equals, greater/less than, between, one of, contains, starts/ends with, empty, and all/any/not groups).
8. Safe storage: files are kept once under a fingerprint and never overwritten; rule changes always create a new version; the audit log is append-only.
9. Background processing: runs go into a queue and a worker processes them, so large files don't freeze the screen. The same queue will handle scheduled runs later.
10. Groundwork for outside systems: a standard way to add data sources and destinations, and a place to store their credentials encrypted.
11. A public, versioned API (`/api/v1`) with interactive docs, used by the screens today and by other systems later.
12. Automated tests for the shared tools and the full upload → run → download → audit path, plus a check of the full Docker setup.
13. Documentation: `guide.md`, `CLAUDE.md` and this plan.

**Until Phase 2 started,** running Causeway Sales Reconciliation copied the input to the output unchanged. It now does the reconciliation (Phase 2, step 4).

---

## Phase 2: Causeway Sales Reconciliation logic (In progress)

**Goal:** cut the daily Causeway posting from about 15 minutes to 5.

**Needs before starting**

- Instructions from the user on the steps, given one at a time (the process notes in `neasi_organised.txt` are the starting point).
- One complete day of real or dummy data: the Zoho export plus the matching Cash, AFS and PIE amounts and the ERP entries the accountant made for that day.
- Answers to the open points in the notes: the AFS commission rate (answered by the AFS report: 2% commission plus 10% VAT on it, 2.2% in all), where the eSIM price comes from, VAT on the eSIM line, and whether cash is posted the next day.

**Steps**

1. Declare the inputs: the Zoho invoice export as the file, and Cash, AFS and PIE amounts as manual entries. **Done:** the AFS amount is read from the password-protected AFS settlement report (its Total row) instead of being typed; Cash, PIE and the sales date are typed.
2. Clean the Zoho file: keep the agreed columns, drop the rest, keep the original sheet and add the cleaned one, and separate the dates. **Done:** each run gives back the Zoho file under its own name, with the original sheet as it was plus a new "Formatted" sheet holding only Invoice Date, Invoice Number, Customer Name, Company Name, Total, Item Name, Quantity, Item Price, SKU and Sales Person (rule `zoho_columns`), with an empty row between dates. The stored upload itself is never changed.
3. Classify each line (normal product, EVD, Kunooz, KFC) with conditions stored as rules, so Finance can adjust them. **Done:** rule `item_types` (KFC, then Kunooz, then EVD by Item Name; anything else is Normal).
4. Reconcile: sum of payments against the Zoho total, and the difference (the Batelco marketing fund). **Done:** marketing fund = Zoho total - (Cash + AFS + PIE); the worked example for 18/10/2026 gives 43.993.
5. Build every ERP entry the accountant types: Direct Sales Invoice, the EVD/KFC credit note, the cash receipt, the two bank receipts with their commissions, and the marketing fund credit note. Check that the sales side equals the Zoho total.
   - **4a Direct Sales Invoice: Done.** Result tab "Direct Sales Invoice": normal products by SKU, VANILASIM (EVD + Kunooz quantities, no KFC, price 0), 0108002 Kunooz commission (2 / 1.1 = 1.818 per unit) and ESIM9.5 (Kunooz quantity, price "From ERP"), with the Zoho items and SKUs behind each line for reference. Codes and rates in rule `direct_sales_invoice`. Matches page 3 for 03/10/2026.
   - **4b Credit Note EVD + KFC: Done.** Tab "Credit Note EVD + KFC" shows the calculation (EVD = quantity x the price at the end of the SKU; KFC quantity is already the amount); tab "Credit Note (JV)" shows debit CAUSEWAY = the total and the credit line for the KFC terminal account (from the Zoho item), with no amount. Accounts in rule `credit_note`. Matches page 4: 158.000 for 03/10/2026.
   - **5a-5c Receipts: Done.** Tabs "Receipt (Cash)" (CAUSEWAY = cash), "Receipt (AFS)" (CAUSEWAY = AFS total, AFS = -2.2%, cheque "AFS <batch>") and "Receipt (PIE)" (CAUSEWAY = PIE total, PAYME = -1.65%, cheque "MSWIPE DD/MM/YYYY"). A warning shows if 2.2% differs from the AFS file's Commission + VAT. Accounts and rates in rule `receipts`. Matches page 5 (88.998, 211.452).
   - **6 Credit Note, Batelco marketing fund: Next** (page 6: credit CAUSEWAY, debit 201002004001 with the difference).
   - **Check, sales side = Zoho total: Next.** Needs the ESIM9.5 price (see open points).
6. Show all of this on screen in the order it is typed into PACT, and produce the Excel output in the agreed format.
7. Store rates, account codes and product-code mappings as rules, starting from the confirmed values. **Mostly done:** rules `zoho_columns`, `item_types`, `direct_sales_invoice`, `credit_note` and `receipts` hold them; values still to be confirmed are listed under open points.
8. Test against the worked example so every total matches to the fils. **Done for pages 2-5:** automated tests check the cleaned Zoho sheet, the Direct Sales Invoice, the credit note and the receipts against the procedure examples (37 tests).
9. Walk through it with the accountant on a real day, then compare a week of portal results with their manual results before switching over.

**Screen changes made during Phase 2**

- Images: zoom with the mouse wheel (towards the cursor), drag to move, double-click to zoom in or back to fit, and - / % / + / Fit buttons and keys. Still view-only, never processed.
- Preview and result: an **Expand** button hides the inputs so the panel uses the full width. Columns of sheets without a header row show Excel letters (A, B, C...), so wide sheets like the AFS report fit and its Total row is visible. Hovering a cell shows its full text.
- Result tiles (Zoho total, Cash + AFS + PIE, Marketing fund) are larger.
- "From ERP" cells are greyed and can't be selected or copied, so they aren't pasted into the ERP by mistake.
- After a page refresh the run screen asks "Keep your previous work?": keep brings back the files, entries and last result (file passwords are never saved and are typed again); start fresh clears them. Works within the same browser tab.
- Pressing Run automation first shows the typed values (sales date, cash, PIE) for confirmation; "Go back and edit" cancels.

**Open points to confirm with Finance**

- Item prices and where they come from: ESIM9.5 at 7.500 (not in Zoho), whether the Zoho Item Price always equals the ERP price for normal products, whether the EVD price is always the number at the end of the SKU, and whether the Kunooz commission of 2 is fixed. A message for the accountant was drafted on 26 Oct 2026.
- The credit account name for KFC 1 (terminal 056194010436028); only KFC 2 (CAUSEWAY CASH SALES 2) is known.
- How "eSIM 12 (kunooz)" is posted; today it counts under ESIM9.5.
- Whether a day with both KFC terminals gives two credit lines.
- Cash receipt date (posted the next day?) and VAT on ESIM9.5, from the notes.

**Done when** the accountant completes a day's posting from the portal in 5 minutes or less and a week of results matches the manual figures exactly.

---

## Phase 3: Login, roles and access (Planned)

**Goal:** know who did what, and limit who can see or change what.

**Steps**

1. User accounts with secure passwords, plus sign-in and sign-out. Session timeout follows the Compliance Portal's lessons (warn before expiry, allow extending).
2. Roles: Administrator (users, rules, settings), Operator (run automations, view history), Viewer (view results only).
3. Department access: a user sees only their department's automations.
4. Replace "anonymous" in all new audit records with the real user. Older records keep "anonymous".
5. API tokens for other systems calling the portal, each with a name, an owner and an expiry, and revocable.
6. An admin screen for users, roles and tokens, and an audit log viewer with filters.
7. Optional later: sign-in with the company directory (Active Directory/LDAP) instead of local passwords.

**Done when** every action in the audit log has a named user or token, and a Viewer cannot run or change anything.

---

## Phase 4: The other Finance automations (Planned)

Each one follows the same path as Phase 2: instructions from the user, sample data, build, test against a worked example, trial with the accountant, switch over.

1. **Start Back Invoicing**: compare each salesman's cash sales in Focus with deposits in IBL, show differences and flag short or missing deposits. Starts with uploaded exports from both systems.
2. **Cash Collection**: group Benefit QR transactions and cash by salesman, calculate the totals, and flag duplicate, missing or unlinked transaction IDs.
3. **Threshold Alert System**: users define thresholds and conditions once and apply them to any file in one click. This adds a **condition builder screen** (choose a column, an operator and a value; combine with AND/OR) on top of the existing condition engine, plus alert highlighting, filtering and export.

As each one goes live, its box on the home screen stops being blurred.

---

## Phase 5: Integrations and scheduled runs (Planned)

**Goal:** the "full automation" option in each proposal: the portal fetches and delivers data by itself.

**Needs:** approved access and documentation for each outside system.

**Steps**

1. A connections screen for administrators to add an outside system, enter its credentials (stored encrypted) and test the connection.
2. Sources, in order of value:
   - The email inbox that receives the AFS file, opening the password-protected attachment.
   - Zoho (invoice export by date).
   - PIE POS / MSwipe (daily sales).
   - Benefit (QR transactions).
   - Focus and IBL (sales and deposits).
   - A shared network folder (any file dropped there).
3. Destinations: a shared folder, email with the output attached, a PACT import file or the PACT API if one is approved, and a webhook to notify other systems.
4. Scheduled runs: for example, every working day at 8:00, fetch yesterday's files, run the automation and email the accountant the result for review. Retries when an outside system is down, and an alert when a run fails.
5. Each automation can still be run by hand with uploads, as a fallback.

**Done when** at least one automation runs every morning without anyone uploading files, and its results match the manual runs.

---

## Phase 6: Reports and notifications (Planned)

1. Monthly consolidated report for each automation, built from its run history (Proposal 01 asks for this).
2. A summary dashboard per department: runs per day, failures, time saved compared with the manual process.
3. Notifications by email (and later Teams) when a run finishes, fails or finds differences that need review.
4. Export of the audit log for a date range, for auditors.

---

## Phase 7: Server deployment and hardening (Planned)

1. Install on the local server with Docker Compose. Set real passwords and the encryption key, and turn on HTTPS with an internal certificate.
2. Nightly backups of the database and the file storage, and one tested restore.
3. Retention rules: how long input and output files and audit records are kept (Finance and Compliance to decide).
4. Monitoring: health check, disk space, failed runs, a worker that has stopped.
5. Performance check with the largest real files expected (the target is a preview in a few seconds and a run in under a minute for 100k rows).
6. A short user guide and a training session for the Finance team.

---

## Phase 8: Other departments (Planned)

Add a department to the portal's list and give it its own home section. Its automations are built the same way as Finance's, reusing the shared tools, connectors, rules, history and audit. Once Phase 3 is in place, access is controlled per department.
