"""
Simple AI commentary using a lightweight open-source model.
Uses transformers/pipeline for zero-shot or summarization tasks.
"""

from typing import Dict, List


def generate_portfolio_comment(
    stats: Dict,
    df_positions,
    concentration_risk: Dict
) -> str:
    """
    Generate a simple educational comment about the portfolio.
    No investment advice, just educational observations.
    """
    total_value = stats["total_value"]
    num_positions = stats["num_positions"]
    top_5_pct = concentration_risk.get("top_5_pct", 0)
    warnings = concentration_risk.get("warnings", [])
    
    # Build observation text
    observations = []
    
    observations.append(
        f"Das Portfolio hat einen Gesamtwert von {total_value:,.2f} EUR "
        f"mit {num_positions} Positionen."
    )
    
    if top_5_pct > 0:
        observations.append(
            f"Die Top-5-Positionen machen {top_5_pct}% des Portfolios aus."
        )
    
    if warnings:
        observations.append("Hinweise auf Konzentration: " + "; ".join(warnings))
    
    # Asset type breakdown (simple stats)
    if "asset_type" in df_positions.columns:
        asset_counts = df_positions["asset_type"].value_counts().to_dict()
        type_text = ", ".join([f"{k}: {v}" for k, v in asset_counts.items()])
        observations.append(f"Asset-Typen: {type_text}")
    
    observations.append(
        "Dies ist eine reine Analyse ohne Anlageberatung. "
        "Für konkrete Entscheidungen konsultieren Sie einen Fachberater."
    )
    
    return " ".join(observations)


def simple_summary_with_transformers(comment: str) -> str:
    """
    Optional: use transformers summarization pipeline for further processing.
    Falls back to original comment if model not available.
    """
    try:
        from transformers import pipeline
        
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        summary = summarizer(comment, max_length=100, min_length=50, do_sample=False)
        return summary[0]["summary_text"]
    except Exception as e:
        print(f"Summarization not available: {e}")
        return comment
