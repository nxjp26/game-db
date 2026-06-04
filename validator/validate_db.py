#!/usr/bin/env python3
import argparse, sys, math, re
import pandas as pd
import yaml

def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    # also allow case-insensitive match
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None

def to_float(x):
    if pd.isna(x):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if s == "" or s.lower() in ("nan","none","null","-"):
        return None
    # remove commas and spaces
    s = s.replace(",", "").replace(" ", "")
    # percent
    s = s.replace("%","")
    # handle japanese units like 億, 万 if present
    m = re.fullmatch(r"([-+]?\d+(\.\d+)?)(億|万)?", s)
    if m:
        val = float(m.group(1))
        unit = m.group(3)
        if unit == "億":
            val *= 100_000_000
        elif unit == "万":
            val *= 10_000
        return val
    # fallback numeric
    try:
        return float(s)
    except:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--rules", required=True)
    args = ap.parse_args()

    with open(args.rules, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)

    df = pd.read_csv(args.csv)
    errors = []
    warns = []

    # required columns
    for col in rules.get("required_columns", []):
        if col not in df.columns:
            errors.append(f"[schema] required column missing: {col}")

    opt = rules.get("optional_numeric_columns", {})
    col_rev = find_col(df, opt.get("revenue", {}).get("candidates", []))
    col_op = find_col(df, opt.get("operating_income", {}).get("candidates", []))
    col_ni = find_col(df, opt.get("net_income", {}).get("candidates", []))
    col_mg = find_col(df, opt.get("operating_margin", {}).get("candidates", []))

    margin_max = float(rules.get("thresholds", {}).get("margin_max_percent", 100.0))

    # sanity checks
    if col_mg:
        for i, v in enumerate(df[col_mg].tolist()):
            fv = to_float(v)
            if fv is None:
                continue
            # assume margin in % if it's <= 200, otherwise it's probably ratio or wrong unit
            if fv > margin_max:
                errors.append(f"[margin_over_100] row={i+2} col={col_mg} value={v}")

    def check_gt(col_a, col_b, name, level):
        if not col_a or not col_b:
            return
        a = df[col_a].tolist()
        b = df[col_b].tolist()
        for i, (va, vb) in enumerate(zip(a,b)):
            fa = to_float(va)
            fb = to_float(vb)
            if fa is None or fb is None:
                continue
            if fa > fb and fb != 0:
                msg = f"[{name}] row={i+2} {col_a}({va}) > {col_b}({vb})"
                (errors if level=="error" else warns).append(msg)

    enabled = {r["name"]: r.get("enabled", True) for r in rules.get("rules", [])}
    levels = {r["name"]: r.get("level", "warn") for r in rules.get("rules", [])}

    if enabled.get("net_income_gt_revenue", True):
        check_gt(col_ni, col_rev, "net_income_gt_revenue", levels.get("net_income_gt_revenue","error"))
    if enabled.get("operating_income_gt_revenue", True):
        check_gt(col_op, col_rev, "operating_income_gt_revenue", levels.get("operating_income_gt_revenue","error"))

    # suspicious 10x jumps: if numeric columns exist and there is a prev_ column
    if enabled.get("suspicious_unit_jump_10x", True):
        for base in [col_rev, col_op, col_ni]:
            if not base:
                continue
            prev = None
            for cand in [f"prev_{base}", f"{base}_prev", f"{base}_previous", f"전기{base}"]:
                if cand in df.columns:
                    prev = cand
                    break
            if not prev:
                continue
            for i, (va, vb) in enumerate(zip(df[base].tolist(), df[prev].tolist())):
                fa = to_float(va); fb = to_float(vb)
                if fa is None or fb is None or fb == 0:
                    continue
                ratio = abs(fa/fb)
                if ratio >= 10:
                    warns.append(f"[suspicious_unit_jump_10x] row={i+2} {base} jumped {ratio:.1f}x vs {prev}")

    # output
    if errors:
        print("FAIL")
        for e in errors[:200]:
            print("ERROR:", e)
    else:
        print("PASS")

    if warns:
        for w in warns[:200]:
            print("WARN:", w)

    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
