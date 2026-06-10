import pandas as pd
from typing import Dict, List


def calculate_portfolio_stats(df: pd.DataFrame) -> tuple:
    """Calculate portfolio statistics."""
    df = df.copy()

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["current_price"] = pd.to_numeric(df["current_price"], errors="coerce").fillna(0)
    df["current_value"] = pd.to_numeric(df["current_value"], errors="coerce").fillna(0)

    total_value = df["current_value"].sum()
    df["weight_pct"] = (df["current_value"] / total_value * 100).round(2) if total_value > 0 else 0.0

    if "asset_type" not in df.columns:
        df["asset_type"] = df.apply(
            lambda row: guess_asset_type(row.get("name", ""), row.get("ticker", "")), axis=1
        )

    stats = {
        "total_value": round(float(total_value), 2),
        "num_positions": int(len(df)),
        "top_5": get_top_n(df, 5),
        "concentration_risk": assess_concentration(df),
        "asset_breakdown": get_asset_breakdown(df),
    }

    return stats, df


def get_top_n(df: pd.DataFrame, n: int = 5) -> List[Dict]:
    """Get top N positions by value."""
    cols = ["name", "ticker", "quantity", "current_price", "current_value", "weight_pct"]
    return df.nlargest(n, "current_value")[cols].to_dict("records")


def guess_asset_type(name: str, ticker: str = "") -> str:
    """Heuristic asset type detection."""
    combined = (name + " " + ticker).lower()

    if any(k in combined for k in ("option", " call ", " put ", "warrant")):
        return "Option"

    if any(k in combined for k in (
        "etf", "ishares", "vanguard", "xtrackers", "amundi", "lyxor", "spdr",
        "wisdomtree", "invesco", "ubs etf", "deka etf", "comstage", "ucits",
        "index fund", "indexfonds",
    )):
        return "ETF"

    if any(k in combined for k in (
        "anleihe", "bond", "rente", "treasury", "bund", "pfandbrief",
        "note ", "notes", "schuldverschreibung",
    )):
        return "Anleihe"

    if any(k in combined for k in (
        "reit", "realty", "immobilien fonds", "property trust",
    )):
        return "REIT"

    if any(k in combined for k in (
        "gold", "silver", "silber", "rohstoff", "commodity", "öl", "oil",
        "euwax gold", "xetra-gold",
    )):
        return "Rohstoff"

    if any(k in combined for k in (
        "cash", "geldmarkt", "money market", "liquidity",
    )):
        return "Cash"

    return "Aktie"


def get_asset_breakdown(df: pd.DataFrame) -> Dict:
    """Return percentage split by asset type."""
    total = df["current_value"].sum()
    if total == 0:
        return {}
    grouped = df.groupby("asset_type")["current_value"].sum()
    return {
        asset: round(float(value / total * 100), 1)
        for asset, value in grouped.items()
    }


def assess_concentration(df: pd.DataFrame) -> Dict:
    """Assess portfolio concentration risks."""
    df = df.copy()
    warnings = []

    # Top-5 concentration
    top5 = df.nlargest(5, "current_value")
    top5_pct = float(top5["weight_pct"].sum())
    if top5_pct > 40:
        warnings.append(f"Hohe Konzentration in Top-5: {round(top5_pct, 1)}%")

    # Single position > 15 %
    max_weight = float(df["weight_pct"].max())
    max_name = df.loc[df["weight_pct"].idxmax(), "name"] if len(df) > 0 else ""
    if max_weight > 15:
        warnings.append(f"Große Einzelposition '{max_name}': {round(max_weight, 1)}%")

    # USA / Tech concentration
    usa_tech_keywords = [
        "usa", "us ", "s&p", "sp500", "nasdaq", "dow jones",
        "tech", "technology", "technologie",
        "apple", "microsoft", "amazon", "nvidia", "tesla",
        "alphabet", "google", "meta", "netflix",
    ]
    mask = df["name"].str.lower().str.contains("|".join(usa_tech_keywords), na=False)
    usa_pct = float(df[mask]["weight_pct"].sum())
    if usa_pct > 30:
        warnings.append(f"Tech-/USA-Konzentration: ~{round(usa_pct, 1)}%")

    # Options as share of total (risk exposure)
    if "asset_type" in df.columns:
        option_pct = float(df[df["asset_type"] == "Option"]["weight_pct"].sum())
        if option_pct > 10:
            warnings.append(f"Hoher Optionsanteil: {round(option_pct, 1)}%")

    return {
        "warnings": warnings,
        "top_5_pct": round(top5_pct, 1),
        "max_single_pct": round(max_weight, 1),
        "usa_tech_pct": round(usa_pct, 1),
    }
