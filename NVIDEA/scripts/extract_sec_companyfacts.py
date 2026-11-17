#!/usr/bin/env python3
"""Extract auditable NVIDIA financial facts from SEC Companyfacts XBRL.

The script deliberately stages reported facts only. It does not fabricate missing
quarters, infer fiscal period ends, or mix GAAP and non-GAAP disclosures.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CIK = "0001045810"
ENTITY = "NVIDIA Corporation"
COMPANYFACTS_URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"

# concept: (statement, canonical id, canonical label, accepted units, duration/instant)
TAGS = {
    "Revenues": ("income_statement", "revenue", "Revenue", {"USD"}, "duration"),
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("income_statement", "revenue", "Revenue", {"USD"}, "duration"),
    "CostOfRevenue": ("income_statement", "cogs", "Cost of revenue", {"USD"}, "duration"),
    "CostOfGoodsAndServicesSold": ("income_statement", "cogs", "Cost of revenue", {"USD"}, "duration"),
    "GrossProfit": ("income_statement", "gross_profit", "Gross profit", {"USD"}, "duration"),
    "ResearchAndDevelopmentExpense": ("income_statement", "research_development", "Research and development", {"USD"}, "duration"),
    "SellingGeneralAndAdministrativeExpense": ("income_statement", "selling_general_admin", "Selling, general and administrative", {"USD"}, "duration"),
    "OperatingExpenses": ("income_statement", "opex_total", "Total operating expenses", {"USD"}, "duration"),
    "OperatingIncomeLoss": ("income_statement", "operating_income", "Operating income", {"USD"}, "duration"),
    "NonoperatingIncomeExpense": ("income_statement", "non_operating_income_expense", "Non-operating income / expense", {"USD"}, "duration"),
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": ("income_statement", "pretax_income", "Income before income taxes", {"USD"}, "duration"),
    "IncomeTaxExpenseBenefit": ("income_statement", "tax_expense", "Income tax expense", {"USD"}, "duration"),
    "NetIncomeLoss": ("income_statement", "net_income", "Net income", {"USD"}, "duration"),
    "EarningsPerShareBasic": ("income_statement", "eps_basic", "Basic EPS", {"USD/shares"}, "duration"),
    "EarningsPerShareDiluted": ("income_statement", "eps_diluted", "Diluted EPS", {"USD/shares"}, "duration"),
    "WeightedAverageNumberOfSharesOutstandingBasic": ("share_count", "shares_basic", "Weighted-average basic shares", {"shares"}, "duration"),
    "WeightedAverageNumberOfDilutedSharesOutstanding": ("share_count", "shares_diluted", "Weighted-average diluted shares", {"shares"}, "duration"),
    "CashAndCashEquivalentsAtCarryingValue": ("balance_sheet", "cash_equivalents", "Cash and cash equivalents", {"USD"}, "instant"),
    "ShortTermInvestments": ("balance_sheet", "short_term_investments", "Short-term investments", {"USD"}, "instant"),
    "MarketableSecuritiesCurrent": ("balance_sheet", "marketable_securities_current", "Marketable securities, current", {"USD"}, "instant"),
    "AccountsReceivableNetCurrent": ("balance_sheet", "accounts_receivable", "Accounts receivable, net", {"USD"}, "instant"),
    "InventoryNet": ("balance_sheet", "inventory", "Inventory", {"USD"}, "instant"),
    "OtherCurrentAssets": ("balance_sheet", "other_current_assets", "Other current assets", {"USD"}, "instant"),
    "AssetsCurrent": ("balance_sheet", "total_current_assets", "Total current assets", {"USD"}, "instant"),
    "PropertyPlantAndEquipmentNet": ("balance_sheet", "ppne_net", "Property and equipment, net", {"USD"}, "instant"),
    "Goodwill": ("balance_sheet", "goodwill", "Goodwill", {"USD"}, "instant"),
    "Assets": ("balance_sheet", "total_assets", "Total assets", {"USD"}, "instant"),
    "AccountsPayableCurrent": ("balance_sheet", "accounts_payable", "Accounts payable", {"USD"}, "instant"),
    "AccruedLiabilitiesCurrent": ("balance_sheet", "accrued_liabilities", "Accrued liabilities, current", {"USD"}, "instant"),
    "LiabilitiesCurrent": ("balance_sheet", "total_current_liabilities", "Total current liabilities", {"USD"}, "instant"),
    "LongTermDebtCurrent": ("balance_sheet", "short_term_debt", "Short-term debt", {"USD"}, "instant"),
    "LongTermDebtNoncurrent": ("balance_sheet", "long_term_debt", "Long-term debt", {"USD"}, "instant"),
    "LongTermDebt": ("balance_sheet", "long_term_debt_total", "Long-term debt", {"USD"}, "instant"),
    "Liabilities": ("balance_sheet", "total_liabilities", "Total liabilities", {"USD"}, "instant"),
    "StockholdersEquity": ("balance_sheet", "total_equity", "Total shareholders' equity", {"USD"}, "instant"),
    "LiabilitiesAndStockholdersEquity": ("balance_sheet", "liabilities_equity", "Total liabilities and equity", {"USD"}, "instant"),
    "NetCashProvidedByUsedInOperatingActivities": ("cash_flow", "cfo", "Cash flow from operations", {"USD"}, "duration"),
    "DepreciationDepletionAndAmortization": ("cash_flow", "depreciation_amortization_cf", "Depreciation and amortization", {"USD"}, "duration"),
    "ShareBasedCompensation": ("cash_flow", "stock_based_comp_cf", "Stock-based compensation", {"USD"}, "duration"),
    "PaymentsToAcquirePropertyPlantAndEquipment": ("cash_flow", "capex", "Capital expenditures", {"USD"}, "duration"),
    "PaymentsForProceedsFromOtherInvestingActivities": ("cash_flow", "other_investing_cash_flow", "Other investing cash flow", {"USD"}, "duration"),
    "NetCashProvidedByUsedInInvestingActivities": ("cash_flow", "cfi", "Cash flow from investing", {"USD"}, "duration"),
    "PaymentsOfDividends": ("cash_flow", "dividends", "Dividends paid", {"USD"}, "duration"),
    "PaymentsForRepurchaseOfCommonStock": ("cash_flow", "share_repurchases", "Share repurchases", {"USD"}, "duration"),
    "NetCashProvidedByUsedInFinancingActivities": ("cash_flow", "cff", "Cash flow from financing", {"USD"}, "duration"),
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect": ("cash_flow", "net_change_cash", "Net change in cash", {"USD"}, "duration"),
}

LONG_COLUMNS = [
    "entity","source_id","statement","line_item_original","line_item_standard","line_item_id",
    "period_end","period_label","period_type","currency","units","source_value",
    "normalized_value","normalization_method","source_location","evidence_label","confidence",
    "normalization_note",
]
SOURCE_COLUMNS = [
    "source_id","source_name","source_type","owner_or_provider","period_covered","as_of_date",
    "retrieved_at","file_tab_page_url_or_location","source_rank","freshness_status","notes",
]
ISSUE_COLUMNS = ["severity","issue_type","source_id","concept","period_end","description","recommended_action"]
QA_COLUMNS = ["flag_id","severity","entity","period","area","issue","impact","recommended_fix","source_id","status"]
CHECK_COLUMNS = ["check_id","area","period","test","expected_value","observed_value","variance","result","source_id","notes"]

def fetch_companyfacts(input_json: Path | None) -> dict:
    if input_json:
        return json.loads(input_json.read_text(encoding="utf-8"))
    contact_email = os.getenv("SEC_CONTACT_EMAIL", "").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact_email):
        raise RuntimeError(
            "SEC_CONTACT_EMAIL is missing or invalid. Configure the repository Actions variable "
            "SEC_CONTACT_EMAIL with a monitored contact email; SEC requires a declared company/app "
            "and contact email in the User-Agent header."
        )
    user_agent = f"EMPRESAS-AMERICANAS NVIDEA research {contact_email}"
    req = urllib.request.Request(
        COMPANYFACTS_URL,
        headers={"User-Agent": user_agent, "Accept-Encoding": "identity", "Host": "data.sec.gov"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))

def fiscal_label(end: str, fy: object, fp: object) -> str:
    return f"FY{fy}-{fp}" if fy and fp else end

def duration_bucket(start: str, end: str) -> tuple[str, str] | None:
    try:
        d0 = datetime.strptime(start, "%Y-%m-%d").date()
        d1 = datetime.strptime(end, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    days = (d1 - d0).days + 1
    if 70 <= days <= 110:
        return ("quarterly", f"{days} days")
    if 330 <= days <= 380:
        return ("annual", f"{days} days")
    return None

def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-json", type=Path, help="Optional Companyfacts JSON fixture; otherwise downloads SEC data")
    ap.add_argument("--output-dir", type=Path, default=Path("NVIDEA/02_DADOS_FINANCEIROS"))
    args = ap.parse_args()
    retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = fetch_companyfacts(args.input_json)
    facts = payload.get("facts", {}).get("us-gaap", {})
    if not facts:
        raise SystemExit("SEC payload has no us-gaap facts; refusing to emit an empty model dataset")

    # Discover filing accessions and preserve the source-level filing identity.
    filing_meta: dict[str, dict] = {}
    for concept, fact in facts.items():
        for unit, observations in fact.get("units", {}).items():
            for obs in observations:
                acc = obs.get("accn")
                if not acc:
                    continue
                meta = filing_meta.setdefault(acc, {"filed": obs.get("filed",""), "form": obs.get("form",""), "period": obs.get("end",""), "fy": obs.get("fy"), "fp": obs.get("fp")})
                if obs.get("filed","") > meta.get("filed",""):
                    meta.update({"filed":obs.get("filed",""),"form":obs.get("form",""),"period":obs.get("end",""),"fy":obs.get("fy"),"fp":obs.get("fp")})
    eligible = {a:m for a,m in filing_meta.items() if m.get("form") in {"10-K","10-Q"}}
    sorted_acc = sorted(eligible, key=lambda a: (eligible[a].get("filed",""), a))
    source_id_by_acc = {acc:f"SRC-{i:03d}" for i,acc in enumerate(sorted_acc,1)}
    sources = []
    for acc in sorted_acc:
        m = eligible[acc]
        acc_clean = acc.replace("-","")
        sources.append({
            "source_id":source_id_by_acc[acc],"source_name":f"NVIDIA {m.get('form')} filing {acc}",
            "source_type":"filing","owner_or_provider":"U.S. Securities and Exchange Commission",
            "period_covered":m.get("period",""),"as_of_date":m.get("filed",""),"retrieved_at":retrieved,
            "file_tab_page_url_or_location":f"https://www.sec.gov/Archives/edgar/data/1045810/{acc_clean}/ (accession {acc})",
            "source_rank":"3","freshness_status":"current" if m.get("filed","") == max(x.get("filed","") for x in eligible.values()) else "acceptable_for_period",
            "notes":"Filing identity mapped from SEC Companyfacts observation metadata; exact concept/tag retained in row locator."
        })
    rows, issues = [], []
    seen = set()
    available_line_items = {mapping[1] for tag, mapping in TAGS.items() if tag in facts}
    for tag, mapping in TAGS.items():
        statement, item_id, label, allowed_units, kind = mapping
        if tag not in facts:
            if item_id not in available_line_items:
                issues.append({"severity":"medium","issue_type":"concept_not_present","source_id":"","concept":tag,"period_end":"","description":"No mapped US-GAAP alternative for this line item was present in the SEC Companyfacts payload.","recommended_action":"Inspect issuer taxonomy or filing statement; add an explicit mapping only after review."})
            continue
        for unit, observations in facts[tag].get("units", {}).items():
            if unit not in allowed_units:
                continue
            for obs in observations:
                acc = obs.get("accn","")
                if acc not in source_id_by_acc or obs.get("form") not in {"10-K","10-Q"}:
                    continue
                end = obs.get("end","")
                start = obs.get("start","")
                if not end:
                    continue
                if kind == "duration":
                    bucket = duration_bucket(start, end)
                    if not bucket:
                        continue  # YTD/stub durations are intentionally excluded from quarterly/annual load series.
                    period_type, span_note = bucket
                    # Avoid treating a 10-Q's annual comparative fact as a current annual observation.
                    if period_type == "annual" and obs.get("form") != "10-K":
                        continue
                    period_label = fiscal_label(end, obs.get("fy"), obs.get("fp"))
                else:
                    period_type, span_note = "quarterly" if obs.get("form") == "10-Q" else "annual", "instant balance"
                    period_label = fiscal_label(end, obs.get("fy"), obs.get("fp"))
                key = (item_id, unit, start, end, acc, period_type)
                if key in seen:
                    continue
                seen.add(key)
                raw = obs.get("val")
                if raw is None:
                    continue
                # Normalize monetary facts to USD millions; shares to millions; per-share remains USD/share.
                if unit == "USD":
                    normalized, units_out, currency = float(raw)/1_000_000, "$mm", "USD"
                elif unit == "shares":
                    normalized, units_out, currency = float(raw)/1_000_000, "mm shares", "shares"
                elif unit == "USD/shares":
                    normalized, units_out, currency = float(raw), "USD/share", "USD"
                else:
                    continue
                source_id = source_id_by_acc[acc]
                rows.append({
                    "entity":ENTITY,"source_id":source_id,"statement":statement,
                    "line_item_original":tag,"line_item_standard":label,"line_item_id":item_id,
                    "period_end":end,"period_label":period_label,"period_type":period_type,
                    "currency":currency,"units":units_out,"source_value":str(raw),
                    "normalized_value":f"{normalized:.8f}".rstrip("0").rstrip("."),
                    "normalization_method":"scaled_to_millions" if unit in {"USD","shares"} else "as_reported",
                    "source_location":f"SEC Companyfacts us-gaap:{tag}; accession={acc}; start={start or 'instant'}; end={end}; form={obs.get('form')}",
                    "evidence_label":"fact_source_reported","confidence":"high",
                    "normalization_note":f"SEC unit={unit}; duration={span_note}; filed={obs.get('filed','')}; fiscal metadata fp={obs.get('fp','')} fy={obs.get('fy','')}"
                })

    # Add the Companyfacts endpoint itself as a provenance record.
    sources.insert(0,{
        "source_id":"SRC-000","source_name":"SEC Companyfacts API — NVIDIA CIK 1045810",
        "source_type":"web","owner_or_provider":"U.S. Securities and Exchange Commission",
        "period_covered":"Companyfacts payload; filing observations carry individual periods",
        "as_of_date":retrieved[:10],"retrieved_at":retrieved,"file_tab_page_url_or_location":COMPANYFACTS_URL,
        "source_rank":"3","freshness_status":"current","notes":"Raw SEC XBRL facts; rows are linked to individual filing accessions."
    })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir/"Source_Index.csv", SOURCE_COLUMNS, sources)
    write_csv(args.output_dir/"Normalized_Financials_Long.csv", LONG_COLUMNS, rows)
    write_csv(args.output_dir/"Normalization_Issues.csv", ISSUE_COLUMNS, issues)

    # Conservative QA: verify key balance-sheet identity when all components coexist.
    latest_bs = defaultdict(dict)
    for r in rows:
        if r["statement"] == "balance_sheet" and r["period_type"] in {"quarterly","annual"}:
            latest_bs[(r["period_end"], r["source_id"])][r["line_item_id"]] = float(r["normalized_value"])
    flags, checks = [], []
    for idx, ((period, source_id), vals) in enumerate(sorted(latest_bs.items()),1):
        if all(k in vals for k in ("total_assets","total_liabilities","total_equity")):
            variance = vals["total_assets"] - vals["total_liabilities"] - vals["total_equity"]
            ok = abs(variance) <= 1.0  # $1mm tolerance
            checks.append({"check_id":f"CHK-{idx:03d}","area":"balance_sheet","period":period,"test":"Assets = liabilities + equity (USD mm)","expected_value":vals["total_assets"],"observed_value":vals["total_liabilities"]+vals["total_equity"],"variance":variance,"result":"PASS" if ok else "FAIL","source_id":source_id,"notes":"Tolerance: USD 1mm; all components in this test share the same filing source_id."})
            if not ok:
                flags.append({"flag_id":f"QA-{len(flags)+1:03d}","severity":"high","entity":ENTITY,"period":period,"area":"balance_sheet","issue":f"Balance sheet identity variance {variance:.3f} USD mm.","impact":"Could indicate mapping, period, or filing-selection conflict.","recommended_fix":"Inspect accession-level facts and statement presentation before model loading.","source_id":source_id,"status":"open"})
        else:
            checks.append({"check_id":f"CHK-{idx:03d}","area":"balance_sheet","period":period,"test":"Assets = liabilities + equity","expected_value":"","observed_value":"","variance":"","result":"NOT_TESTABLE","source_id":source_id,"notes":"One or more required components are absent in this filing."})
    if not rows:
        raise SystemExit("No eligible facts extracted; no empty financial package will be accepted")
    write_csv(args.output_dir/"QA_Flags.csv", QA_COLUMNS, flags)
    write_csv(args.output_dir/"Validation_Checks.csv", CHECK_COLUMNS, checks)
    print(json.dumps({"entity":ENTITY,"rows":len(rows),"filings":len(sources)-1,"issues":len(issues),"qa_flags":len(flags),"periods":len({period for period, _ in latest_bs}),"output_dir":str(args.output_dir)},indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
