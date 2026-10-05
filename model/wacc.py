"""
wacc.py

Calculates Merck's Weighted Average Cost of Capital (WACC) - the discount
rate used to bring projected future cash flows back to present value.

WACC blends the cost of equity and cost of debt, weighted by each
source's share of the company's total capital (at market value).
 
Refactored into a parameterized function (calculate_wacc) so Monte Carlo
simulation can vary beta, the equity risk premium, etc. per iteration,
rather than reading fixed module-level constants. Default argument values
preserve the exact same single-point assumptions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from merck_historicals import (
    CURRENT_STOCK_PRICE, SHARES_OUTSTANDING_MILLIONS, TOTAL_DEBT_FY2025,
)

# Fixed inputs that Monte Carlo does NOT vary (kept as module-level
# constants since they're not being treated as uncertain in this project)

# Effective tax rate, computed from FY2025 actuals: pretax income $21,067M,
# net income $18,254M -> tax rate = 1 - (18254/21067). Genuinely below the
# US statutory 21% rate, reflecting Merck's international revenue mix.

EFFECTIVE_TAX_RATE = 1 - (18254 / 21067)

MARKET_CAP = CURRENT_STOCK_PRICE * SHARES_OUTSTANDING_MILLIONS
TOTAL_CAPITAL = MARKET_CAP + TOTAL_DEBT_FY2025
WEIGHT_EQUITY = MARKET_CAP / TOTAL_CAPITAL
WEIGHT_DEBT = TOTAL_DEBT_FY2025 / TOTAL_CAPITAL



def calculate_wacc(
    beta: float = 0.30,
    risk_free_rate: float = 0.0472, # 10-year US Treasury yield, Aug 31, 2026 (source: tradingeconomics.com)
    equity_risk_premium: float = 0.05, ## standard long-term historical average assumption
    pre_tax_cost_of_debt: float = 0.050,
) -> float:
    """
    Calculates WACC from the given inputs. Defaults match the original
    single-point assumptions this project started with.
    
    ## ----- beta
    # Merck's reported beta varies by source (CNBC: 0.23, TradingView: -0.23) -
    # sign disagreement, but both agree the MAGNITUDE is very low. This is
    # genuinely consistent with Merck's real profile: a large, stable,
    # dividend-paying pharma company whose stock has historically moved with
    # unusually low sensitivity to broad market swings - not a data error.
    # Using a conservative, rounded, clearly-flagged estimate rather than
    # either source's exact (and disputed) figure.

    ## ----- Cost of debt 
    # No direct market-quoted yield-to-maturity gathered for Merck's specific
    # bonds; using a documented, reasonable estimate for an investment-grade
    # large-cap pharma issuer (modest spread over the risk-free rate).
    """


    ## --- Cost of equity, via CAPM: Cost of Equity = Rf + Beta x ERP ---
    cost_of_equity = risk_free_rate + beta * equity_risk_premium #based on CAPM
    after_tax_cost_of_debt = pre_tax_cost_of_debt * (1 - EFFECTIVE_TAX_RATE)
 
    wacc = (WEIGHT_EQUITY * cost_of_equity) + (WEIGHT_DEBT * after_tax_cost_of_debt)
    return wacc


def print_wacc_breakdown(beta: float = 0.30, risk_free_rate: float = 0.0472,
                          equity_risk_premium: float = 0.05,
                          pre_tax_cost_of_debt: float = 0.050):
    cost_of_equity = risk_free_rate + beta * equity_risk_premium
    after_tax_cost_of_debt = pre_tax_cost_of_debt * (1 - EFFECTIVE_TAX_RATE)
    wacc = calculate_wacc(beta, risk_free_rate, equity_risk_premium, pre_tax_cost_of_debt)
 
    print("=" * 55)
    print("WACC CALCULATION - Merck & Co. (MRK)")
    print("=" * 55)
    print(f"Risk-free rate (10yr Treasury):     {risk_free_rate:.2%}")
    print(f"Beta (assumed, see note):            {beta:.2f}")
    print(f"Equity risk premium (assumed):        {equity_risk_premium:.2%}")
    print(f"  -> Cost of equity (CAPM):          {cost_of_equity:.2%}")
    print()
    print(f"Pre-tax cost of debt (assumed):      {pre_tax_cost_of_debt:.2%}")
    print(f"Effective tax rate (from FY25):      {EFFECTIVE_TAX_RATE:.2%}")
    print(f"  -> After-tax cost of debt:         {after_tax_cost_of_debt:.2%}")
    print()
    print(f"Market cap:                          ${MARKET_CAP:,.0f}M")
    print(f"Total debt:                          ${TOTAL_DEBT_FY2025:,.0f}M")
    print(f"Weight of equity:                     {WEIGHT_EQUITY:.1%}")
    print(f"Weight of debt:                       {WEIGHT_DEBT:.1%}")
    print()
    print(f"WACC = {wacc:.2%}")
 
 
# Module-level constant, computed with the default (single-point) assumptions -
# kept for backward compatibility with dcf_model.py's existing `from wacc
# import WACC` usage.
WACC = calculate_wacc()
 
 
if __name__ == "__main__":
    print_wacc_breakdown()
    print()
    print("Note: this WACC is low relative to typical pharma DCF")
    print("assumptions (often 7-9%), driven directly by Merck's unusually")
    print("low reported beta - a real characteristic of this specific")
    print("stock's defensive profile, not an error. Worth sensitivity")
    print("testing against a higher beta assumption (see Monte Carlo step).")
 