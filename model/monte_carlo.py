"""
monte_carlo.py

Runs the DCF thousands of times, each time randomly sampling the genuinely
uncertain inputs from probability distributions instead of using single
point estimates - producing a distribution of possible valuations rather
than one number.

Which inputs are treated as uncertain, and why:

1. BETA - genuine, flagged source disagreement (CNBC: 0.23, TradingView:
   -0.23) found while building the original model. Modelled as Normal,
   centred on the original point estimate, with a spread wide enough to
   cover the real disagreement between sources.

2. 2029 GROWTH RATE (the Keytruda patent-cliff year) - the single most
   genuinely uncertain assumption in the whole model. Merck's own 10-K
   says US sales will decline "materially" but does not quantify by how
   much. Given a much wider spread than the other, more routine forecast
   years.

3. OTHER GROWTH YEARS (2026-2028, 2030) - given a smaller, routine amount
   of uncertainty, since these aren't tied to a specific known structural
   event the way 2029 is.

4. TERMINAL GROWTH RATE - standard practice to treat as uncertain in a
   DCF Monte Carlo; a long-run assumption nobody can know precisely.

5. FCF MARGIN - historical margins ranged from 15.2% to 28.2% (2021-2025),
   genuinely volatile, not a stable, precisely-known figure.

A genuine numerical risk, handled explicitly: if a sampled WACC ends up
below the sampled terminal growth rate, the Gordon Growth terminal value
formula is mathematically invalid. Rather than silently producing a
nonsense (or crashing) result, these draws are caught, discarded, and
counted - and reported, since a high discard rate would itself be a sign
the distributions are poorly calibrated relative to each other.
"""

import sys
import os
import numpy as np
from datetime import datetime, timezone


sys.path.insert(0, os.path.dirname(__file__))
from dcf_model import run_dcf, DEFAULT_GROWTH_ASSUMPTIONS, HISTORICAL_AVG_FCF_MARGIN, DEFAULT_TERMINAL_GROWTH_RATE
from merck_historicals import STOCK_PRICE_AS_OF

N_SIMULATIONS = 10_000
RNG = np.random.default_rng(seed=42)  # fixed seed - reproducible results, documented, not "random each time"

# --- Distribution parameters, each with the reasoning noted above ---
BETA_MEAN, BETA_STD = 0.30, 0.15
GROWTH_2029_MEAN, GROWTH_2029_STD = DEFAULT_GROWTH_ASSUMPTIONS[2029], 0.04  # wide - the Keytruda cliff year
ROUTINE_GROWTH_STD = 0.01  # applied to 2026, 2027, 2028, 2030
TERMINAL_GROWTH_MEAN, TERMINAL_GROWTH_STD = DEFAULT_TERMINAL_GROWTH_RATE, 0.005
FCF_MARGIN_MEAN, FCF_MARGIN_STD = HISTORICAL_AVG_FCF_MARGIN, 0.03
 

 
def run_simulation(n_simulations: int = N_SIMULATIONS):
    implied_prices = []
    n_discarded = 0
 
    betas = RNG.normal(BETA_MEAN, BETA_STD, n_simulations)
    growth_2029_draws = RNG.normal(GROWTH_2029_MEAN, GROWTH_2029_STD, n_simulations)
    terminal_growth_draws = RNG.normal(TERMINAL_GROWTH_MEAN, TERMINAL_GROWTH_STD, n_simulations)
    fcf_margin_draws = RNG.normal(FCF_MARGIN_MEAN, FCF_MARGIN_STD, n_simulations)
 
    routine_years = [y for y in DEFAULT_GROWTH_ASSUMPTIONS if y != 2029]
    routine_growth_draws = {
        year: RNG.normal(DEFAULT_GROWTH_ASSUMPTIONS[year], ROUTINE_GROWTH_STD, n_simulations)
        for year in routine_years
    }
 
    for i in range(n_simulations):
        growth_assumptions = {year: routine_growth_draws[year][i] for year in routine_years}
        growth_assumptions[2029] = growth_2029_draws[i]
 
        try:
            results = run_dcf(
                growth_assumptions=growth_assumptions,
                fcf_margin=fcf_margin_draws[i],
                terminal_growth_rate=terminal_growth_draws[i],
                beta=betas[i],
            )
            implied_prices.append(results["implied_share_price"])
        except ValueError:
            # WACC <= terminal growth rate for this particular draw - the
            # Gordon Growth formula is invalid here. Discard and count.
            n_discarded += 1
            continue
 
    return np.array(implied_prices), n_discarded


def summarize_results(implied_prices: np.ndarray, n_discarded: int, current_price: float,
                       n_requested: int = N_SIMULATIONS):
    print("=" * 60)
    print("MONTE CARLO DCF SIMULATION - Merck & Co. (MRK)")
    print(f"Stock price as of: {STOCK_PRICE_AS_OF}  |  Analysis run: "
          f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)
    print(f"Simulations run: {n_requested:,}  |  Valid results: {len(implied_prices):,}  "
          f"|  Discarded (invalid WACC/terminal growth combo): {n_discarded:,} "
          f"({n_discarded/n_requested:.1%})")
    print()
    print(f"Mean implied share price:    ${implied_prices.mean():>8.2f}")
    print(f"Median implied share price:  ${np.median(implied_prices):>8.2f}")
    print(f"Std deviation:               ${implied_prices.std():>8.2f}")
    print()
    p5, p25, p75, p95 = np.percentile(implied_prices, [5, 25, 75, 95])
    print(f"5th percentile:              ${p5:>8.2f}")
    print(f"25th percentile:             ${p25:>8.2f}")
    print(f"75th percentile:             ${p75:>8.2f}")
    print(f"95th percentile:             ${p95:>8.2f}")
    print()
    print(f"Current market price:        ${current_price:>8.2f}")
    pct_overvalued = (implied_prices < current_price).mean()
    print(f"P(model implies overvalued): {pct_overvalued:.1%}")
    print(f"  (i.e. in {pct_overvalued:.1%} of simulations, the model's implied")
    print(f"   price came in BELOW the current market price of ${current_price:.2f})")
 
 
 
def plot_distribution(implied_prices: np.ndarray, current_price: float,
                       output_path: str = "output/monte_carlo_distribution.png"):
    """Saves a histogram of the simulated implied share prices, with a
    vertical line marking the current market price for visual comparison.
    Optional - only called if --plot is passed, so the core simulation
    stays fast for repeated runs without matplotlib overhead."""
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend - saves to file, doesn't need a display
    import matplotlib.pyplot as plt
 
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
 
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(implied_prices, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
    ax.axvline(current_price, color="#C44E52", linestyle="--", linewidth=2,
               label=f"Current market price (${current_price:.2f})")
    ax.axvline(np.median(implied_prices), color="#55A868", linestyle="--", linewidth=2,
               label=f"Median implied price (${np.median(implied_prices):.2f})")
 
    ax.set_title("Merck (MRK) DCF - Monte Carlo Distribution of Implied Share Price",
                 fontsize=13, fontweight="bold", pad=28)
    ax.text(0.5, 1.04,
            f"Stock price as of {STOCK_PRICE_AS_OF}  |  Analysis run "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            transform=ax.transAxes, ha="center", fontsize=9, color="gray")
    ax.set_xlabel("Implied share price ($)")
    ax.set_ylabel("Number of simulations")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
 
    print(f"\nChart saved to: {output_path}")
 
 
if __name__ == "__main__":
    import argparse
    from merck_historicals import CURRENT_STOCK_PRICE
 
    parser = argparse.ArgumentParser(description="Run Monte Carlo DCF simulation for Merck.")
    parser.add_argument("--plot", action="store_true",
                         help="Also generate and save a histogram of the results (requires matplotlib).")
    parser.add_argument("--n-simulations", type=int, default=N_SIMULATIONS,
                         help=f"Number of Monte Carlo simulations to run (default: {N_SIMULATIONS:,}).")
    args = parser.parse_args()
 
    implied_prices, n_discarded = run_simulation(n_simulations=args.n_simulations)
    summarize_results(implied_prices, n_discarded, CURRENT_STOCK_PRICE, n_requested=args.n_simulations)
 
    if args.plot:
        plot_distribution(implied_prices, CURRENT_STOCK_PRICE)
 