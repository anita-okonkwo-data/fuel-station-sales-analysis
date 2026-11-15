"""
Step 2: Clean the raw POS export and keep a log of every change.

Rule: nothing is silently dropped. Each fix is counted and written to cleaning_log.csv,
and rejected rows go to rejected_rows.csv so a manager can review them.
"""
import numpy as np
import pandas as pd

raw = pd.read_csv("raw_pos_transactions.csv", dtype=str)
log = []


def record(step, rows_affected, action):
    log.append({"step": step, "rows_affected": int(rows_affected), "action": action})


start = len(raw)
record("Raw rows loaded", start, "Starting point")

df = raw.copy()

# 1. Remove exact duplicate transactions (same txn_id sent twice by the terminal)
dup_mask = df.duplicated(subset="txn_id", keep="first")
record("Duplicate transaction IDs", dup_mask.sum(), "Removed, first copy kept")
df = df[~dup_mask].copy()

# 2. Standardise labels
product_map = {"pms": "PMS (Petrol)", "PMS (Petrol)": "PMS (Petrol)", "Diesel": "AGO (Diesel)",
               "AGO (Diesel)": "AGO (Diesel)", "LPG": "LPG (Cooking gas)", "LPG (Cooking gas)": "LPG (Cooking gas)"}
before = df["product"].copy()
df["product"] = df["product"].str.strip().replace(product_map)
record("Inconsistent product labels", (before != df["product"]).sum(), "Mapped to one standard name")

pay_map = {"pos": "POS card", "transfer": "Transfer", "cash": "Cash", "pos card": "POS card"}
before = df["payment_method"].copy()
df["payment_method"] = df["payment_method"].str.strip().str.lower().map(pay_map)
changed = ((before.fillna("") != df["payment_method"].fillna("")) & before.notna()).sum()
record("Inconsistent payment labels", changed, "Trimmed spaces and standardised case")

# 3. Fix data types
df["txn_time"] = pd.to_datetime(df["txn_time"], errors="coerce")
df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
text_amt = df["amount"].str.contains("₦", na=False)
record("Amount stored as text with ₦ symbol", text_amt.sum(), "Symbol and commas stripped, converted to number")
df["amount"] = pd.to_numeric(df["amount"].str.replace("₦", "", regex=False).str.replace(",", "", regex=False), errors="coerce")

# 4. Reject rows that cannot be trusted. Keep them for review.
reasons = pd.Series("", index=df.index)
reasons[df["station_id"].isna()] += "missing station; "
reasons[df["payment_method"].isna()] += "missing payment method; "
reasons[df["quantity"].isna()] += "missing quantity; "
reasons[df["quantity"] <= 0] += "zero or negative quantity; "
# Outlier rule: a single sale above 500 units (litres/kg/items) is not plausible at a retail station
reasons[df["quantity"] > 500] += "implausible quantity; "

rejected = df[reasons != ""].copy()
rejected["reject_reason"] = reasons[reasons != ""]
rejected.to_csv("rejected_rows.csv", index=False)
for r in ["missing station", "missing payment method", "missing quantity", "zero or negative quantity", "implausible quantity"]:
    record(f"Rejected: {r}", reasons.str.contains(r).sum(), "Moved to rejected_rows.csv for review")
df = df[reasons == ""].copy()

# 5. Recalculate amount so it always equals quantity x unit_price
df["amount"] = (df["quantity"] * df["unit_price"]).round(0)

# 6. Helpful columns for reporting
df["date"] = df["txn_time"].dt.date
df["month"] = df["txn_time"].dt.to_period("M").astype(str)
df["hour"] = df["txn_time"].dt.hour
df["weekday"] = df["txn_time"].dt.day_name()

df.to_csv("clean_pos_transactions.csv", index=False)
record("Clean rows kept", len(df), f"{len(df) / start:.1%} of raw rows")

pd.DataFrame(log).to_csv("cleaning_log.csv", index=False)
print(pd.DataFrame(log).to_string(index=False))
