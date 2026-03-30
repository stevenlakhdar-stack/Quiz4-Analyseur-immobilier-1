from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).with_name(".matplotlib")))
Path(os.environ["MPLCONFIGDIR"]).mkdir(exist_ok=True)

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
import streamlit as st


DATA_PATH = Path(__file__).with_name("kc_house_data.csv")
DICTIONARY_PATH = Path(__file__).with_name("dictionnaire_variables (1).txt")


st.set_page_config(
    page_title="King County Real Estate Lab",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #102a43;
            --muted: #486581;
            --teal: #0f766e;
            --sand: #f7f4ea;
            --amber: #b45309;
            --card-shadow: 0 18px 50px rgba(16, 42, 67, 0.10);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(15, 118, 110, 0.15), transparent 32%),
                radial-gradient(circle at bottom right, rgba(180, 83, 9, 0.12), transparent 28%),
                linear-gradient(180deg, #f5fbfa 0%, #f8f4eb 100%);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 2.2rem;
            padding-bottom: 2.5rem;
        }

        .hero-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(240,248,247,0.98));
            border: 1px solid rgba(15, 118, 110, 0.14);
            border-radius: 28px;
            padding: 2rem 2.2rem;
            box-shadow: var(--card-shadow);
            margin-bottom: 1.2rem;
        }

        .hero-kicker {
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--teal);
            margin-bottom: 0.85rem;
        }

        .hero-title {
            color: var(--ink);
            font-size: 2.25rem;
            line-height: 1.05;
            font-weight: 800;
            margin: 0 0 0.55rem 0;
        }

        .hero-copy {
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.65;
            margin: 0;
            max-width: 860px;
        }

        .hero-chip-row {
            display: flex;
            gap: 0.65rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }

        .hero-chip {
            background: rgba(15, 118, 110, 0.10);
            color: var(--teal);
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            font-size: 0.9rem;
            font-weight: 600;
        }

        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(16, 42, 67, 0.08);
            border-radius: 20px;
            padding: 0.95rem 1rem;
            box-shadow: 0 10px 30px rgba(16, 42, 67, 0.05);
        }

        div[data-testid="stMetricLabel"] {
            color: var(--muted);
            font-weight: 600;
        }

        .signal-card {
            background: linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(255, 255, 255, 0.95));
            border: 1px solid rgba(15, 118, 110, 0.18);
            border-radius: 22px;
            padding: 1rem 1.1rem;
            color: var(--ink);
            margin-bottom: 1rem;
        }

        .signal-title {
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .signal-copy {
            color: var(--muted);
            margin: 0;
            line-height: 1.55;
        }

        .mini-note {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.55;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_currency(value: float | int | np.floating) -> str:
    if pd.isna(value):
        return "n/a"
    return f"${value:,.0f}"


def format_compact_currency(value: float | int | np.floating) -> str:
    if pd.isna(value):
        return "n/a"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}k"
    return f"${value:,.0f}"


def currency_axis(_: plt.Axes) -> FuncFormatter:
    return FuncFormatter(lambda value, _: format_compact_currency(value))


@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%dT%H%M%S")
    df["zipcode"] = df["zipcode"].astype(str)
    numeric_columns = [
        "price",
        "bedrooms",
        "bathrooms",
        "sqft_living",
        "sqft_lot",
        "floors",
        "waterfront",
        "view",
        "condition",
        "grade",
        "sqft_above",
        "sqft_basement",
        "yr_built",
        "yr_renovated",
        "lat",
        "long",
        "sqft_living15",
        "sqft_lot15",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["sale_month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["sale_year"] = df["date"].dt.year
    df["price_per_sqft"] = df["price"] / df["sqft_living"].replace(0, np.nan)
    df["house_age"] = df["date"].dt.year - df["yr_built"]
    df["renovated"] = df["yr_renovated"].gt(0)
    df["waterfront_label"] = np.where(df["waterfront"].eq(1), "Oui", "Non")
    df["renovation_label"] = np.where(df["renovated"], "Renovee", "D'origine")
    return df


def build_sidebar_filters(df: pd.DataFrame) -> dict[str, object]:
    st.sidebar.title("Pilotage")
    st.sidebar.caption("Ajustez les filtres pour isoler un segment du marche du comte de King.")

    date_min = df["date"].min().date()
    date_max = df["date"].max().date()
    price_min = int(df["price"].min())
    price_max = int(df["price"].max())
    sqft_min = int(df["sqft_living"].min())
    sqft_max = int(df["sqft_living"].max())

    date_range = st.sidebar.slider(
        "Periode de vente",
        min_value=date_min,
        max_value=date_max,
        value=(date_min, date_max),
    )
    price_range = st.sidebar.slider(
        "Prix ($)",
        min_value=price_min,
        max_value=price_max,
        value=(price_min, price_max),
        step=25_000,
    )
    living_range = st.sidebar.slider(
        "Surface habitable (sqft)",
        min_value=sqft_min,
        max_value=sqft_max,
        value=(sqft_min, sqft_max),
        step=50,
    )
    bedroom_range = st.sidebar.slider(
        "Chambres",
        min_value=int(df["bedrooms"].min()),
        max_value=int(df["bedrooms"].max()),
        value=(int(df["bedrooms"].min()), int(df["bedrooms"].max())),
    )
    bathroom_range = st.sidebar.slider(
        "Salles de bain",
        min_value=float(df["bathrooms"].min()),
        max_value=float(df["bathrooms"].max()),
        value=(float(df["bathrooms"].min()), float(df["bathrooms"].max())),
        step=0.25,
    )
    grade_range = st.sidebar.slider(
        "Grade",
        min_value=int(df["grade"].min()),
        max_value=int(df["grade"].max()),
        value=(int(df["grade"].min()), int(df["grade"].max())),
    )
    zipcodes = st.sidebar.multiselect(
        "Zipcodes",
        options=sorted(df["zipcode"].unique()),
        help="Laissez vide pour inclure l'ensemble du comte.",
    )
    waterfront_mode = st.sidebar.radio(
        "Front de mer",
        options=["Tous", "Oui", "Non"],
        horizontal=True,
    )
    renovated_only = st.sidebar.checkbox("Seulement les biens renoves", value=False)

    return {
        "date_range": date_range,
        "price_range": price_range,
        "living_range": living_range,
        "bedroom_range": bedroom_range,
        "bathroom_range": bathroom_range,
        "grade_range": grade_range,
        "zipcodes": zipcodes,
        "waterfront_mode": waterfront_mode,
        "renovated_only": renovated_only,
    }


def apply_filters(df: pd.DataFrame, filters: dict[str, object]) -> pd.DataFrame:
    date_start, date_end = filters["date_range"]
    price_low, price_high = filters["price_range"]
    living_low, living_high = filters["living_range"]
    bed_low, bed_high = filters["bedroom_range"]
    bath_low, bath_high = filters["bathroom_range"]
    grade_low, grade_high = filters["grade_range"]

    mask = (
        df["date"].between(pd.Timestamp(date_start), pd.Timestamp(date_end))
        & df["price"].between(price_low, price_high)
        & df["sqft_living"].between(living_low, living_high)
        & df["bedrooms"].between(bed_low, bed_high)
        & df["bathrooms"].between(bath_low, bath_high)
        & df["grade"].between(grade_low, grade_high)
    )

    zipcodes = filters["zipcodes"]
    if zipcodes:
        mask &= df["zipcode"].isin(zipcodes)

    waterfront_mode = filters["waterfront_mode"]
    if waterfront_mode == "Oui":
        mask &= df["waterfront"].eq(1)
    elif waterfront_mode == "Non":
        mask &= df["waterfront"].eq(0)

    if filters["renovated_only"]:
        mask &= df["renovated"]

    return df.loc[mask].copy()


def premium_from_binary(df: pd.DataFrame, column: str) -> float | None:
    grouped = df.groupby(column)["price"].median()
    if len(grouped) < 2 or grouped.min() <= 0:
        return None
    return grouped.iloc[-1] / grouped.iloc[0] - 1


def monthly_price_change(df: pd.DataFrame) -> float | None:
    monthly = df.groupby("sale_month")["price"].median().sort_index()
    if len(monthly) < 2 or monthly.iloc[0] == 0:
        return None
    return monthly.iloc[-1] / monthly.iloc[0] - 1


def render_hero(filtered_df: pd.DataFrame, full_df: pd.DataFrame) -> None:
    share = len(filtered_df) / len(full_df)
    change = monthly_price_change(filtered_df)
    change_text = "Tendance insuffisante"
    if change is not None:
        direction = "hausse" if change >= 0 else "baisse"
        change_text = f"{direction} mediane {change:+.1%}"

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-kicker">King County, WA</div>
            <div class="hero-title">Market Explorer et Property Lab</div>
            <p class="hero-copy">
                Cette application permet a l'equipe investissement d'explorer rapidement le marche residentiel,
                de comparer des micro-segments et d'evaluer des transactions individuelles avec des comparables
                et une couche d'analyse IA optionnelle.
            </p>
            <div class="hero-chip-row">
                <span class="hero-chip">{len(filtered_df):,} transactions visibles</span>
                <span class="hero-chip">{share:.0%} du dataset conserve</span>
                <span class="hero-chip">Prix median {format_compact_currency(filtered_df["price"].median())}</span>
                <span class="hero-chip">{change_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(filtered_df: pd.DataFrame) -> None:
    col1, col2, col3, col4, col5 = st.columns(5)
    ppsf = filtered_df["price_per_sqft"].median()
    waterfront_premium = premium_from_binary(filtered_df, "waterfront")
    renovation_premium = premium_from_binary(filtered_df, "renovated")

    with col1:
        st.metric("Transactions", f"{len(filtered_df):,}")
    with col2:
        st.metric("Prix median", format_currency(filtered_df["price"].median()))
    with col3:
        st.metric("Prix moyen / sqft", f"${ppsf:,.0f}")
    with col4:
        st.metric(
            "Prime front de mer",
            "n/a" if waterfront_premium is None else f"{waterfront_premium:+.1%}",
        )
    with col5:
        st.metric(
            "Prime renovation",
            "n/a" if renovation_premium is None else f"{renovation_premium:+.1%}",
        )


def render_monthly_chart(df: pd.DataFrame) -> None:
    monthly = (
        df.groupby("sale_month")
        .agg(median_price=("price", "median"), sales=("id", "count"))
        .reset_index()
    )

    fig, ax1 = plt.subplots(figsize=(10, 4.6))
    ax2 = ax1.twinx()

    ax1.plot(
        monthly["sale_month"],
        monthly["median_price"],
        color="#0f766e",
        linewidth=3,
        marker="o",
        markersize=5,
    )
    ax2.bar(
        monthly["sale_month"],
        monthly["sales"],
        width=20,
        color="#f0d9b5",
        edgecolor="#b45309",
        alpha=0.7,
    )

    ax1.set_title("Prix median mensuel et volume de transactions", loc="left", fontsize=13, weight="bold")
    ax1.set_ylabel("Prix median")
    ax2.set_ylabel("Transactions")
    ax1.yaxis.set_major_formatter(currency_axis(ax1))
    ax1.grid(axis="y", alpha=0.18)
    ax1.set_xlabel("")

    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_price_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.hist(df["price"], bins=35, color="#0f766e", alpha=0.75, edgecolor="#0c4a45")
    median_price = df["price"].median()
    ax.axvline(median_price, color="#b45309", linestyle="--", linewidth=2)
    ax.set_title("Distribution des prix de vente", loc="left", fontsize=13, weight="bold")
    ax.set_xlabel("Prix de vente")
    ax.set_ylabel("Nombre de transactions")
    ax.xaxis.set_major_formatter(currency_axis(ax))
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_zipcode_chart(df: pd.DataFrame) -> None:
    zipcode_summary = (
        df.groupby("zipcode")
        .agg(transactions=("id", "count"), median_price=("price", "median"))
        .query("transactions >= 25")
        .sort_values("median_price", ascending=False)
        .head(12)
        .sort_values("median_price")
    )

    if zipcode_summary.empty:
        st.info("Pas assez de volume pour afficher le classement des zipcodes.")
        return

    fig, ax = plt.subplots(figsize=(10, 5.2))
    bars = ax.barh(
        zipcode_summary.index,
        zipcode_summary["median_price"],
        color="#89d5cc",
        edgecolor="#0f766e",
    )
    ax.set_title("Top zipcodes par prix median", loc="left", fontsize=13, weight="bold")
    ax.set_xlabel("Prix median")
    ax.xaxis.set_major_formatter(currency_axis(ax))
    ax.grid(axis="x", alpha=0.18)

    for bar, transactions in zip(bars, zipcode_summary["transactions"]):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f"  {transactions} ventes",
            va="center",
            fontsize=9,
            color="#486581",
        )

    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_scatter_chart(df: pd.DataFrame) -> None:
    sample = df.sample(min(len(df), 3_000), random_state=42) if len(df) > 3_000 else df
    fig, ax = plt.subplots(figsize=(10, 5.1))
    scatter = ax.scatter(
        sample["sqft_living"],
        sample["price"],
        c=sample["grade"],
        cmap="YlGnBu",
        s=32,
        alpha=0.6,
        edgecolors="none",
    )
    ax.set_title("Prix vs surface habitable", loc="left", fontsize=13, weight="bold")
    ax.set_xlabel("Surface habitable (sqft)")
    ax.set_ylabel("Prix")
    ax.yaxis.set_major_formatter(currency_axis(ax))
    ax.grid(alpha=0.18)
    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label("Grade")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_bedroom_boxplot(df: pd.DataFrame) -> None:
    plot_df = df[df["bedrooms"].between(1, 7)].copy()
    if plot_df.empty:
        st.info("Pas assez de donnees pour le boxplot des chambres.")
        return

    groups = [
        plot_df.loc[plot_df["bedrooms"].eq(bedroom), "price"] / 1_000
        for bedroom in sorted(plot_df["bedrooms"].unique())
    ]
    labels = [str(int(bedroom)) for bedroom in sorted(plot_df["bedrooms"].unique())]

    fig, ax = plt.subplots(figsize=(10, 4.9))
    box = ax.boxplot(groups, patch_artist=True, labels=labels)
    for patch in box["boxes"]:
        patch.set(facecolor="#9ad7cf", alpha=0.85, edgecolor="#0f766e")
    for median in box["medians"]:
        median.set(color="#b45309", linewidth=2)

    ax.set_title("Distribution des prix par nombre de chambres", loc="left", fontsize=13, weight="bold")
    ax.set_xlabel("Chambres")
    ax.set_ylabel("Prix (en milliers de dollars)")
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_grade_chart(df: pd.DataFrame) -> None:
    summary = (
        df.groupby("grade")
        .agg(median_price=("price", "median"), median_ppsf=("price_per_sqft", "median"), sales=("id", "count"))
        .sort_index()
    )
    fig, ax1 = plt.subplots(figsize=(10, 4.9))
    ax2 = ax1.twinx()
    ax1.plot(summary.index, summary["median_ppsf"], color="#0f766e", linewidth=3, marker="o")
    ax2.bar(summary.index, summary["sales"], color="#f0d9b5", edgecolor="#b45309", alpha=0.75)
    ax1.set_title("Qualite de construction: prix au sqft et profondeur de marche", loc="left", fontsize=13, weight="bold")
    ax1.set_xlabel("Grade")
    ax1.set_ylabel("Prix median / sqft")
    ax2.set_ylabel("Transactions")
    ax1.yaxis.set_major_formatter(currency_axis(ax1))
    ax1.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_market_tab(filtered_df: pd.DataFrame) -> None:
    render_kpis(filtered_df)
    st.markdown("")
    left, right = st.columns(2)
    with left:
        render_monthly_chart(filtered_df)
    with right:
        render_price_distribution(filtered_df)

    left, right = st.columns(2)
    with left:
        render_zipcode_chart(filtered_df)
    with right:
        render_scatter_chart(filtered_df)


def render_segmentation_tab(filtered_df: pd.DataFrame) -> None:
    premium_table = (
        filtered_df.assign(segment=np.where(filtered_df["waterfront"].eq(1), "Front de mer", "Interieur"))
        .groupby("segment")
        .agg(
            transactions=("id", "count"),
            median_price=("price", "median"),
            median_ppsf=("price_per_sqft", "median"),
            median_grade=("grade", "median"),
        )
        .reset_index()
    )

    col1, col2 = st.columns([1.05, 1.25])
    with col1:
        st.markdown("#### Prime de micro-segment")
        display = premium_table.copy()
        display["median_price"] = display["median_price"].map(format_currency)
        display["median_ppsf"] = display["median_ppsf"].map(lambda value: f"${value:,.0f}")
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.markdown(
            """
            <p class="mini-note">
            Utilisez cette vue pour tester rapidement si la performance est surtout tiree par l'emplacement,
            la qualite de construction ou la rarete du stock visible.
            </p>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        render_bedroom_boxplot(filtered_df)

    st.markdown("")
    left, right = st.columns(2)
    with left:
        render_grade_chart(filtered_df)
    with right:
        render_scatter_chart(filtered_df)


def property_label(row: pd.Series) -> str:
    return (
        f"ID {row['id']} | ZIP {row['zipcode']} | {format_currency(row['price'])} | "
        f"{int(row['sqft_living']):,} sqft | {int(row['bedrooms'])} ch"
    )


def compute_similarity_scores(df: pd.DataFrame, subject: pd.Series) -> pd.Series:
    sale_gap_days = (df["date"] - subject["date"]).abs().dt.days
    sqft_scale = max(subject["sqft_living"], 500)

    return (
        (df["zipcode"] != subject["zipcode"]).astype(float) * 2.2
        + (df["waterfront"] != subject["waterfront"]).astype(float) * 1.7
        + (df["grade"] - subject["grade"]).abs() * 0.8
        + (df["condition"] - subject["condition"]).abs() * 0.45
        + (df["bedrooms"] - subject["bedrooms"]).abs() * 0.65
        + (df["bathrooms"] - subject["bathrooms"]).abs() * 0.75
        + (df["sqft_living"] - subject["sqft_living"]).abs() / sqft_scale
        + sale_gap_days / 180
        + (df["lat"] - subject["lat"]).abs() * 35
        + (df["long"] - subject["long"]).abs() * 35
    )


def find_comparables(df: pd.DataFrame, subject: pd.Series, n: int = 10) -> pd.DataFrame:
    base = df.loc[df["id"] != subject["id"]].copy()
    base["sale_gap_days"] = (base["date"] - subject["date"]).abs().dt.days

    strict = base[
        base["sale_gap_days"].le(365)
        & base["sqft_living"].between(subject["sqft_living"] * 0.65, subject["sqft_living"] * 1.35)
        & base["bedrooms"].between(subject["bedrooms"] - 2, subject["bedrooms"] + 2)
        & base["bathrooms"].between(subject["bathrooms"] - 1.5, subject["bathrooms"] + 1.5)
    ].copy()

    relaxed = base[
        base["sale_gap_days"].le(540)
        & base["sqft_living"].between(subject["sqft_living"] * 0.50, subject["sqft_living"] * 1.50)
        & base["bedrooms"].between(subject["bedrooms"] - 3, subject["bedrooms"] + 3)
        & base["bathrooms"].between(subject["bathrooms"] - 2.0, subject["bathrooms"] + 2.0)
    ].copy()

    candidates = strict if len(strict) >= n else relaxed
    if candidates.empty:
        candidates = base.copy()

    candidates["similarity_score"] = compute_similarity_scores(candidates, subject)
    return candidates.nsmallest(n, "similarity_score").copy()


def compute_valuation(subject: pd.Series, comparables: pd.DataFrame) -> dict[str, float | str]:
    weights = 1 / (comparables["similarity_score"] + 0.25)
    weighted_price = np.average(comparables["price"], weights=weights)
    weighted_ppsf = np.average(comparables["price_per_sqft"], weights=weights)
    ppsf_estimate = weighted_ppsf * subject["sqft_living"]
    grade_adjustment = 1 + (subject["grade"] - comparables["grade"].median()) * 0.025
    fair_value = (0.65 * weighted_price + 0.35 * ppsf_estimate) * grade_adjustment
    low_value = fair_value * 0.92
    high_value = fair_value * 1.08
    gap = subject["price"] - fair_value
    gap_pct = gap / fair_value if fair_value else 0.0

    if subject["price"] < low_value:
        signal = "Sous evaluee"
        signal_copy = "Le prix historique se situe sous la borne basse de la fourchette estimee."
    elif subject["price"] > high_value:
        signal = "Prime elevee"
        signal_copy = "La transaction s'est faite au-dessus de la fourchette estimee par les comparables."
    else:
        signal = "Prix coherent"
        signal_copy = "Le prix historique reste globalement aligne avec les comparables les plus proches."

    return {
        "fair_value": float(fair_value),
        "low_value": float(low_value),
        "high_value": float(high_value),
        "gap": float(gap),
        "gap_pct": float(gap_pct),
        "weighted_ppsf": float(weighted_ppsf),
        "signal": signal,
        "signal_copy": signal_copy,
    }


def build_takeaways(subject: pd.Series, comparables: pd.DataFrame, valuation: dict[str, float | str]) -> list[str]:
    local_market = comparables["price_per_sqft"].median()
    renovation_text = "bien renove" if subject["renovated"] else "bien non renove"
    return [
        (
            f"La transaction selectionnee a ete conclue a {format_currency(subject['price'])}, "
            f"soit {valuation['gap_pct']:+.1%} vs la juste valeur estimee."
        ),
        (
            f"Le prix au sqft du bien ({subject['price_per_sqft']:,.0f} $/sqft) se compare a "
            f"{local_market:,.0f} $/sqft sur les comparables retenus."
        ),
        (
            f"Le signal modele est '{valuation['signal']}' sur un {renovation_text}, "
            f"grade {int(subject['grade'])}, vendu en ZIP {subject['zipcode']}."
        ),
    ]


def render_property_tab(filtered_df: pd.DataFrame, full_df: pd.DataFrame) -> tuple[pd.Series | None, pd.DataFrame, dict[str, float | str] | None]:
    if filtered_df.empty:
        st.warning("Aucune transaction disponible dans le filtre courant.")
        return None, pd.DataFrame(), None

    option_rows = filtered_df.sort_values(["zipcode", "price"], ascending=[True, False])
    option_ids = option_rows["id"].tolist()
    label_map = {row["id"]: property_label(row) for _, row in option_rows.iterrows()}

    selected_id = st.selectbox(
        "Selectionnez une transaction a examiner",
        options=option_ids,
        format_func=lambda property_id: label_map[property_id],
    )
    subject = filtered_df.loc[filtered_df["id"].eq(selected_id)].iloc[0]
    comparables = find_comparables(full_df, subject)
    valuation = compute_valuation(subject, comparables)

    st.markdown(
        f"""
        <div class="signal-card">
            <div class="signal-title">{valuation['signal']}</div>
            <p class="signal-copy">
                {valuation['signal_copy']} Fourchette estimee:
                {format_currency(valuation['low_value'])} - {format_currency(valuation['high_value'])}.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Prix historique", format_currency(subject["price"]))
    with col2:
        st.metric("Juste valeur", format_currency(valuation["fair_value"]), delta=f"{valuation['gap_pct']:+.1%}")
    with col3:
        st.metric("Prix estime / sqft", f"${valuation['weighted_ppsf']:,.0f}")
    with col4:
        st.metric("Comparables utilises", f"{len(comparables)}")

    left, right = st.columns([1.1, 1.2])
    with left:
        snapshot = pd.DataFrame(
            {
                "Attribut": [
                    "Date de vente",
                    "Zipcode",
                    "Chambres",
                    "Salles de bain",
                    "Surface habitable",
                    "Surface terrain",
                    "Grade",
                    "Condition",
                    "Annee de construction",
                    "Renovation",
                    "Vue",
                    "Front de mer",
                ],
                "Valeur": [
                    subject["date"].date().isoformat(),
                    subject["zipcode"],
                    int(subject["bedrooms"]),
                    f"{subject['bathrooms']:.2f}",
                    f"{int(subject['sqft_living']):,} sqft",
                    f"{int(subject['sqft_lot']):,} sqft",
                    int(subject["grade"]),
                    int(subject["condition"]),
                    int(subject["yr_built"]),
                    "Oui" if subject["renovated"] else "Non",
                    int(subject["view"]),
                    "Oui" if subject["waterfront"] == 1 else "Non",
                ],
            }
        )
        st.markdown("#### Fiche rapide")
        st.dataframe(snapshot, use_container_width=True, hide_index=True)
        st.markdown("#### Points de lecture")
        for takeaway in build_takeaways(subject, comparables, valuation):
            st.markdown(f"- {takeaway}")

    with right:
        st.markdown("#### Carte locale")
        map_df = pd.concat(
            [
                pd.DataFrame({"lat": [subject["lat"]], "lon": [subject["long"]]}),
                comparables[["lat", "long"]].rename(columns={"long": "lon"}),
            ],
            ignore_index=True,
        )
        st.map(map_df, use_container_width=True)

    st.markdown("#### Table des comparables")
    comparables_display = comparables[
        [
            "id",
            "date",
            "zipcode",
            "price",
            "price_per_sqft",
            "sqft_living",
            "bedrooms",
            "bathrooms",
            "grade",
            "similarity_score",
        ]
    ].copy()
    comparables_display["date"] = comparables_display["date"].dt.date.astype(str)
    comparables_display["price"] = comparables_display["price"].map(format_currency)
    comparables_display["price_per_sqft"] = comparables_display["price_per_sqft"].map(lambda value: f"${value:,.0f}")
    comparables_display["sqft_living"] = comparables_display["sqft_living"].map(lambda value: f"{int(value):,}")
    comparables_display["similarity_score"] = comparables_display["similarity_score"].map(lambda value: f"{value:.2f}")
    st.dataframe(comparables_display, use_container_width=True, hide_index=True)

    return subject, comparables, valuation


def market_context_text(filtered_df: pd.DataFrame, full_df: pd.DataFrame) -> str:
    monthly = (
        filtered_df.groupby("sale_month")
        .agg(median_price=("price", "median"), sales=("id", "count"))
        .sort_index()
    )
    zipcode_summary = (
        filtered_df.groupby("zipcode")
        .agg(transactions=("id", "count"), median_price=("price", "median"))
        .sort_values("transactions", ascending=False)
        .head(5)
    )
    lines = [
        f"Visible universe: {len(filtered_df)} transactions out of {len(full_df)} total.",
        f"Sale period: {filtered_df['date'].min().date()} to {filtered_df['date'].max().date()}.",
        f"Median price: {format_currency(filtered_df['price'].median())}.",
        f"Average price: {format_currency(filtered_df['price'].mean())}.",
        f"Median price per sqft: ${filtered_df['price_per_sqft'].median():,.0f}.",
        f"Median living area: {filtered_df['sqft_living'].median():,.0f} sqft.",
        f"Waterfront share: {filtered_df['waterfront'].mean():.1%}.",
        f"Renovated share: {filtered_df['renovated'].mean():.1%}.",
    ]

    if len(monthly) >= 2:
        start_price = monthly["median_price"].iloc[0]
        end_price = monthly["median_price"].iloc[-1]
        lines.append(
            f"Median monthly price moved from {format_currency(start_price)} to {format_currency(end_price)}, "
            f"or {end_price / start_price - 1:+.1%}."
        )

    if not zipcode_summary.empty:
        top_zipcodes = ", ".join(
            [
                f"{zipcode} ({row['transactions']} sales, median {format_currency(row['median_price'])})"
                for zipcode, row in zipcode_summary.iterrows()
            ]
        )
        lines.append(f"Top zipcodes by volume: {top_zipcodes}.")

    return "\n".join(lines)


def property_context_text(
    subject: pd.Series | None,
    comparables: pd.DataFrame,
    valuation: dict[str, float | str] | None,
) -> str:
    if subject is None or valuation is None:
        return "No individual property selected."

    comparable_lines = []
    if not comparables.empty:
        top_comps = comparables.nsmallest(min(len(comparables), 5), "similarity_score")
        for _, row in top_comps.iterrows():
            comparable_lines.append(
                f"- Comparable {row['id']} in ZIP {row['zipcode']}: sold at {format_currency(row['price'])}, "
                f"{int(row['sqft_living']):,} sqft, grade {int(row['grade'])}, score {row['similarity_score']:.2f}"
            )

    lines = [
        f"Selected property id: {subject['id']}.",
        f"Historical sale date: {subject['date'].date()}.",
        f"Sale price: {format_currency(subject['price'])}.",
        f"Characteristics: {int(subject['bedrooms'])} bedrooms, {subject['bathrooms']:.2f} bathrooms, "
        f"{int(subject['sqft_living']):,} sqft living area, grade {int(subject['grade'])}, "
        f"condition {int(subject['condition'])}, built {int(subject['yr_built'])}, zipcode {subject['zipcode']}.",
        f"Waterfront: {'yes' if subject['waterfront'] == 1 else 'no'}. Renovated: {'yes' if subject['renovated'] else 'no'}.",
        f"Model fair value: {format_currency(valuation['fair_value'])}.",
        f"Estimated range: {format_currency(valuation['low_value'])} to {format_currency(valuation['high_value'])}.",
        f"Observed gap versus fair value: {valuation['gap_pct']:+.1%}.",
        f"Pricing signal: {valuation['signal']}.",
        "Closest comparables:",
    ]
    lines.extend(comparable_lines if comparable_lines else ["- No comparables available."])
    return "\n".join(lines)


def generate_ai_analysis(
    api_key: str,
    model_name: str,
    market_context: str,
    property_context: str,
    user_prompt: str,
) -> str:
    from google import genai

    client = genai.Client(api_key=api_key)
    prompt = (
        "You are a buy-side real estate analyst supporting an investment committee.\n"
        "Respond in French.\n"
        "Be concise, numerical, decision-oriented, and explicit about what is observed versus inferred.\n\n"
        "Market context:\n"
        f"{market_context}\n\n"
        "Property context:\n"
        f"{property_context}\n\n"
        "User request:\n"
        f"{user_prompt}\n"
    )
    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )
    return response.text


def render_ai_tab(
    filtered_df: pd.DataFrame,
    full_df: pd.DataFrame,
    subject: pd.Series | None,
    comparables: pd.DataFrame,
    valuation: dict[str, float | str] | None,
) -> None:
    st.markdown(
        """
        <p class="mini-note">
        La couche IA est optionnelle. Elle transforme les chiffres du tableau de bord et, si vous le souhaitez,
        la propriete selectionnee en note de synthese en francais.
        </p>
        """,
        unsafe_allow_html=True,
    )

    default_prompt = (
        "Redige une note d'investissement de 3 parties: synthese du segment filtre, "
        "risques/points d'attention, et recommandation actionnable pour l'equipe."
    )
    api_key = st.text_input(
        "Cle API Google",
        value=os.getenv("GOOGLE_API_KEY", ""),
        type="password",
        help="La cle n'est pas stockee par l'application. Vous pouvez aussi definir GOOGLE_API_KEY dans votre environnement.",
    )
    model_name = st.text_input("Modele Google", value="gemini-3.1-flash-lite-preview")
    user_prompt = st.text_area("Consigne d'analyse", value=default_prompt, height=140)

    market_context = market_context_text(filtered_df, full_df)
    property_context = property_context_text(subject, comparables, valuation)

    with st.expander("Voir le contexte envoye au modele"):
        st.code(f"Market context\n{market_context}\n\nProperty context\n{property_context}", language="text")

    if st.button("Generer l'analyse IA", type="primary"):
        if not api_key:
            st.warning("Ajoutez une cle API Google pour lancer l'analyse.")
            return

        try:
            with st.spinner("Generation de la note en cours..."):
                answer = generate_ai_analysis(
                    api_key=api_key,
                    model_name=model_name,
                    market_context=market_context,
                    property_context=property_context,
                    user_prompt=user_prompt,
                )
        except ImportError:
            st.error("Le package google-genai n'est pas installe. Installez les dependances avec requirements.txt.")
            return
        except Exception as error:
            st.error(f"Echec de l'appel Google GenAI: {error}")
            return

        st.markdown("#### Note IA")
        st.write(answer)
        st.download_button(
            "Telecharger la note",
            data=answer,
            file_name="note_ia_immobiliere.md",
            mime="text/markdown",
        )


def render_dataset_footer(filtered_df: pd.DataFrame) -> None:
    with st.expander("Apercu des transactions visibles"):
        preview = filtered_df[
            ["id", "date", "price", "zipcode", "bedrooms", "bathrooms", "sqft_living", "grade", "condition"]
        ].copy()
        preview["date"] = preview["date"].dt.date.astype(str)
        preview["price"] = preview["price"].map(format_currency)
        st.dataframe(preview.head(100), use_container_width=True, hide_index=True)

    with st.expander("Dictionnaire des variables"):
        if DICTIONARY_PATH.exists():
            dictionary_text = DICTIONARY_PATH.read_text(encoding="utf-8", errors="ignore")
            st.text(dictionary_text)
        else:
            st.info("Le dictionnaire n'a pas ete trouve dans le dossier du projet.")


def main() -> None:
    inject_styles()

    if not DATA_PATH.exists():
        st.error("Le fichier kc_house_data.csv est introuvable dans le dossier du projet.")
        st.stop()

    df = load_data(str(DATA_PATH))
    filters = build_sidebar_filters(df)
    filtered_df = apply_filters(df, filters)

    render_hero(filtered_df, df)

    if filtered_df.empty:
        st.warning("Aucune transaction ne correspond aux filtres actuels. Elargissez le segment analyse.")
        st.stop()

    tabs = st.tabs(
        [
            "Vue marche",
            "Segmentation",
            "Evaluateur de propriete",
            "Assistant IA",
        ]
    )

    selected_property = None
    selected_comparables = pd.DataFrame()
    selected_valuation = None

    with tabs[0]:
        render_market_tab(filtered_df)

    with tabs[1]:
        render_segmentation_tab(filtered_df)

    with tabs[2]:
        selected_property, selected_comparables, selected_valuation = render_property_tab(filtered_df, df)

    with tabs[3]:
        render_ai_tab(filtered_df, df, selected_property, selected_comparables, selected_valuation)

    render_dataset_footer(filtered_df)


if __name__ == "__main__":
    main()
