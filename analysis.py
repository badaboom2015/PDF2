import pandas as pd
import re
from typing import Dict, List, Tuple


def calculate_portfolio_stats(df: pd.DataFrame) -> Dict:
    """Calculate basic portfolio statistics."""
    df = df.copy()
    
    # Ensure numeric types
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["current_price"] = pd.to_numeric(df["current_price"], errors="coerce").fillna(0)
    df["current_value"] = pd.to_numeric(df["current_value"], errors="coerce").fillna(0)
    
    total_value = df["current_value"].sum()
    
    # Calculate weights
    df["weight_pct"] = (df["current_value"] / total_value * 100).round(2) if total_value > 0 else 0
    
    stats = {
        "total_value": round(total_value, 2),
        "num_positions": len(df),
        "top_5": get_top_n(df, 5),
        "concentration_risk": assess_concentration(df),
    }
    
    return stats, df


def get_top_n(df: pd.DataFrame, n: int = 5) -> List[Dict]:
    """Get top N positions by value."""
    top = df.nlargest(n, "current_value")[
        ["name", "ticker", "quantity", "current_price", "current_value", "weight_pct"]
    ].to_dict("records")
    return top


def guess_asset_type(name: str, ticker: str = "") -> str:
    """Simple heuristic to guess asset type."""
    name_lower = (name + " " + ticker).lower()
    
    if "option" in name_lower or "call" in name_lower or "put" in name_lower:
        return "Option"
    elif "etf" in name_lower or "ishares" in name_lower or "vanguard" in name_lower:
        return "ETF"
    elif "cash" in name_lower or "geldmarkt" in name_lower:
        return "Cash"
    else:
        return "Aktie"  # Default to stock


def assess_concentration(df: pd.DataFrame) -> Dict:
    """Assess portfolio concentration risks."""
    df = df.copy()
    
    # Add asset type if not present
    if "asset_type" not in df.columns:
        df["asset_type"] = df.apply(
            lambda row: guess_asset_type(row.get("name", ""), row.get("ticker", "")),
            axis=1
        )
    
    warnings = []
    
    # Top 5 concentration
    top_5_pct = df.nlargest(5, "current_value")["weight_pct"].sum()
    if top_5_pct > 40:
        warnings.append(f"Hohe Konzentration in Top-5: {round(top_5_pct, 1)}%")
    
    # Single position
    max_position = df["weight_pct"].max()
    if max_position > 15:
        warnings.append(f"Große Einzelposition: {round(max_position, 1)}%")
    
    # USA/Tech concentration (simple name-based heuristic)
    usa_tech_keywords = ["usa", "us ", "tech", "apple", "microsoft", "amazon", "nvidia", "tesla", "sp500"]
    usa_mask = df["name"].str.lower().str.contains("|".join(usa_tech_keywords), na=False)
    usa_pct = df[usa_mask]["weight_pct"].sum()
    
    if usa_pct > 30:
        warnings.append(f"Tech/USA Konzentration: ~{round(usa_pct, 1)}%")
    
    return {"warnings": warnings, "top_5_pct": round(top_5_pct, 1)}
