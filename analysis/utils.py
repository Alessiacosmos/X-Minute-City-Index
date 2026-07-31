import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter
from scipy import stats

country_map = {"DE": "Germany", "NL": "Netherlands", "ES": "Spain"}

style_map = {
    "Germany": {"color": "#009E73", "marker": "o"},  # circle
    "Netherlands": {"color": "#56B4E9", "marker": "D"},  # diamond
    "Spain": {"color": "#E69F00", "marker": "s"},  # square
}

city_name_fixes_map = {
    "München": "Munich",
    "'s-Gravenhage": "The Hague",
    "Köln": "Cologne",
}

travel_mode_map = {"foot-walking": "walking", "cycling-regular": "biking"}


def calc_correlation_accessibility_anal(
    category_name: str,
    category_both_scores: pd.DataFrame,
    ax: plt.Axes,
    nice_ticks_real: list[int],
):
    x = category_both_scores["population"]

    # regression
    x_range = x.max() - x.min()
    x_min, x_max = x.min() - x_range * 0.05, x.max() + x_range * 0.05

    line_x = np.linspace(x_min, x_max, 100)

    # 3. Plot
    # scatter points, colored/shaped by country
    for country, style in style_map.items():
        pts = category_both_scores[category_both_scores["country"] == country]
        country_x, country_y = pts["population"], pts[f"{category_name}"]
        ax.scatter(
            country_x,
            country_y,
            color=style["color"],
            marker=style["marker"],
            edgecolor="black",
            linewidth=0.3,
            alpha=0.9,
            s=50,
            label=country,
        )

        # regression line
        country_valid = ~np.isnan(country_x) & ~np.isnan(country_y)
        country_x_valid, country_y_valid = (
            country_x[country_valid],
            country_y[country_valid],
        )
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            country_x_valid, country_y_valid
        )
        line_y = slope * line_x + intercept

        if not np.isnan(slope):
            linestyle = "-" if p_value < 0.05 else "--"
            ax.plot(
                line_x, line_y, color=style["color"], linestyle=linestyle, linewidth=1.5
            )

    ax.set_title(f"{category_name.capitalize()}", fontsize=12)

    ax.set_xlim(x_min, x_max)

    # keep only ticks within the actual data range, to avoid clutter/out-of-range labels
    nice_ticks_real = [v for v in nice_ticks_real if x_min <= np.log10(v) <= x_max]

    # convert to log10(thousands) coordinate space to match your transformed x
    tick_positions = [np.log10(v) for v in nice_ticks_real]
    tick_labels = [f"{v:,.0f}" for v in nice_ticks_real]

    ax.xaxis.set_major_locator(FixedLocator(tick_positions))
    ax.xaxis.set_major_formatter(FixedFormatter(tick_labels))

    ax.set_ylim(0, 100)


def calc_correlation_data_quality(
    category_name: str,
    category_both_scores: pd.DataFrame,
    ax: plt.Axes,
    x_suffix: str = "quality",
    y_suffix: str = "access",
):
    x, y = (
        category_both_scores[f"{category_name}_{x_suffix}"],
        category_both_scores[f"{category_name}_{y_suffix}"],
    )

    # regression
    valid = ~np.isnan(x) & ~np.isnan(y)
    x_valid, y_valid = x[valid], y[valid]
    slope, intercept, r_value, p_value, std_err = stats.linregress(x_valid, y_valid)
    # line_x = np.linspace(x.min(), x.max(), 100)
    if x_suffix == "quality":
        line_x = np.linspace(0, 100, 100)
    else:
        line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept

    # 3. Plot
    # scatter points, colored/shaped by country
    for country, style in style_map.items():
        pts = category_both_scores[category_both_scores["country"] == country]
        ax.scatter(
            pts[f"{category_name}_{x_suffix}"],
            pts[f"{category_name}_{y_suffix}"],
            color=style["color"],
            marker=style["marker"],
            edgecolor="black",
            linewidth=0.3,
            alpha=0.9,
            s=50,
            label=country,
        )

    # regression line
    if not np.isnan(slope):
        ax.plot(line_x, line_y, color="black", linewidth=2)
        reg_label = f"y={slope:.2f}x+{intercept:.2f}, $R^2$={r_value**2:.2f}"
    else:
        reg_label = "Regression: n/a"

    ax.set_title(f"{category_name.capitalize()} ({reg_label})", fontsize=11)

    ax.set_xlim(0, 100) if x_suffix in ["access", "quality"] else ax.set_xlim(
        x.min(), x.max()
    )
    ax.set_ylim(0, 100) if y_suffix in ["access", "quality"] else ax.set_ylim(
        y.min(), y.max()
    )
