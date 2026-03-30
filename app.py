from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
import requests
import streamlit as st


plt.style.use("seaborn-v0_8-whitegrid")

DATA_PATH = Path(__file__).resolve().parent / "kc_house_data.csv"

COLORS = {
    "teal": "#0f766e",
    "ink": "#10231d",
    "sand": "#f5efe3",
    "card": "#fffaf4",
    "terracotta": "#b45309",
    "mist": "#d7ece7",
    "slate": "#6b7b75",
}

NUMERIC_COLUMNS = [
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


def format_currency(value: float) -> str:
    return f"${value:,.0f}"


def format_compact_currency(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.0f}k"
    return f"${value:,.0f}"


def format_pct(value: float) -> str:
    return f"{value:.1%}"


def pct_change(current: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return (current / reference) - 1


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Source+Serif+4:wght@400;600;700&display=swap');
        :root {{
            --bg: {COLORS["sand"]};
            --card: {COLORS["card"]};
            --ink: {COLORS["ink"]};
            --teal: {COLORS["teal"]};
            --terracotta: {COLORS["terracotta"]};
            --mist: {COLORS["mist"]};
            --slate: {COLORS["slate"]};
        }}
        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 30%),
                radial-gradient(circle at top right, rgba(180, 83, 9, 0.08), transparent 28%),
                linear-gradient(180deg, #f8f3ea 0%, #f3ede1 55%, #efe7da 100%);
            color: var(--ink);
            font-family: "Source Serif 4", Georgia, serif;
        }}
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }}
        h1, h2, h3, h4, .stTabs [data-baseweb="tab"] {{
            font-family: "Space Grotesk", "Segoe UI", sans-serif;
        }}
        .hero {{
            background: linear-gradient(135deg, rgba(255, 250, 244, 0.96), rgba(215, 236, 231, 0.90));
            border: 1px solid rgba(15, 118, 110, 0.15);
            border-radius: 24px;
            padding: 1.6rem 1.8rem 1.4rem;
            box-shadow: 0 18px 40px rgba(16, 35, 29, 0.08);
            margin-bottom: 1.4rem;
        }}
        .eyebrow {{
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-size: 0.75rem;
            color: var(--teal);
            margin-bottom: 0.25rem;
            font-family: "Space Grotesk", "Segoe UI", sans-serif;
            font-weight: 700;
        }}
        .hero h1 {{
            margin: 0;
            color: var(--ink);
            font-size: 2.35rem;
            line-height: 1.05;
        }}
        .hero p {{
            margin: 0.8rem 0 0;
            color: #28433b;
            font-size: 1rem;
        }}
        .section-note {{
            background: rgba(255, 250, 244, 0.8);
            border-left: 4px solid var(--terracotta);
            padding: 0.9rem 1rem;
            border-radius: 0 14px 14px 0;
            margin-bottom: 1rem;
        }}
        [data-testid="stMetric"] {{
            background: rgba(255, 250, 244, 0.92);
            border: 1px solid rgba(16, 35, 29, 0.08);
            padding: 0.8rem 1rem;
            border-radius: 18px;
            box-shadow: 0 12px 30px rgba(16, 35, 29, 0.05);
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(255, 250, 244, 0.98), rgba(247, 240, 228, 0.98));
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.75rem;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: rgba(255, 250, 244, 0.88);
            border-radius: 999px;
            border: 1px solid rgba(16, 35, 29, 0.08);
            padding: 0.55rem 1rem;
        }}
        .stTabs [aria-selected="true"] {{
            background: rgba(15, 118, 110, 0.12);
            color: var(--teal);
        }}
        .property-chip {{
            display: inline-block;
            margin: 0 0.5rem 0.5rem 0;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(15, 118, 110, 0.10);
            color: var(--ink);
            font-family: "Space Grotesk", "Segoe UI", sans-serif;
            font-size: 0.82rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, dtype={"id": "string", "zipcode": "string"})
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["sale_date"] = pd.to_datetime(df["date"], format="%Y%m%dT%H%M%S")
    df["sale_month"] = df["sale_date"].dt.to_period("M").dt.to_timestamp()
    df["sale_year"] = df["sale_date"].dt.year
    df["price_per_sqft"] = df["price"] / df["sqft_living"].replace(0, np.nan)
    df["lot_ratio"] = df["sqft_lot"] / df["sqft_living"].replace(0, np.nan)
    df["renovated"] = df["yr_renovated"].fillna(0).astype(int) > 0
    df["effective_year"] = np.where(df["yr_renovated"] > 0, df["yr_renovated"], df["yr_built"])
    df["effective_age"] = (df["sale_year"] - df["effective_year"]).clip(lower=0)
    df["price_bucket"] = pd.qcut(df["price"], q=5, labels=False, duplicates="drop") + 1
    df["waterfront_label"] = np.where(df["waterfront"] > 0, "Waterfront", "Standard")
    df["property_label"] = (
        "ID "
        + df["id"].astype(str)
        + " | "
        + df["sale_date"].dt.strftime("%Y-%m-%d")
        + " | "
        + df["zipcode"].astype(str)
        + " | "
        + (df["price"] / 1000).round().astype(int).astype(str)
        + "k | "
        + df["bedrooms"].astype(int).astype(str)
        + " ch | "
        + df["sqft_living"].astype(int).astype(str)
        + " sqft"
    )
    return df


def filter_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    st.sidebar.header("Filtres marché")

    min_date = df["sale_date"].min().date()
    max_date = df["sale_date"].max().date()
    date_range = st.sidebar.slider(
        "Période de vente",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD",
    )

    price_min, price_max = int(df["price"].min()), int(df["price"].max())
    price_range = st.sidebar.slider(
        "Fourchette de prix ($)",
        min_value=price_min,
        max_value=price_max,
        value=(price_min, price_max),
        step=25_000,
    )

    sqft_min, sqft_max = int(df["sqft_living"].min()), int(df["sqft_living"].max())
    sqft_range = st.sidebar.slider(
        "Surface habitable (sqft)",
        min_value=sqft_min,
        max_value=sqft_max,
        value=(sqft_min, sqft_max),
        step=50,
    )

    bed_range = st.sidebar.slider(
        "Chambres",
        min_value=int(df["bedrooms"].min()),
        max_value=int(df["bedrooms"].max()),
        value=(int(df["bedrooms"].min()), int(df["bedrooms"].max())),
        step=1,
    )

    bath_range = st.sidebar.slider(
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
        step=1,
    )

    condition_range = st.sidebar.slider(
        "Condition",
        min_value=int(df["condition"].min()),
        max_value=int(df["condition"].max()),
        value=(int(df["condition"].min()), int(df["condition"].max())),
        step=1,
    )

    waterfront_option = st.sidebar.selectbox("Exposition à l'eau", ["Tous", "Oui", "Non"])
    zipcodes = sorted(df["zipcode"].dropna().unique().tolist())
    selected_zipcodes = st.sidebar.multiselect(
        "Codes postaux ciblés",
        options=zipcodes,
        default=[],
        help="Laisser vide pour couvrir tout le comté.",
    )

    filtered = df[
        (df["sale_date"].dt.date >= date_range[0])
        & (df["sale_date"].dt.date <= date_range[1])
        & (df["price"] >= price_range[0])
        & (df["price"] <= price_range[1])
        & (df["sqft_living"] >= sqft_range[0])
        & (df["sqft_living"] <= sqft_range[1])
        & (df["bedrooms"] >= bed_range[0])
        & (df["bedrooms"] <= bed_range[1])
        & (df["bathrooms"] >= bath_range[0])
        & (df["bathrooms"] <= bath_range[1])
        & (df["grade"] >= grade_range[0])
        & (df["grade"] <= grade_range[1])
        & (df["condition"] >= condition_range[0])
        & (df["condition"] <= condition_range[1])
    ].copy()

    if waterfront_option == "Oui":
        filtered = filtered[filtered["waterfront"] > 0]
    elif waterfront_option == "Non":
        filtered = filtered[filtered["waterfront"] == 0]

    if selected_zipcodes:
        filtered = filtered[filtered["zipcode"].isin(selected_zipcodes)]

    filters = {
        "date_range": date_range,
        "price_range": price_range,
        "sqft_range": sqft_range,
        "bed_range": bed_range,
        "bath_range": bath_range,
        "grade_range": grade_range,
        "condition_range": condition_range,
        "waterfront_option": waterfront_option,
        "selected_zipcodes": selected_zipcodes,
    }
    return filtered, filters


def compute_market_metrics(filtered: pd.DataFrame, full_df: pd.DataFrame) -> dict[str, Any]:
    if filtered.empty:
        return {}

    monthly = (
        filtered.groupby("sale_month")
        .agg(
            transactions=("id", "count"),
            median_price=("price", "median"),
            median_ppsf=("price_per_sqft", "median"),
        )
        .reset_index()
    )

    zip_summary = (
        filtered.groupby("zipcode")
        .agg(
            transactions=("id", "count"),
            median_price=("price", "median"),
            median_ppsf=("price_per_sqft", "median"),
        )
        .sort_values(["transactions", "median_price"], ascending=[False, False])
        .reset_index()
    )

    start_window = monthly.head(min(3, len(monthly)))
    end_window = monthly.tail(min(3, len(monthly)))
    momentum = pct_change(end_window["median_price"].mean(), start_window["median_price"].mean())
    full_median_price = full_df["price"].median()
    full_median_ppsf = full_df["price_per_sqft"].median()

    return {
        "transactions": int(filtered.shape[0]),
        "median_price": float(filtered["price"].median()),
        "avg_price": float(filtered["price"].mean()),
        "median_ppsf": float(filtered["price_per_sqft"].median()),
        "median_sqft": float(filtered["sqft_living"].median()),
        "waterfront_share": float((filtered["waterfront"] > 0).mean()),
        "renovated_share": float(filtered["renovated"].mean()),
        "price_vs_county": pct_change(float(filtered["price"].median()), float(full_median_price)),
        "ppsf_vs_county": pct_change(float(filtered["price_per_sqft"].median()), float(full_median_ppsf)),
        "momentum": float(momentum),
        "monthly": monthly,
        "zip_summary": zip_summary,
        "top_zipcodes": zip_summary.head(5).to_dict(orient="records"),
        "date_min": filtered["sale_date"].min(),
        "date_max": filtered["sale_date"].max(),
    }


def render_market_overview(metrics: dict[str, Any], filtered: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="section-note">
            Cette vue combine lecture macro, segmentation géographique et signaux de pricing
            pour aider l'équipe à repérer rapidement les poches de valeur dans le comté de King.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Transactions", f"{metrics['transactions']:,}")
    col2.metric("Prix médian", format_currency(metrics["median_price"]), f"{metrics['price_vs_county']:.1%} vs comté")
    col3.metric("Prix médian / sqft", f"${metrics['median_ppsf']:.0f}", f"{metrics['ppsf_vs_county']:.1%} vs comté")
    col4.metric("Momentum prix", f"{metrics['momentum']:.1%}", "3 premiers mois vs 3 derniers")

    col5, col6, col7 = st.columns(3)
    col5.metric("Surface médiane", f"{metrics['median_sqft']:.0f} sqft")
    col6.metric("Part rénovée", format_pct(metrics["renovated_share"]))
    col7.metric("Part waterfront", format_pct(metrics["waterfront_share"]))

    left, right = st.columns((1.25, 1))
    with left:
        st.subheader("Prix médian et volume mensuel")
        st.pyplot(plot_monthly_trends(metrics["monthly"]), use_container_width=True)
    with right:
        st.subheader("Distribution des prix")
        st.pyplot(plot_price_distribution(filtered), use_container_width=True)

    lower_left, lower_right = st.columns((1, 1))
    with lower_left:
        st.subheader("Segments géographiques les plus actifs")
        st.pyplot(plot_top_zipcodes(metrics["zip_summary"]), use_container_width=True)
    with lower_right:
        st.subheader("Prix vs surface")
        st.pyplot(plot_price_vs_sqft(filtered), use_container_width=True)

    st.subheader("Transactions sous la médiane locale")
    opportunity_table = build_opportunity_table(filtered)
    st.dataframe(opportunity_table, use_container_width=True, hide_index=True)


def plot_monthly_trends(monthly: pd.DataFrame) -> plt.Figure:
    fig, ax1 = plt.subplots(figsize=(10, 4.2))
    ax2 = ax1.twinx()

    ax2.bar(
        monthly["sale_month"],
        monthly["transactions"],
        color=COLORS["mist"],
        alpha=0.65,
        width=20,
        label="Transactions",
    )
    ax1.plot(
        monthly["sale_month"],
        monthly["median_price"],
        color=COLORS["teal"],
        linewidth=2.8,
        marker="o",
        label="Prix médian",
    )

    ax1.set_ylabel("Prix médian ($)", color=COLORS["ink"])
    ax2.set_ylabel("Transactions", color=COLORS["slate"])
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: format_compact_currency(x)))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax1.tick_params(axis="x", rotation=30)
    ax1.set_title("Compression temporelle des prix et de la liquidité", loc="left", fontsize=13)

    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)
    ax2.spines["top"].set_visible(False)
    return fig


def plot_price_distribution(filtered: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.hist(filtered["price"], bins=35, color=COLORS["teal"], alpha=0.75, edgecolor="white")
    ax.axvline(filtered["price"].median(), color=COLORS["terracotta"], linestyle="--", linewidth=2, label="Médiane")
    ax.axvline(filtered["price"].mean(), color=COLORS["ink"], linestyle=":", linewidth=2, label="Moyenne")
    ax.set_xlabel("Prix de vente ($)")
    ax.set_ylabel("Nombre de transactions")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: format_compact_currency(x)))
    ax.set_title("Asymétrie du marché résidentiel", loc="left", fontsize=13)
    ax.legend(frameon=False)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    return fig


def plot_top_zipcodes(zip_summary: pd.DataFrame) -> plt.Figure:
    top = zip_summary.head(12).sort_values("median_price")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(top["zipcode"], top["median_price"], color=COLORS["teal"], alpha=0.85)
    ax.set_xlabel("Prix médian ($)")
    ax.set_ylabel("Zipcode")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: format_compact_currency(x)))
    ax.set_title("Zipcodes dominants par activité et pricing", loc="left", fontsize=13)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    return fig


def plot_price_vs_sqft(filtered: pd.DataFrame) -> plt.Figure:
    sample = filtered.sample(min(len(filtered), 3500), random_state=42)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    scatter = ax.scatter(
        sample["sqft_living"],
        sample["price"],
        c=sample["grade"],
        cmap="YlGnBu",
        alpha=0.55,
        s=36,
        edgecolors="none",
    )
    ax.set_xlabel("Surface habitable (sqft)")
    ax.set_ylabel("Prix ($)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: format_compact_currency(x)))
    ax.set_title("Prime de prix par taille et qualité", loc="left", fontsize=13)
    fig.colorbar(scatter, ax=ax, label="Grade")
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    return fig


def build_opportunity_table(filtered: pd.DataFrame) -> pd.DataFrame:
    zipcode_ppsf = filtered.groupby("zipcode")["price_per_sqft"].median().rename("zip_median_ppsf")
    opportunity_df = filtered.join(zipcode_ppsf, on="zipcode")
    opportunity_df["discount_vs_zip"] = 1 - (opportunity_df["price_per_sqft"] / opportunity_df["zip_median_ppsf"])
    shortlist = (
        opportunity_df[
            (opportunity_df["discount_vs_zip"] > 0)
            & (opportunity_df["grade"] >= 7)
            & (opportunity_df["condition"] >= 3)
        ]
        .sort_values(["discount_vs_zip", "price"], ascending=[False, True])
        .head(12)
        .copy()
    )

    if shortlist.empty:
        shortlist = opportunity_df.sort_values("price_per_sqft").head(12).copy()

    shortlist["sale_date"] = shortlist["sale_date"].dt.strftime("%Y-%m-%d")
    shortlist["price"] = shortlist["price"].map(format_currency)
    shortlist["price_per_sqft"] = shortlist["price_per_sqft"].map(lambda x: f"${x:,.0f}")
    shortlist["discount_vs_zip"] = shortlist["discount_vs_zip"].map(lambda x: f"{x:.1%}")
    shortlist["waterfront"] = shortlist["waterfront"].map({1: "Oui", 0: "Non"})

    return shortlist[
        [
            "sale_date",
            "zipcode",
            "price",
            "price_per_sqft",
            "discount_vs_zip",
            "bedrooms",
            "bathrooms",
            "sqft_living",
            "grade",
            "waterfront",
        ]
    ].rename(
        columns={
            "sale_date": "Date",
            "zipcode": "Zipcode",
            "price": "Prix",
            "price_per_sqft": "Prix / sqft",
            "discount_vs_zip": "Décote vs zipcode",
            "bedrooms": "Chambres",
            "bathrooms": "SDB",
            "sqft_living": "Surface",
            "grade": "Grade",
            "waterfront": "Waterfront",
        }
    )


def get_subject_from_existing_sales(df: pd.DataFrame) -> dict[str, Any]:
    zipcodes = sorted(df["zipcode"].unique().tolist())
    selected_zip = st.selectbox("Zipcode du bien", zipcodes, index=0)
    pool = df[df["zipcode"] == selected_zip].sort_values("sale_date", ascending=False)
    selected_label = st.selectbox("Transaction historique", pool["property_label"].tolist())
    row = pool.loc[pool["property_label"] == selected_label].iloc[0]

    return {
        "mode": "historical",
        "id": row["id"],
        "price": float(row["price"]),
        "asking_price": float(row["price"]),
        "zipcode": str(row["zipcode"]),
        "bedrooms": float(row["bedrooms"]),
        "bathrooms": float(row["bathrooms"]),
        "sqft_living": float(row["sqft_living"]),
        "sqft_lot": float(row["sqft_lot"]),
        "floors": float(row["floors"]),
        "waterfront": int(row["waterfront"]),
        "view": float(row["view"]),
        "condition": float(row["condition"]),
        "grade": float(row["grade"]),
        "yr_built": int(row["yr_built"]),
        "yr_renovated": int(row["yr_renovated"]),
        "effective_age": float(row["effective_age"]),
        "lat": float(row["lat"]),
        "long": float(row["long"]),
        "sale_date": row["sale_date"],
    }


def get_subject_from_manual_input(df: pd.DataFrame) -> dict[str, Any]:
    zipcodes = sorted(df["zipcode"].unique().tolist())
    col1, col2, col3 = st.columns(3)
    zipcode = col1.selectbox("Zipcode ciblé", zipcodes, index=0, key="manual_zipcode")
    asking_price = col2.number_input("Prix demandé ($)", min_value=0, value=650_000, step=25_000)
    sqft_living = col3.number_input("Surface habitable (sqft)", min_value=300, value=2_000, step=50)

    col4, col5, col6 = st.columns(3)
    bedrooms = col4.number_input("Chambres", min_value=0, value=3, step=1)
    bathrooms = col5.number_input("Salles de bain", min_value=0.5, value=2.5, step=0.25)
    floors = col6.number_input("Etages", min_value=1.0, value=2.0, step=0.5)

    col7, col8, col9 = st.columns(3)
    sqft_lot = col7.number_input("Terrain (sqft)", min_value=500, value=6_000, step=100)
    grade = col8.slider("Grade", min_value=3, max_value=13, value=7)
    condition = col9.slider("Condition", min_value=1, max_value=5, value=3)

    col10, col11, col12 = st.columns(3)
    waterfront = 1 if col10.selectbox("Waterfront", ["Non", "Oui"]) == "Oui" else 0
    view = col11.slider("Vue", min_value=0, max_value=4, value=0)
    yr_built = col12.number_input("Année de construction", min_value=1900, max_value=2015, value=1995, step=1)

    renovated = st.checkbox("Bien rénové", value=False)
    yr_renovated = 2010 if renovated else 0
    reference_year = int(df["sale_year"].max())
    effective_year = yr_renovated if yr_renovated > 0 else yr_built

    return {
        "mode": "manual",
        "id": "manual_subject",
        "price": float(asking_price),
        "asking_price": float(asking_price),
        "zipcode": zipcode,
        "bedrooms": float(bedrooms),
        "bathrooms": float(bathrooms),
        "sqft_living": float(sqft_living),
        "sqft_lot": float(sqft_lot),
        "floors": float(floors),
        "waterfront": int(waterfront),
        "view": float(view),
        "condition": float(condition),
        "grade": float(grade),
        "yr_built": int(yr_built),
        "yr_renovated": int(yr_renovated),
        "effective_age": float(reference_year - effective_year),
        "lat": float("nan"),
        "long": float("nan"),
        "sale_date": pd.Timestamp(year=reference_year, month=5, day=1),
    }


def find_comparables(df: pd.DataFrame, subject: dict[str, Any]) -> pd.DataFrame:
    pool = df[df["zipcode"] == subject["zipcode"]].copy()
    pool = pool[pool["id"] != subject["id"]]

    if subject["waterfront"] in (0, 1) and (pool["waterfront"] == subject["waterfront"]).sum() >= 8:
        pool = pool[pool["waterfront"] == subject["waterfront"]]

    rules = [
        {"sqft_pct": 0.20, "bed": 0, "bath": 0.5, "grade": 0, "condition": 0},
        {"sqft_pct": 0.35, "bed": 1, "bath": 1.0, "grade": 1, "condition": 1},
        {"sqft_pct": 0.50, "bed": 1, "bath": 1.5, "grade": 1, "condition": 1},
        {"sqft_pct": 0.70, "bed": 2, "bath": 2.0, "grade": 2, "condition": 2},
    ]

    subject_sqft = max(subject["sqft_living"], 1)
    selected = pool.copy()
    for rule in rules:
        candidates = pool[
            (np.abs(pool["sqft_living"] - subject["sqft_living"]) <= subject_sqft * rule["sqft_pct"])
            & (np.abs(pool["bedrooms"] - subject["bedrooms"]) <= rule["bed"])
            & (np.abs(pool["bathrooms"] - subject["bathrooms"]) <= rule["bath"])
            & (np.abs(pool["grade"] - subject["grade"]) <= rule["grade"])
            & (np.abs(pool["condition"] - subject["condition"]) <= rule["condition"])
        ].copy()
        if len(candidates) >= 8:
            selected = candidates
            break

    if selected.empty:
        selected = pool.copy()

    return score_comparables(selected, subject).head(12)


def score_comparables(comps: pd.DataFrame, subject: dict[str, Any]) -> pd.DataFrame:
    if comps.empty:
        return comps

    scoring_features = {
        "sqft_living": 0.34,
        "sqft_lot": 0.05,
        "bedrooms": 0.10,
        "bathrooms": 0.10,
        "grade": 0.14,
        "condition": 0.07,
        "floors": 0.04,
        "effective_age": 0.10,
        "view": 0.06,
    }

    scored = comps.copy()
    for feature, weight in scoring_features.items():
        scale = max(comps[feature].std(ddof=0), 1)
        scored[f"{feature}_score"] = np.abs(scored[feature] - subject[feature]) / scale * weight

    scored["distance_score"] = 0.0
    if np.isfinite(subject["lat"]) and np.isfinite(subject["long"]):
        geo_distance = np.sqrt((scored["lat"] - subject["lat"]) ** 2 + (scored["long"] - subject["long"]) ** 2)
        scored["distance_score"] = geo_distance / max(geo_distance.std(ddof=0), 0.01) * 0.08

    month_gap = np.abs((scored["sale_date"] - subject["sale_date"]).dt.days.fillna(0)) / 30
    scored["time_score"] = (month_gap / max(month_gap.std(ddof=0), 1)) * 0.06

    score_columns = [f"{feature}_score" for feature in scoring_features]
    scored["similarity_score"] = scored[score_columns + ["distance_score", "time_score"]].sum(axis=1)
    scored["weight"] = 1 / (0.15 + scored["similarity_score"])
    return scored.sort_values(["similarity_score", "sale_date"], ascending=[True, False]).copy()


def estimate_value(df: pd.DataFrame, subject: dict[str, Any], comps: pd.DataFrame) -> dict[str, Any]:
    if comps.empty:
        return {}

    weighted_ppsf = np.average(comps["price_per_sqft"], weights=comps["weight"])
    weighted_price = np.average(comps["price"], weights=comps["weight"])
    blended_estimate = 0.55 * weighted_price + 0.45 * (weighted_ppsf * subject["sqft_living"])
    price_std = comps["price"].std(ddof=0)
    uncertainty = max(0.08, min(0.20, price_std / blended_estimate if blended_estimate else 0.10))

    low = blended_estimate * (1 - uncertainty)
    high = blended_estimate * (1 + uncertainty)
    asking_price = subject["asking_price"]
    value_gap = pct_change(asking_price, blended_estimate) if blended_estimate else 0.0

    if asking_price <= low:
        stance = "Potentiellement sous-évalué"
    elif asking_price >= high:
        stance = "Prime agressive"
    else:
        stance = "Dans la fourchette"

    zipcode_slice = df[df["zipcode"] == subject["zipcode"]]
    return {
        "fair_value": float(blended_estimate),
        "value_low": float(low),
        "value_high": float(high),
        "weighted_ppsf": float(weighted_ppsf),
        "value_gap": float(value_gap),
        "stance": stance,
        "comp_count": int(comps.shape[0]),
        "zipcode_median_price": float(zipcode_slice["price"].median()),
        "zipcode_median_ppsf": float(zipcode_slice["price_per_sqft"].median()),
        "comps_avg_price": float(comps["price"].mean()),
        "comps_avg_grade": float(comps["grade"].mean()),
    }


def render_subject_summary(subject: dict[str, Any], valuation: dict[str, Any]) -> None:
    st.markdown(
        "".join(
            [
                f"<span class='property-chip'>{subject['zipcode']}</span>",
                f"<span class='property-chip'>{subject['bedrooms']:.0f} chambres</span>",
                f"<span class='property-chip'>{subject['bathrooms']:.2g} SDB</span>",
                f"<span class='property-chip'>{subject['sqft_living']:.0f} sqft</span>",
                f"<span class='property-chip'>Grade {subject['grade']:.0f}</span>",
                f"<span class='property-chip'>Condition {subject['condition']:.0f}</span>",
                f"<span class='property-chip'>{'Waterfront' if subject['waterfront'] else 'Standard'}</span>",
            ]
        ),
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Juste valeur", format_currency(valuation["fair_value"]))
    col2.metric("Fourchette", f"{format_compact_currency(valuation['value_low'])} - {format_compact_currency(valuation['value_high'])}")
    col3.metric("Prix / sqft implicite", f"${valuation['weighted_ppsf']:,.0f}")
    col4.metric("Lecture", valuation["stance"], f"{valuation['value_gap']:.1%} vs juste valeur")


def plot_comparable_scatter(comps: pd.DataFrame, subject: dict[str, Any], valuation: dict[str, Any]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.scatter(
        comps["sqft_living"],
        comps["price"],
        s=(comps["weight"] * 220),
        color=COLORS["mist"],
        edgecolor=COLORS["teal"],
        alpha=0.85,
        label="Comparables",
    )
    ax.scatter(
        [subject["sqft_living"]],
        [subject["asking_price"]],
        s=220,
        marker="*",
        color=COLORS["terracotta"],
        label="Bien analysé",
        zorder=5,
    )
    ax.axhspan(valuation["value_low"], valuation["value_high"], color=COLORS["teal"], alpha=0.08, label="Zone de valeur")
    ax.set_xlabel("Surface habitable (sqft)")
    ax.set_ylabel("Prix ($)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: format_compact_currency(x)))
    ax.set_title("Positionnement du bien face aux comparables", loc="left", fontsize=13)
    ax.legend(frameon=False)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    return fig


def render_comparable_table(comps: pd.DataFrame) -> None:
    table = comps[
        [
            "sale_date",
            "price",
            "price_per_sqft",
            "bedrooms",
            "bathrooms",
            "sqft_living",
            "grade",
            "condition",
            "similarity_score",
        ]
    ].copy()
    table["sale_date"] = table["sale_date"].dt.strftime("%Y-%m-%d")
    table["price"] = table["price"].map(format_currency)
    table["price_per_sqft"] = table["price_per_sqft"].map(lambda x: f"${x:,.0f}")
    table["similarity_score"] = table["similarity_score"].map(lambda x: f"{x:.2f}")
    st.dataframe(
        table.rename(
            columns={
                "sale_date": "Date",
                "price": "Prix",
                "price_per_sqft": "Prix / sqft",
                "bedrooms": "Chambres",
                "bathrooms": "SDB",
                "sqft_living": "Surface",
                "grade": "Grade",
                "condition": "Condition",
                "similarity_score": "Score proximité",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def get_secret_or_env(name: str) -> str:
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, "")


def call_openai_responses(api_key: str, model: str, instructions: str, prompt: str) -> str:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 600,
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()

    choices = payload.get("choices", [])
    if choices and len(choices) > 0:
        return choices[0].get("message", {}).get("content", "").strip()
    return "Erreur : aucune réponse générée."


def build_market_prompt(metrics: dict[str, Any], filters: dict[str, Any]) -> str:
    top_zip_lines = "\n".join(
        [
            f"- {item['zipcode']}: {item['transactions']} ventes, prix médian {format_currency(item['median_price'])}, prix médian/sqft ${item['median_ppsf']:.0f}"
            for item in metrics["top_zipcodes"]
        ]
    )
    return f"""
Rédige une note buy-side en français sur le marché résidentiel de King County à partir des métriques suivantes.

Période observée : {metrics['date_min']:%Y-%m-%d} au {metrics['date_max']:%Y-%m-%d}
Transactions observées : {metrics['transactions']}
Prix médian : {format_currency(metrics['median_price'])}
Prix moyen : {format_currency(metrics['avg_price'])}
Prix médian par sqft : ${metrics['median_ppsf']:.0f}
Surface médiane : {metrics['median_sqft']:.0f} sqft
Momentum des prix (3 premiers mois vs 3 derniers) : {metrics['momentum']:.1%}
Part des biens rénovés : {metrics['renovated_share']:.1%}
Part waterfront : {metrics['waterfront_share']:.1%}
Ecart de prix vs l'ensemble du comté : {metrics['price_vs_county']:.1%}

Top zipcodes :
{top_zip_lines}

Filtres actifs :
- Prix : {format_currency(filters['price_range'][0])} à {format_currency(filters['price_range'][1])}
- Surface : {filters['sqft_range'][0]} à {filters['sqft_range'][1]} sqft
- Chambres : {filters['bed_range'][0]} à {filters['bed_range'][1]}
- Salles de bain : {filters['bath_range'][0]} à {filters['bath_range'][1]}
- Waterfront : {filters['waterfront_option']}
- Zipcodes ciblés : {', '.join(filters['selected_zipcodes']) if filters['selected_zipcodes'] else 'Tous'}

Structure attendue :
1. Résumé exécutif
2. Lecture du marché
3. Risques de pricing ou de liquidité
4. Pistes d'investissement pour un fonds immobilier

N'invente aucun indicateur absent.
""".strip()


def build_property_prompt(subject: dict[str, Any], valuation: dict[str, Any], comps: pd.DataFrame) -> str:
    top_comp_lines = "\n".join(
        [
            f"- {row.sale_date:%Y-%m-%d} | prix {format_currency(row.price)} | {row.sqft_living:.0f} sqft | {row.bedrooms:.0f} ch | grade {row.grade:.0f} | score {row.similarity_score:.2f}"
            for row in comps.head(5).itertuples()
        ]
    )
    return f"""
Rédige une note d'investissement en français pour ce bien résidentiel dans King County.

Bien analysé :
- Mode : {subject['mode']}
- Zipcode : {subject['zipcode']}
- Prix demandé / prix observé : {format_currency(subject['asking_price'])}
- Surface habitable : {subject['sqft_living']:.0f} sqft
- Chambres : {subject['bedrooms']:.0f}
- Salles de bain : {subject['bathrooms']:.2g}
- Grade : {subject['grade']:.0f}
- Condition : {subject['condition']:.0f}
- Waterfront : {'Oui' if subject['waterfront'] else 'Non'}
- Vue : {subject['view']:.0f}
- Année de construction : {subject['yr_built']}

Valorisation :
- Juste valeur estimée : {format_currency(valuation['fair_value'])}
- Fourchette de valeur : {format_currency(valuation['value_low'])} à {format_currency(valuation['value_high'])}
- Prix implicite par sqft : ${valuation['weighted_ppsf']:.0f}
- Ecart du prix demandé vs juste valeur : {valuation['value_gap']:.1%}
- Lecture synthétique : {valuation['stance']}
- Nombre de comparables retenus : {valuation['comp_count']}
- Prix médian du zipcode : {format_currency(valuation['zipcode_median_price'])}
- Prix médian par sqft du zipcode : ${valuation['zipcode_median_ppsf']:.0f}

Comparables les plus proches :
{top_comp_lines}

Structure attendue :
1. Thèse d'investissement
2. Facteurs qui soutiennent la valeur
3. Points de vigilance
4. Verdict clair : acquérir, surveiller ou écarter

Reste strictement fidèle aux chiffres fournis.
""".strip()


def fallback_market_analysis(metrics: dict[str, Any]) -> str:
    direction = "haussière" if metrics["momentum"] >= 0 else "baissière"
    return f"""
### Analyse locale sans LLM

Le sous-ensemble observé couvre **{metrics['transactions']:,} transactions** entre
**{metrics['date_min']:%Y-%m-%d}** et **{metrics['date_max']:%Y-%m-%d}**.
Le **prix médian** ressort à **{format_currency(metrics['median_price'])}** et le **prix médian par sqft**
à **${metrics['median_ppsf']:.0f}**, soit **{metrics['price_vs_county']:.1%}** par rapport à l'ensemble du comté.

Le momentum récent est **{direction}** avec une variation de **{metrics['momentum']:.1%}**
entre les premiers et les derniers mois observés. La présence de biens rénovés ({metrics['renovated_share']:.1%})
et la faible part waterfront ({metrics['waterfront_share']:.1%}) suggèrent un marché surtout piloté par
la qualité intrinsèque des actifs plutôt que par les emplacements premium rares.
""".strip()


def fallback_property_analysis(subject: dict[str, Any], valuation: dict[str, Any]) -> str:
    return f"""
### Analyse locale sans LLM

Pour ce bien situé en **{subject['zipcode']}**, la juste valeur ressort à
**{format_currency(valuation['fair_value'])}** pour une fourchette de
**{format_currency(valuation['value_low'])}** à **{format_currency(valuation['value_high'])}**.

Le prix étudié de **{format_currency(subject['asking_price'])}** se situe à **{valuation['value_gap']:.1%}**
de cette juste valeur, ce qui conduit à une lecture de type **{valuation['stance']}**.
La décision finale doit ensuite être validée par la micro-localisation, l'inspection physique
et l'enveloppe de capex.
""".strip()


def render_llm_panel(
    metrics: dict[str, Any],
    filters: dict[str, Any],
    subject: dict[str, Any],
    valuation: dict[str, Any],
    comps: pd.DataFrame,
) -> None:
    st.subheader("Assistant d'analyse")
    st.caption("L'application reste fonctionnelle sans clé API grâce à un commentaire local de secours.")

    default_model = get_secret_or_env("OPENAI_MODEL") or "gpt-4o-mini"
    env_api_key = get_secret_or_env("OPENAI_API_KEY")

    col1, col2 = st.columns((1.2, 1))
    with col1:
        model = st.text_input("Modèle OpenAI", value=default_model)
    with col2:
        api_key = st.text_input(
            "Clé API OpenAI",
            value="",
            type="password",
            help="Laisser vide pour utiliser OPENAI_API_KEY si elle est définie.",
        )

    effective_api_key = api_key or env_api_key
    market_prompt = build_market_prompt(metrics, filters)
    property_prompt = build_property_prompt(subject, valuation, comps)
    system_prompt = (
        "Tu es analyste buy-side en immobilier résidentiel. "
        "Tu rédiges en français, avec un ton professionnel, concis et chiffré. "
        "Tu n'inventes aucun chiffre absent."
    )

    action1, action2 = st.columns(2)
    if action1.button("Générer une note marché", use_container_width=True):
        if effective_api_key:
            with st.spinner("Génération de la note marché..."):
                try:
                    st.session_state["market_note"] = call_openai_responses(
                        api_key=effective_api_key,
                        model=model,
                        instructions=system_prompt,
                        prompt=market_prompt,
                    )
                except requests.RequestException as exc:
                    detail = exc.response.text[:300] if getattr(exc, "response", None) is not None else str(exc)
                    st.session_state["market_note"] = f"Erreur API OpenAI: {detail}"
        else:
            st.session_state["market_note"] = fallback_market_analysis(metrics)

    if action2.button("Générer une note bien", use_container_width=True):
        if effective_api_key:
            with st.spinner("Génération de la note bien..."):
                try:
                    st.session_state["property_note"] = call_openai_responses(
                        api_key=effective_api_key,
                        model=model,
                        instructions=system_prompt,
                        prompt=property_prompt,
                    )
                except requests.RequestException as exc:
                    detail = exc.response.text[:300] if getattr(exc, "response", None) is not None else str(exc)
                    st.session_state["property_note"] = f"Erreur API OpenAI: {detail}"
        else:
            st.session_state["property_note"] = fallback_property_analysis(subject, valuation)

    note_col1, note_col2 = st.columns(2)
    with note_col1:
        st.markdown("#### Note marché")
        st.markdown(st.session_state.get("market_note", "Cliquez pour générer une synthèse du marché filtré."))
    with note_col2:
        st.markdown("#### Note bien")
        st.markdown(st.session_state.get("property_note", "Cliquez pour générer une synthèse du bien analysé."))

    with st.expander("Voir les prompts transmis au modèle"):
        st.markdown("**Prompt marché**")
        st.code(market_prompt, language="markdown")
        st.markdown("**Prompt bien**")
        st.code(property_prompt, language="markdown")


def main() -> None:
    st.set_page_config(
        page_title="King County Real Estate Lab",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()

    st.markdown(
        """
        <section class="hero">
            <div class="eyebrow">King County | Seattle Metro | Investment Research</div>
            <h1>Atlas interactif du marché résidentiel</h1>
            <p>
                Explorez 21 613 transactions historiques, repérez les zones de valeur,
                comparez un bien à son marché local et générez une note d'investissement
                assistée par IA directement depuis Streamlit.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    df = load_data()
    filtered, filters = filter_dataset(df)
    if filtered.empty:
        st.error("Aucune transaction ne correspond aux filtres actuels. Elargissez le périmètre.")
        return

    metrics = compute_market_metrics(filtered, df)
    market_tab, geo_tab, property_tab, ai_tab = st.tabs(
        ["Vue marché", "Géographie & segments", "Valorisation d'un bien", "Assistant IA"]
    )

    with market_tab:
        render_market_overview(metrics, filtered)

    with geo_tab:
        st.subheader("Cartographie d'exploration")
        map_data = filtered[["lat", "long"]].dropna()
        if not map_data.empty:
            st.map(map_data.sample(min(len(map_data), 3000), random_state=42))
        else:
            st.info("Aucune coordonnée exploitable n'est disponible pour la carte dans ce sous-ensemble.")

        left, right = st.columns(2)
        with left:
            st.subheader("Prix médian par grade")
            grade_chart = filtered.groupby("grade")["price"].median().reset_index()
            fig, ax = plt.subplots(figsize=(8, 4.2))
            ax.plot(grade_chart["grade"], grade_chart["price"], marker="o", color=COLORS["terracotta"], linewidth=2.5)
            ax.fill_between(grade_chart["grade"], grade_chart["price"], color=COLORS["terracotta"], alpha=0.12)
            ax.set_xlabel("Grade")
            ax.set_ylabel("Prix médian ($)")
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: format_compact_currency(x)))
            ax.set_title("Prime de qualité", loc="left", fontsize=13)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            st.pyplot(fig, use_container_width=True)

        with right:
            st.subheader("Liquidité par segment")
            liquidity = (
                filtered.assign(
                    size_band=pd.cut(
                        filtered["sqft_living"],
                        bins=[0, 1200, 1800, 2600, 10000],
                        labels=["Compact", "Mid-size", "Family", "Large"],
                    )
                )
                .groupby("size_band")
                .agg(transactions=("id", "count"), median_price=("price", "median"))
                .reset_index()
            )
            fig, ax = plt.subplots(figsize=(8, 4.2))
            ax.bar(liquidity["size_band"], liquidity["transactions"], color=COLORS["mist"], edgecolor=COLORS["teal"])
            ax.set_ylabel("Transactions")
            ax.set_xlabel("Segment")
            ax.set_title("Où le marché tourne le plus vite", loc="left", fontsize=13)
            ax2 = ax.twinx()
            ax2.plot(liquidity["size_band"], liquidity["median_price"], color=COLORS["teal"], linewidth=2.5, marker="o")
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: format_compact_currency(x)))
            ax2.set_ylabel("Prix médian ($)")
            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)
            st.pyplot(fig, use_container_width=True)

    subject: dict[str, Any] = {}
    comps = pd.DataFrame()
    valuation: dict[str, Any] = {}

    with property_tab:
        st.subheader("Valorisation par comparables")
        st.caption("La valorisation utilise l'historique complet du dataset pour maximiser la robustesse des comps.")
        mode = st.radio("Mode d'analyse", ["Transaction historique", "Nouveau bien"], horizontal=True)

        if mode == "Transaction historique":
            subject = get_subject_from_existing_sales(df)
        else:
            subject = get_subject_from_manual_input(df)

        comps = find_comparables(df, subject)
        if comps.empty:
            st.warning("Aucun comparable pertinent trouvé pour ce bien.")
        else:
            valuation = estimate_value(df, subject, comps)
            render_subject_summary(subject, valuation)

            left, right = st.columns((1.05, 1))
            with left:
                st.pyplot(plot_comparable_scatter(comps, subject, valuation), use_container_width=True)
            with right:
                st.markdown("#### Lecture rapide")
                st.markdown(
                    f"""
                    - **Prix observé / demandé** : {format_currency(subject['asking_price'])}
                    - **Zipcode médian** : {format_currency(valuation['zipcode_median_price'])}
                    - **Prix médian / sqft local** : ${valuation['zipcode_median_ppsf']:.0f}
                    - **Nombre de comparables** : {valuation['comp_count']}
                    - **Grade moyen des comparables** : {valuation['comps_avg_grade']:.1f}
                    - **Signal** : {valuation['stance']}
                    """
                )

            st.markdown("#### Tableau des comparables")
            render_comparable_table(comps)

    with ai_tab:
        if not subject or not valuation or comps.empty:
            st.info("Configurez d'abord un bien dans l'onglet de valorisation pour activer la note d'investissement.")
        else:
            render_llm_panel(metrics, filters, subject, valuation, comps)


if __name__ == "__main__":
    main()
