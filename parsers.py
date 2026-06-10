import pandas as pd
import pdfplumber
import re
import csv
from pathlib import Path
from typing import List, Dict, Tuple


def parse_csv(file_path: str) -> pd.DataFrame:
    """
    Parse CSV file with portfolio data.
    Handles Interactive Brokers statement format with multiple sections.
    """
    positions = []
    
    try:
        # Try parsing as standard CSV first
        df = pd.read_csv(file_path, nrows=5)
        if len(df.columns) > 4:
            # Likely IB format, parse specially
            return parse_ib_csv(file_path)
        else:
            return df
    except Exception:
        # Fall back to IB format parsing
        return parse_ib_csv(file_path)


def parse_ib_csv(file_path: str) -> pd.DataFrame:
    """
    Parse Interactive Brokers statement CSV format.
    Extracts "Offene Positionen" section.
    """
    positions = []
    in_open_positions = False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            
            # Check if we're entering open positions section
            if len(row) > 0 and row[0] == "Offene Positionen":
                if len(row) > 1 and row[1] == "Header":
                    in_open_positions = True
                    continue
                
                if in_open_positions and len(row) > 1:
                    # Row format: [Section, Type, Discriminator, AssetClass, Currency, Symbol, Qty, ...]
                    row_type = row[1] if len(row) > 1 else ""
                    
                    # Skip headers and totals
                    if row_type == "Data" and len(row) > 6:
                        try:
                            discriminator = row[2] if len(row) > 2 else ""
                            asset_class = row[3] if len(row) > 3 else ""
                            currency = row[4] if len(row) > 4 else ""
                            symbol = row[5] if len(row) > 5 else ""
                            
                            # Skip discriminator/summary rows or section headers
                            if discriminator == "Summary" and symbol:
                                quantity = pd.to_numeric(row[6], errors='coerce') if len(row) > 6 else 0
                                entry_price = pd.to_numeric(row[8], errors='coerce') if len(row) > 8 else 0
                                close_price = pd.to_numeric(row[10], errors='coerce') if len(row) > 10 else 0
                                value = pd.to_numeric(row[11], errors='coerce') if len(row) > 11 else 0
                                
                                if quantity != 0 or value != 0:  # Only valid positions
                                    positions.append({
                                        'name': f"{symbol} {asset_class}",
                                        'ticker': symbol,
                                        'quantity': quantity,
                                        'current_price': close_price if close_price > 0 else entry_price,
                                        'current_value': value,
                                        'asset_type': 'Option' if asset_class.lower() == 'optionen' else 'Aktie',
                                        'currency': currency,
                                    })
                        except (ValueError, IndexError):
                            pass
                    
                    elif row_type == "Total" or row_type == "SubTotal":
                        # End of section, still in positions but stop processing
                        pass
            
            # End of positions section when we hit another main section
            elif in_open_positions and len(row) > 0 and row[0] and row[0] not in ["Offene Positionen", ""]:
                if row[0] in ["Devisenpositionen", "Transaktionen", "Dividenden"]:
                    in_open_positions = False
    
    df = pd.DataFrame(positions)
    if df.empty:
        # Return empty dataframe with correct columns
        df = pd.DataFrame(columns=['name', 'ticker', 'quantity', 'current_price', 'current_value', 'asset_type'])
    
    return df


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def parse_pdf_simple(file_path: str) -> List[Dict]:
    """
    Simple heuristic-based PDF parser for portfolio statements.
    Looks for patterns like:
    - ISIN + Company name + quantity + price + value
    """
    text = extract_text_from_pdf(file_path)
    positions = []

    # Very simple pattern: lines with ISIN-like codes
    # Adjust regex based on actual portfolio statement format
    isin_pattern = r"[A-Z]{2}[A-Z0-9]{9}\d"
    
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.search(isin_pattern, line):
            # Try to extract position info from this and adjacent lines
            parts = line.split()
            if len(parts) >= 2:
                # Basic extraction; adjust based on actual format
                pos = {
                    "isin": re.search(isin_pattern, line).group(0) if re.search(isin_pattern, line) else "",
                    "name": " ".join(parts[1:5]) if len(parts) > 5 else " ".join(parts[1:]),
                    "ticker": parts[0] if parts else "",
                    "quantity": 0,
                    "current_price": 0.0,
                    "current_value": 0.0,
                }
                positions.append(pos)
    
    return positions


def standardize_positions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize portfolio dataframe columns to:
    name, ticker, quantity, current_price, current_value, asset_type
    """
    # Attempt to map common column names
    column_mapping = {
        "Wertpapier": "name",
        "Ticker": "ticker",
        "Stückzahl": "quantity",
        "Menge": "quantity",
        "Kurs": "current_price",
        "Preis": "current_price",
        "Wert": "current_value",
        "Gesamtwert": "current_value",
        "Typ": "asset_type",
        "Asset-Typ": "asset_type",
    }
    
    df.rename(columns=column_mapping, inplace=True)
    
    # Ensure required columns exist
    required = ["name", "ticker", "quantity", "current_price", "current_value"]
    for col in required:
        if col not in df.columns:
            df[col] = 0 if col in ["quantity", "current_price", "current_value"] else ""
    
    return df


def load_portfolio(file_path: str) -> pd.DataFrame:
    """Load portfolio from CSV or PDF."""
    if file_path.endswith(".csv"):
        df = parse_csv(file_path)
    elif file_path.endswith(".pdf"):
        positions = parse_pdf_simple(file_path)
        df = pd.DataFrame(positions)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")
    
    df = standardize_positions(df)
    return df
