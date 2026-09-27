"""
unit_economics.py
==================
Deterministic CAC / LTV / payback / ROAS calculator with an industry-
benchmark comparison table. This is arithmetic on inputs the caller
supplies, not a model guessing plausible-sounding numbers — every output
figure is either a direct input or a formula applied to inputs, and the
formula used is always named in the output so it can be checked by eye.

This exists because a strategic option's EVIDENCE field ("this channel
looks underpriced") is a much weaker claim than one backed by an actual
projected CAC, LTV, payback period, and a stated comparison against a
named industry benchmark band. This script is what turns the first into
the second — it does not replace judgment about which inputs to use, and
it cannot verify that the inputs themselves are real (that's the calling
agent's job, same discipline as citation_guard.py: an input pulled from
public research needs its own evidence-logged source; an input that's a
planning assumption must be labeled as one, not as fact).

What this script is NOT:
- Not a source of "true" industry benchmarks. The BENCHMARKS table below
  is a set of commonly-cited industry heuristics (the 3:1 LTV:CAC rule,
  <12-month SaaS payback as healthy, etc.) assembled from widely-repeated
  planning wisdom, not from a live, sourced dataset. Every benchmark
  comparison in the output is labeled with this ceiling explicitly.
  Report it as "the commonly-cited planning heuristic for this model is
  X," never as "the industry average is X."
- Not a predictor. It does not know whether *this* business will actually
  hit the CAC or churn rate it's given — those are the caller's
  assumptions (own historical data, a domain agent's research finding, or
  a stated planning scenario). GIGO applies; the script's only job is to
  make the arithmetic on top of those assumptions correct and legible.

Usage:
    python unit_economics.py compute --model subscription \
        --spend 50000 --new-customers 200 \
        --arpu 80 --gross-margin 0.75 --monthly-churn 0.04 \
        --business-type saas_b2b_smb [--json-out report.json]

    python unit_economics.py compute --model transactional \
        --spend 50000 --new-customers 500 \
        --aov 60 --gross-margin 0.45 \
        --orders-per-year 3 --customer-lifespan-years 2 \
        --business-type ecommerce_dtc [--json-out report.json]

    python unit_economics.py benchmarks [--business-type saas_b2b_smb]
        -- print the heuristic table (or one row) with sourcing caveat.

Exit code 0: computed successfully.
Exit code 1: inputs insufficient or structurally invalid for the chosen
             model (e.g. --monthly-churn 0 with --model subscription,
             which makes LTV divide-by-zero rather than "infinite value").
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Benchmark table — commonly-cited planning heuristics, not live-sourced
# data. Every field here should be read as "the widely-repeated rule of
# thumb for this business type," and reported to the user with that
# framing intact, not laundered into "the industry average."
# ---------------------------------------------------------------------------

BENCHMARKS = {
    "saas_b2b_smb": {
        "label": "B2B SaaS, SMB-focused",
        "ltv_cac_target": (3.0, None),       # (floor, ceiling) -- 3:1 is the standard rule of thumb; >5-7:1 often means under-investing in growth
        "ltv_cac_ceiling_note": "above roughly 5-7:1 is commonly read as under-investing in acquisition, not just efficient",
        "payback_months_target": (0, 12),     # under 12 months commonly read as healthy for SMB SaaS
        "payback_months_excellent": 5,
        "gross_margin_typical": (0.70, 0.85),
    },
    "saas_b2b_enterprise": {
        "label": "B2B SaaS, enterprise",
        "ltv_cac_target": (3.0, None),
        "ltv_cac_ceiling_note": "enterprise deals tolerate a lower ratio short-term because absolute LTV is large and expansion revenue compounds",
        "payback_months_target": (0, 18),
        "payback_months_excellent": 12,
        "gross_margin_typical": (0.70, 0.85),
    },
    "ecommerce_dtc": {
        "label": "Ecommerce / DTC",
        "ltv_cac_target": (3.0, None),
        "ltv_cac_ceiling_note": "DTC ratios above ~4:1 often signal room to spend more aggressively on acquisition while margin allows it",
        "payback_months_target": (0, 6),
        "payback_months_excellent": 2,
        "gross_margin_typical": (0.35, 0.65),
    },
    "marketplace": {
        "label": "Marketplace (two-sided)",
        "ltv_cac_target": (3.0, None),
        "ltv_cac_ceiling_note": "supply-side and demand-side CAC should be modeled and benchmarked separately -- a blended ratio here hides which side is actually expensive",
        "payback_months_target": (0, 12),
        "payback_months_excellent": 6,
        "gross_margin_typical": (0.15, 0.30),
    },
    "mobile_app_freemium": {
        "label": "Mobile app, freemium/subscription",
        "ltv_cac_target": (3.0, None),
        "ltv_cac_ceiling_note": "freemium LTV is highly sensitive to the free-to-paid conversion assumption -- treat a high ratio built on an unvalidated conversion rate as low-confidence regardless of the arithmetic",
        "payback_months_target": (0, 12),
        "payback_months_excellent": 6,
        "gross_margin_typical": (0.60, 0.80),
    },
}

BENCHMARK_SOURCING_NOTE = (
    "These are commonly-cited planning heuristics repeated across VC/operator "
    "commentary (the 3:1 LTV:CAC rule, sub-12-month SaaS payback as healthy), "
    "not figures pulled from a live, sourced benchmark dataset. Report them as "
    "'the standard planning heuristic for this business type,' not as a "
    "verified industry average -- if a claim needs a sourced figure instead of "
    "a heuristic, that's a WebFetch/WebSearch job for the calling agent, "
    "logged and citation-checked the normal way, not something this script can supply."
)


@dataclass
class Result:
    model: str
    inputs: dict
    cac: float
    ltv: float
    ltv_formula: str
    ltv_cac_ratio: float
    payback_months: float
    payback_formula: str
    roas: Optional[float] = None
    warnings: list = field(default_factory=list)
    benchmark_comparison: Optional[dict] = None


def compute_subscription(args: argparse.Namespace) -> Result:
    warnings = []

    if args.new_customers <= 0:
        raise ValueError("--new-customers must be > 0 to derive CAC from spend")
    cac = args.cac if args.cac is not None else args.spend / args.new_customers

    if args.monthly_churn is None:
        raise ValueError("--model subscription requires --monthly-churn (or use --model transactional for a lifespan-based LTV instead)")
    if args.monthly_churn <= 0:
        raise ValueError("--monthly-churn must be > 0 -- a 0% churn assumption makes LTV mathematically infinite, which isn't a usable planning number; use a floor like 0.005 (0.5%/mo) if you're modeling near-zero churn deliberately, or an explicit lifespan cap instead")
    if args.monthly_churn > 0.5:
        warnings.append(f"monthly_churn of {args.monthly_churn:.1%} is unusually high -- confirm this isn't an annual figure mislabeled as monthly")

    if args.gross_margin <= 0 or args.gross_margin > 1:
        raise ValueError("--gross-margin must be a fraction between 0 and 1 (e.g. 0.75 for 75%)")

    monthly_contribution = args.arpu * args.gross_margin
    ltv = monthly_contribution / args.monthly_churn
    ltv_formula = f"ARPU (${args.arpu:.2f}/mo) x gross_margin ({args.gross_margin:.0%}) / monthly_churn ({args.monthly_churn:.1%}) = ${ltv:,.2f}"

    payback_months = cac / monthly_contribution if monthly_contribution > 0 else float("inf")
    payback_formula = f"CAC (${cac:,.2f}) / monthly_contribution (${monthly_contribution:,.2f}) = {payback_months:.1f} months"

    ltv_cac_ratio = ltv / cac if cac > 0 else float("inf")

    if args.spend > 0 and args.new_customers > 0:
        period_revenue = args.arpu * args.new_customers
        roas = period_revenue / args.spend
    else:
        roas = None

    return Result(
        model="subscription",
        inputs=vars(args),
        cac=round(cac, 2),
        ltv=round(ltv, 2),
        ltv_formula=ltv_formula,
        ltv_cac_ratio=round(ltv_cac_ratio, 2),
        payback_months=round(payback_months, 1),
        payback_formula=payback_formula,
        roas=round(roas, 2) if roas is not None else None,
        warnings=warnings,
    )


def compute_transactional(args: argparse.Namespace) -> Result:
    warnings = []

    if args.new_customers <= 0:
        raise ValueError("--new-customers must be > 0 to derive CAC from spend")
    cac = args.cac if args.cac is not None else args.spend / args.new_customers

    if args.gross_margin <= 0 or args.gross_margin > 1:
        raise ValueError("--gross-margin must be a fraction between 0 and 1 (e.g. 0.45 for 45%)")
    if args.orders_per_year is None or args.customer_lifespan_years is None:
        raise ValueError("--model transactional requires --orders-per-year and --customer-lifespan-years")
    if args.orders_per_year <= 0 or args.customer_lifespan_years <= 0:
        raise ValueError("--orders-per-year and --customer-lifespan-years must both be > 0")

    contribution_per_order = args.aov * args.gross_margin
    ltv = contribution_per_order * args.orders_per_year * args.customer_lifespan_years
    ltv_formula = (
        f"AOV (${args.aov:.2f}) x gross_margin ({args.gross_margin:.0%}) x "
        f"orders/year ({args.orders_per_year:.1f}) x lifespan_years ({args.customer_lifespan_years:.1f}) = ${ltv:,.2f}"
    )

    first_year_contribution = contribution_per_order * args.orders_per_year
    monthly_contribution_rate = first_year_contribution / 12
    payback_months = cac / monthly_contribution_rate if monthly_contribution_rate > 0 else float("inf")
    payback_formula = (
        f"CAC (${cac:,.2f}) / (first_year_contribution (${first_year_contribution:,.2f}) / 12) = {payback_months:.1f} months"
    )

    ltv_cac_ratio = ltv / cac if cac > 0 else float("inf")

    if args.spend > 0 and args.new_customers > 0:
        first_year_revenue = args.aov * args.orders_per_year * args.new_customers
        roas = first_year_revenue / args.spend
    else:
        roas = None

    if args.customer_lifespan_years > 5:
        warnings.append(f"customer_lifespan_years of {args.customer_lifespan_years:.1f} is a long, hard-to-validate assumption -- treat resulting LTV as low-confidence and consider a discounted/shorter-horizon LTV alongside it")

    return Result(
        model="transactional",
        inputs=vars(args),
        cac=round(cac, 2),
        ltv=round(ltv, 2),
        ltv_formula=ltv_formula,
        ltv_cac_ratio=round(ltv_cac_ratio, 2),
        payback_months=round(payback_months, 1),
        payback_formula=payback_formula,
        roas=round(roas, 2) if roas is not None else None,
        warnings=warnings,
    )


def attach_benchmark_comparison(result: Result, business_type: Optional[str]) -> None:
    if not business_type:
        result.warnings.append("no --business-type given -- computed figures are not compared against any benchmark band; the output is arithmetic only, no 'is this good' read attached")
        return
    if business_type not in BENCHMARKS:
        result.warnings.append(f"unknown --business-type '{business_type}' -- valid values: {', '.join(BENCHMARKS)}. No benchmark comparison attached.")
        return

    bm = BENCHMARKS[business_type]
    floor, ceiling = bm["ltv_cac_target"]
    ratio = result.ltv_cac_ratio
    if ratio < floor:
        ltv_cac_read = f"BELOW the {floor:.0f}:1 planning heuristic for {bm['label']} -- CAC looks expensive relative to LTV at these inputs"
    elif ceiling and ratio > ceiling:
        ltv_cac_read = f"ABOVE the typical {floor:.0f}-{ceiling:.0f}:1 band for {bm['label']} -- {bm['ltv_cac_ceiling_note']}"
    else:
        ltv_cac_read = f"WITHIN the commonly-cited {floor:.0f}:1-and-up heuristic band for {bm['label']}"

    pb_floor, pb_ceiling = bm["payback_months_target"]
    pm = result.payback_months
    if pm <= bm["payback_months_excellent"]:
        payback_read = f"at or under the 'excellent' heuristic threshold ({bm['payback_months_excellent']} months) for {bm['label']}"
    elif pm <= pb_ceiling:
        payback_read = f"within the commonly-cited healthy band (under {pb_ceiling} months) for {bm['label']}"
    else:
        payback_read = f"ABOVE the commonly-cited healthy band (under {pb_ceiling} months) for {bm['label']} -- capital is tied up longer than the heuristic target"

    result.benchmark_comparison = {
        "business_type": business_type,
        "label": bm["label"],
        "ltv_cac_ratio_read": ltv_cac_read,
        "payback_months_read": payback_read,
        "gross_margin_typical_band": bm["gross_margin_typical"],
        "sourcing_note": BENCHMARK_SOURCING_NOTE,
    }


def cmd_compute(args: argparse.Namespace) -> Result:
    if args.model == "subscription":
        result = compute_subscription(args)
    elif args.model == "transactional":
        result = compute_transactional(args)
    else:
        raise ValueError(f"unknown --model '{args.model}' -- must be 'subscription' or 'transactional'")

    attach_benchmark_comparison(result, args.business_type)
    return result


def cmd_benchmarks(business_type: Optional[str]) -> dict:
    if business_type:
        if business_type not in BENCHMARKS:
            raise ValueError(f"unknown business_type '{business_type}' -- valid values: {', '.join(BENCHMARKS)}")
        rows = {business_type: BENCHMARKS[business_type]}
    else:
        rows = BENCHMARKS
    return {"benchmarks": rows, "sourcing_note": BENCHMARK_SOURCING_NOTE}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Deterministic CAC/LTV/payback/ROAS calculator with heuristic benchmark comparison.")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compute", help="Compute unit economics from real inputs.")
    c.add_argument("--model", required=True, choices=["subscription", "transactional"])
    c.add_argument("--spend", type=float, required=True, help="Total acquisition spend for the period.")
    c.add_argument("--new-customers", type=float, required=True, help="New customers acquired for that spend.")
    c.add_argument("--cac", type=float, default=None, help="Override computed CAC directly (skips spend/new_customers division) -- use when CAC is already known from real account data rather than derived.")
    c.add_argument("--gross-margin", type=float, required=True, help="Fraction 0-1, e.g. 0.75 for 75 percent.")
    c.add_argument("--business-type", default=None, choices=list(BENCHMARKS.keys()), help="Attaches a benchmark-band comparison; omit for arithmetic-only output.")
    c.add_argument("--json-out", default=None, help="Write the full result as JSON to this path in addition to stdout.")

    # subscription-model inputs
    c.add_argument("--arpu", type=float, default=None, help="[subscription] Average revenue per user per month.")
    c.add_argument("--monthly-churn", type=float, default=None, help="[subscription] Monthly churn as a fraction, e.g. 0.04 for 4 percent.")

    # transactional-model inputs
    c.add_argument("--aov", type=float, default=None, help="[transactional] Average order value.")
    c.add_argument("--orders-per-year", type=float, default=None, help="[transactional] Average orders per customer per year.")
    c.add_argument("--customer-lifespan-years", type=float, default=None, help="[transactional] Assumed active customer lifespan in years.")

    b = sub.add_parser("benchmarks", help="Print the heuristic benchmark table (with sourcing caveat), optionally filtered to one business type.")
    b.add_argument("--business-type", default=None, choices=list(BENCHMARKS.keys()))

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "compute":
            result = cmd_compute(args)
            payload = asdict(result)
            print(json.dumps(payload, indent=2))
            if args.json_out:
                Path_write(args.json_out, payload)
        elif args.command == "benchmarks":
            payload = cmd_benchmarks(args.business_type)
            print(json.dumps(payload, indent=2))
        return 0
    except ValueError as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        return 1


def Path_write(path: str, payload: dict) -> None:
    from pathlib import Path
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
