from typing import Dict, List
import pandas as pd


def generate_portfolio_comment(stats: Dict, df_positions: pd.DataFrame, concentration_risk: Dict) -> str:
    """Generate an educational portfolio commentary in German. No investment advice."""
    total_value = stats["total_value"]
    num_positions = stats["num_positions"]
    top5_pct = concentration_risk.get("top_5_pct", 0)
    max_single = concentration_risk.get("max_single_pct", 0)
    usa_tech = concentration_risk.get("usa_tech_pct", 0)
    warnings = concentration_risk.get("warnings", [])
    asset_breakdown: Dict = stats.get("asset_breakdown", {})

    lines: List[str] = []

    lines.append(
        f"Das Portfolio umfasst {num_positions} Positionen mit einem Gesamtwert von "
        f"{total_value:,.2f} EUR."
    )

    if asset_breakdown:
        breakdown_text = ", ".join(
            f"{atype} {pct}%" for atype, pct in sorted(asset_breakdown.items(), key=lambda x: -x[1])
        )
        lines.append(f"Asset-Mix: {breakdown_text}.")

    if top5_pct > 0:
        lines.append(f"Die Top‑5 Positionen binden {top5_pct}% des Depotvermögens.")

    if max_single > 15:
        lines.append(
            f"Die größte Einzelposition macht {max_single}% aus – "
            "das übersteigt die übliche Faustregel von 15% je Position."
        )

    if usa_tech > 30:
        lines.append(
            f"Rund {usa_tech}% des Portfolios entfallen auf US-amerikanische oder Tech-Werte. "
            "Währungs- und Sektorrisiken sind zu beachten."
        )

    if warnings:
        lines.append("Weitere Hinweise: " + "; ".join(warnings) + ".")

    lines.append(
        "Diese Auswertung dient ausschließlich der Information und stellt keine Anlageberatung dar."
    )

    return " ".join(lines)
