"""
merck_historicals.py

Historical financial data for Merck & Co. (MRK).

Two tiers of data, deliberately kept separate:

1. LONG HISTORY (2007-2025) - sourced directly from SEC EDGAR's official
   Company Facts API (data.sec.gov), via fetch_merck_data_sec_edgar.py.
   Kept for genuine context and transparency, NOT fed directly into the
   DCF's growth/margin assumptions (see note below on why).

2. RECENT WINDOW (2021-2025) - the actual data used by the DCF model's
   assumptions (wacc.py, dcf_model.py). Cross-checked between
   stockanalysis.com (S&P Global Market Intelligence) and SEC EDGAR/
   yfinance.

IMPORTANT: why the long history isn't used for growth-rate/margin
calculations directly - there is a genuine structural break in the data,
not just noise. Revenue jumped from $27.4B (2009) to $46.0B (2010), a 68%
increase - this is NOT organic growth, it reflects Merck's completed
merger with Schering-Plough in November 2009 (2010 was the first full
year of combined reporting). Any growth rate calculated across this
boundary would be measuring "corporate merger," not underlying business
performance. The DCF's assumptions are deliberately restricted to the
recent, single-corporate-structure window (2021-2025) for this reason.

Known gaps in the SEC EDGAR pull (preserved as None, NOT interpolated or
estimated - consistent with the "flag, don't fabricate" approach used
throughout this whole project): revenue is missing 2011-2015, and
operating cash flow is missing 2021. Very likely caused by a shift in
which XBRL tag Merck used to report these figures in those specific
years - the fetch script's tag lookup didn't catch the alternate tag.
CapEx was not pulled for the long-history window at all, so a full-history
Free Cash Flow figure cannot be computed without a further data pull.
"""

# =============================================================================
# LONG HISTORY (2007-2025) - source: SEC EDGAR Company Facts API
# For context/transparency only - NOT used in DCF growth/margin assumptions.
# =============================================================================

REVENUE_LONG_HISTORY = {
    2007: 24_197_700_000, 2008: 23_850_000_000, 2009: 27_428_000_000,
    2010: 45_987_000_000,
    # 2011-2015: MISSING - XBRL tag likely changed in this period; not
    # interpolated, left absent rather than guessed.
    2016: 39_807_000_000, 2017: 40_122_000_000, 2018: 42_294_000_000,
    2019: 39_121_000_000, 2020: 41_518_000_000, 2021: 48_704_000_000,
    2022: 59_283_000_000, 2023: 60_115_000_000, 2024: 64_168_000_000,
    2025: 65_011_000_000,
}

NET_INCOME_LONG_HISTORY = {
    2007: 3_275_400_000, 2008: 7_808_000_000, 2009: 12_899_000_000,
    2010: 861_000_000, 2011: 6_272_000_000, 2012: 6_168_000_000,
    2013: 4_404_000_000, 2014: 11_920_000_000, 2015: 4_442_000_000,
    2016: 3_920_000_000, 2017: 2_394_000_000, 2018: 6_220_000_000,
    2019: 9_843_000_000, 2020: 7_067_000_000, 2021: 13_049_000_000,
    2022: 14_519_000_000, 2023: 365_000_000, 2024: 17_117_000_000,
    2025: 18_254_000_000,
}

OPERATING_CASH_FLOW_LONG_HISTORY = {
    2007: 6_999_200_000, 2008: 6_572_000_000, 2009: 3_392_000_000,
    2010: 10_822_000_000, 2011: 12_383_000_000, 2012: 10_022_000_000,
    2013: 11_654_000_000, 2014: 7_989_000_000, 2015: 12_538_000_000,
    2016: 10_376_000_000, 2017: 6_451_000_000, 2018: 10_922_000_000,
    2019: 13_440_000_000, 2020: 10_253_000_000,
    # 2021: MISSING - same likely cause as the revenue gap above.
    2022: 19_095_000_000, 2023: 13_006_000_000, 2024: 21_468_000_000,
    2025: 16_472_000_000,
}

# =============================================================================
# RECENT WINDOW (2021-2025) - what the DCF model actually uses.
#
# PROVENANCE, FIELD BY FIELD - deliberately precise, not a blanket
# statement, since verification status genuinely differs across fields:
#
# - REVENUE: sourced from SEC EDGAR (REVENUE_LONG_HISTORY above), which
#   the user independently pulled and confirmed via the official
#   data.sec.gov Company Facts API. Verified against a primary source.
#
# - NET_INCOME: same as REVENUE - sourced from SEC EDGAR, independently
#   pulled and confirmed by the user. Verified against a primary source.
#
# - OPERATING_CASH_FLOW: originally sourced from stockanalysis.com
#   (S&P Global Market Intelligence). SUBSEQUENTLY CROSS-CHECKED against
#   the user's actual SEC EDGAR pull for 2022-2025 - all four years
#   matched exactly. 2021 was one of the gap years in the EDGAR pull
#   (see OPERATING_CASH_FLOW_LONG_HISTORY note above), so that single
#   year remains stockanalysis.com-only, unverified against a primary
#   source.
#
# - OPERATING_INCOME: stockanalysis.com only, NOT independently verified.
#   Worth flagging honestly: during initial data gathering, different
#   aggregators (Yahoo Finance, stock-analysis-on.net, stockanalysis.com)
#   showed DIFFERING operating income figures for the same fiscal years -
#   a real disagreement across sources that was never independently
#   resolved. stockanalysis.com's figures were used for internal
#   consistency with the other fields pulled from the same source, not
#   because they were confirmed correct against a primary source.
#
# - FREE_CASH_FLOW and CAPEX: stockanalysis.com only, NOT independently
#   verified. Neither yfinance nor the SEC EDGAR pull in this project
#   retrieved CapEx data at any point.
#
# - CASH_AND_INVESTMENTS_FY2025, TOTAL_DEBT_FY2025: stockanalysis.com
#   only, NOT independently verified via EDGAR or yfinance.
#
# - CURRENT_STOCK_PRICE, SHARES_OUTSTANDING_MILLIONS: from web search
#   results (CNBC for price; Merck's own FY2025 10-K filing, fetched
#   directly, for shares outstanding) - the shares figure IS a primary
#   source citation; the price is a point-in-time market quote, not
#   something that needs "verification" in the same sense.
#
# - KEYTRUDA_REVENUE_FY2025: fetched directly from Merck's actual FY2025
#   10-K filing text (Item 1, Business) - a primary source, not an
#   aggregator.
# =============================================================================

REVENUE = {year: REVENUE_LONG_HISTORY[year] // 1_000_000 for year in range(2021, 2026)}

# stockanalysis.com only - NOT independently verified (see provenance note above)
OPERATING_INCOME = {
    2021: 13893, 2022: 20490, 2023: 15974, 2024: 24889, 2025: 24467,
}

NET_INCOME = {year: NET_INCOME_LONG_HISTORY[year] // 1_000_000 for year in range(2021, 2026)}

# stockanalysis.com only - NOT independently verified
FREE_CASH_FLOW = {
    2021: 9661, 2022: 14707, 2023: 9143, 2024: 18096, 2025: 12360,
}

# stockanalysis.com originally; CONFIRMED matching SEC EDGAR for 2022-2025
# (2021 unverified - EDGAR gap year)
OPERATING_CASH_FLOW = {
    2021: 14109, 2022: 19095, 2023: 13006, 2024: 21468, 2025: 16472,
}

# stockanalysis.com only - NOT independently verified. Never pulled via
# yfinance or SEC EDGAR in this project.
CAPEX = {
    2021: 4448, 2022: 4388, 2023: 3863, 2024: 3372, 2025: 4112,
}

# Balance sheet snapshot, most recent fiscal year end (FY2025 = Dec 31, 2025)
# stockanalysis.com only - NOT independently verified via EDGAR or yfinance
CASH_AND_INVESTMENTS_FY2025 = 14565
TOTAL_DEBT_FY2025 = 50534
NET_DEBT_FY2025 = TOTAL_DEBT_FY2025 - CASH_AND_INVESTMENTS_FY2025  # 35,969

# Market data, as of ~Aug 31-Sep 1, 2026
# CURRENT_STOCK_PRICE: refreshed via web search (previous value: $148.35,
# from Aug 28). Genuine cross-source disagreement found while refreshing:
# investing.com showed $152.55 (dated Aug 23 in its own text, despite
# being labelled "today" - likely stale); CNBC showed a more detailed,
# internally consistent snapshot (Open $147.00, Day High $147.93, Day Low
# $145.95, Prev Close $148.35) that exactly matches this model's beta
# (0.23) and shares outstanding (2.47B) figures. Used CNBC's data as the
# more trustworthy source given that consistency, taking the midpoint of
# its stated trading range ($146.94) as a reasonable point-in-time
# estimate. For genuinely live pricing, use yfinance directly:
# yf.Ticker("MRK").info.get("currentPrice")
# SHARES_OUTSTANDING_MILLIONS: primary source - Merck's own FY2025 10-K,
# fetched directly, as of Jan 31, 2026
CURRENT_STOCK_PRICE = 146.94
STOCK_PRICE_AS_OF = "2026-08-31"  # approximate - see disagreement note above; refresh via yfinance for precision
SHARES_OUTSTANDING_MILLIONS = 2472.4

# Key context for growth assumptions - PRIMARY SOURCE: fetched directly
# from Merck's actual FY2025 10-K filing text (Item 1, Business), not an
# aggregator. Keytruda was 31,681 of 65,011 total revenue in FY2025
# (~49% of total) - a genuine concentration risk. Per Merck's own 10-K:
# Keytruda is expected to be selected for U.S. government price-setting
# under the IRA in 2027, effective January 1, 2029, after which the
# company "expects... U.S. sales of Keytruda will decline materially."
# This is the single most important real-world fact shaping this DCF's
# terminal growth and near-term assumptions - not a generic "pharma
# company" assumption.
KEYTRUDA_REVENUE_FY2025 = 31681
KEYTRUDA_SHARE_OF_TOTAL_REVENUE = KEYTRUDA_REVENUE_FY2025 / REVENUE[2025]

