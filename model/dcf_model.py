"""
dcf_model.py

Core DCF valuation for Merck & Co. (MRK).

Approach: project revenue growth using Monte Carlo run (informed by real,
company-specific facts - the Keytruda patent cliff - not a generic flat
growth rate), apply a normalized historical FCF margin to get projected
free cash flow, discount each year back to present value at WACC, add a
terminal value, and bridge from Enterprise Value to an implied per-share
equity value.

Monte Carlo simulation can vary growth assumptions, terminal growth rate, 
FCF margin, and WACC per iteration. 
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from merck_historicals import (
    REVENUE, FREE_CASH_FLOW, NET_DEBT_FY2025, SHARES_OUTSTANDING_MILLIONS,
    CURRENT_STOCK_PRICE, STOCK_PRICE_AS_OF,
)

from wacc import calculate_wacc

# Historical FCF margin - still computed from fixed historical data (not
# varied by Monte Carlo directly; Monte Carlo instead varies the ASSUMED
# margin used in projections, via the fcf_margin parameter below, which
# defaults to this historical average)

FCF_MARGINS = {year: FREE_CASH_FLOW[year] / REVENUE[year] for year in REVENUE}
HISTORICAL_AVG_FCF_MARGIN = sum(FCF_MARGINS.values()) / len(FCF_MARGINS)
 
BASE_YEAR_REVENUE = REVENUE[2025]

# --- Revenue growth assumptions, explicit forecast period (2026-2030) ---
# Deliberately NOT a flat rate for every year - built around the single
# most important real, company-specific fact: Keytruda (~49% of FY2025
# revenue) is explicitly expected by Merck itself (per its own FY2025
# 10-K) to see "materially" declining U.S. sales once government
# price-setting under the IRA takes effect Jan 1, 2029.
# Default growth assumptions - same reasoning as before (Keytruda patent
# cliff explicitly modelled in 2029), now passed as a parameter so Monte
# Carlo can perturb individual years, especially 2029 (the most genuinely
# uncertain assumption in this whole model).

DEFAULT_GROWTH_ASSUMPTIONS = {
    2026: 0.03,   # modest growth - documented near-term headwinds already
                  # biting (Januvia/Janumet under IRA price-setting from
                  # Jan 2026, MFN pricing agreement, China contraction)
    2027: 0.03,   # continued modest growth, Keytruda still pre-cliff
    2028: 0.02,   # growth decelerating as the 2029 cliff approaches
    2029: -0.03,  # Keytruda patent-cliff year - explicit revenue DECLINE,
                  # not just slower growth, reflecting Merck's own stated
                  # expectation of "material" US sales decline
    2030: 0.01,   # early stabilization/partial recovery via pipeline
                  # (Winrevair, oncology ADCs, enlicitide decanoate, etc.)
}

DEFAULT_TERMINAL_GROWTH_RATE = 0.025  # long-run assumption: modest, sustainable
                               # growth once diversified beyond Keytruda,
                               # roughly in line with long-term GDP/inflation



 
def project_financials(growth_assumptions: dict, fcf_margin: float, wacc: float):
    forecast_years = sorted(growth_assumptions.keys())
    projections = {}
    prior_revenue = BASE_YEAR_REVENUE
 
    for i, year in enumerate(forecast_years, start=1):
        growth = growth_assumptions[year]
        revenue = prior_revenue * (1 + growth)
        fcf = revenue * fcf_margin
        discount_factor = 1 / ((1 + wacc) ** i)
        pv_fcf = fcf * discount_factor
 
        projections[year] = {
            "year_number": i, "revenue": revenue, "fcf": fcf,
            "discount_factor": discount_factor, "pv_fcf": pv_fcf,
        }
        prior_revenue = revenue
 
    return projections
 



def calculate_terminal_value(projections: dict, terminal_growth_rate: float, wacc: float,
                               min_spread: float = 0.02):
    final_year = max(projections.keys())
    final_fcf = projections[final_year]["fcf"]
    final_discount_factor = projections[final_year]["discount_factor"]
 
    # Guard against WACC being too close to (or below) the terminal growth
    # rate. This is NOT just "WACC > terminal growth" - when the two are
    # merely close (e.g. WACC = 3.1%, terminal growth = 3.0%), the Gordon
    # Growth denominator becomes tiny and the formula produces extreme,
    # not-genuinely-meaningful valuations (found empirically: one Monte
    # Carlo run produced an implied share price of $4,030 from exactly
    # this cause). A minimum required spread is standard, careful practice
    # for exactly this reason, not an arbitrary extra restriction.
    if wacc - terminal_growth_rate < min_spread:
        raise ValueError(
            f"WACC ({wacc:.4f}) is too close to terminal growth rate "
            f"({terminal_growth_rate:.4f}) - spread of {wacc - terminal_growth_rate:.4f} "
            f"is below the minimum required {min_spread:.4f}. Gordon Growth "
            f"formula becomes numerically unstable near this boundary."
        )
 
    terminal_value_undiscounted = (
        final_fcf * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
    )
    pv_terminal_value = terminal_value_undiscounted * final_discount_factor
    return terminal_value_undiscounted, pv_terminal_value
 
 
def run_dcf(
    growth_assumptions: dict = None,
    fcf_margin: float = None,
    terminal_growth_rate: float = None,
    wacc: float = None,
    beta: float = 0.30,
):
    """Runs the full DCF. Any parameter left as None uses the original
    single-point default. `wacc`, if not provided directly, is computed
    from `beta` via calculate_wacc() - this lets Monte Carlo vary beta
    specifically (the input with genuine, flagged source disagreement)
    without needing to separately pass a pre-computed WACC each time."""
    if growth_assumptions is None:
        growth_assumptions = DEFAULT_GROWTH_ASSUMPTIONS
    if fcf_margin is None:
        fcf_margin = HISTORICAL_AVG_FCF_MARGIN
    if terminal_growth_rate is None:
        terminal_growth_rate = DEFAULT_TERMINAL_GROWTH_RATE
    if wacc is None:
        wacc = calculate_wacc(beta=beta)
 
    projections = project_financials(growth_assumptions, fcf_margin, wacc)
    terminal_value_undiscounted, pv_terminal_value = calculate_terminal_value(
        projections, terminal_growth_rate, wacc
    )
 
    sum_pv_fcf = sum(p["pv_fcf"] for p in projections.values())
    enterprise_value = sum_pv_fcf + pv_terminal_value
    equity_value = enterprise_value - NET_DEBT_FY2025
    implied_share_price = equity_value / SHARES_OUTSTANDING_MILLIONS
    upside_downside = (implied_share_price / CURRENT_STOCK_PRICE) - 1
 
    return {
        "projections": projections,
        "terminal_value_undiscounted": terminal_value_undiscounted,
        "pv_terminal_value": pv_terminal_value,
        "sum_pv_fcf": sum_pv_fcf,
        "enterprise_value": enterprise_value,
        "net_debt": NET_DEBT_FY2025,
        "equity_value": equity_value,
        "implied_share_price": implied_share_price,
        "current_share_price": CURRENT_STOCK_PRICE,
        "upside_downside": upside_downside,
        "wacc_used": wacc,
    }
 
 
def print_dcf_report(results):
    print("=" * 65)
    print("DCF VALUATION - Merck & Co. (MRK)")
    print(f"Stock price as of: {STOCK_PRICE_AS_OF}  |  Analysis run: "
          f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 65)
    print(f"WACC used: {results['wacc_used']:.2%}")
    print()
    print(f"{'Year':<8}{'Revenue ($M)':>15}{'FCF ($M)':>13}{'Disc. Factor':>14}{'PV of FCF ($M)':>16}")
    print("-" * 66)
    for year, p in results["projections"].items():
        print(f"{year:<8}{p['revenue']:>15,.0f}{p['fcf']:>13,.0f}{p['discount_factor']:>14.3f}{p['pv_fcf']:>16,.0f}")
    print()
    print(f"Sum of PV of explicit-period FCF:     ${results['sum_pv_fcf']:>14,.0f}M")
    print(f"Terminal value (undiscounted):        ${results['terminal_value_undiscounted']:>14,.0f}M")
    print(f"PV of terminal value:                 ${results['pv_terminal_value']:>14,.0f}M")
    print("-" * 66)
    print(f"ENTERPRISE VALUE:                     ${results['enterprise_value']:>14,.0f}M")
    print(f"Less: Net debt:                       ${results['net_debt']:>14,.0f}M")
    print(f"EQUITY VALUE:                          ${results['equity_value']:>14,.0f}M")
    print("-" * 66)
    print(f"Shares outstanding (M):                {SHARES_OUTSTANDING_MILLIONS:>14,.1f}")
    print(f"IMPLIED SHARE PRICE:                   ${results['implied_share_price']:>14.2f}")
    print(f"Current share price:                   ${results['current_share_price']:>14.2f}")
    print(f"Implied upside/(downside):              {results['upside_downside']:>13.1%}")
 
 
if __name__ == "__main__":
    results = run_dcf()  # all defaults - identical to the original single-point model
    print_dcf_report(results)
 