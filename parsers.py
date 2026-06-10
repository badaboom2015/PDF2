import pandas as pd
import pdfplumber
import re
import csv
from typing import List, Dict


def _to_float(value: str) -> float:
    """Convert a string number (possibly with thousands commas) to float."""
    try:
        return float(str(value).replace(',', ''))
    except (ValueError, AttributeError):
        return 0.0


def parse_csv(file_path: str) -> pd.DataFrame:
    """Detect CSV format by inspecting the first line, then dispatch."""
    # utf-8-sig strips BOM if present (common in Windows/IB exports)
    with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
        first_line = f.readline()

    if first_line.startswith("Statement,"):
        return parse_ib_csv(file_path)

    try:
        return pd.read_csv(file_path)
    except Exception:
        return parse_ib_csv(file_path)


def parse_ib_csv(file_path: str) -> pd.DataFrame:
    """
    Parse Interactive Brokers statement CSV (German locale), two-pass.

    Devisenpositionen columns (0-indexed):
      0 Section  1 RowType  2 Category  3 BaseCurrency  4 FxCurrency
      5 Amount   6 EntryRate 7 CostBasisEUR  8 CloseRate  9 ValueEUR

    Offene Positionen columns (0-indexed):
      0 Section  1 RowType  2 Discriminator  3 AssetClass  4 Currency
      5 Symbol   6 Quantity  7 Multiplier  8 EntryPrice  9 CostBasis
      10 ClosePrice  11 Value
    """
    positions: List[Dict] = []
    fx_rates: Dict[str, float] = {}  # currency → EUR conversion factor

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        rows = list(csv.reader(f))

    # ── Pass 1: collect FX rates from Devisenpositionen ──────────────────────
    in_fx = False
    for row in rows:
        if not row:
            continue
        if row[0] == "Devisenpositionen":
            if len(row) > 1 and row[1] == "Header":
                in_fx = True
                continue
            if in_fx and len(row) > 8 and row[1] == "Data":
                currency = row[4].strip()          # e.g. "USD"
                rate = _to_float(row[8])            # Schlusskurs = EUR per 1 unit
                if currency and currency != "EUR" and rate != 0.0:
                    fx_rates[currency] = rate
        elif in_fx:
            in_fx = False                           # any new section ends fx block

    # ── Pass 2: parse Offene Positionen ──────────────────────────────────────
    in_pos = False
    for row in rows:
        if not row:
            continue
        if row[0] == "Offene Positionen":
            row_type = row[1] if len(row) > 1 else ""
            if row_type == "Header":
                in_pos = True
                continue
            if not in_pos or row_type != "Data" or len(row) < 12:
                continue
            if row[2] != "Summary" or not row[5].strip():
                continue

            symbol = row[5].strip()
            asset_class = row[3].strip()
            currency = row[4].strip()

            quantity = _to_float(row[6])
            entry_price = _to_float(row[8])
            close_price = _to_float(row[10])
            value = _to_float(row[11])

            if quantity == 0.0 and value == 0.0:
                continue

            fx = fx_rates.get(currency, 1.0) if currency != "EUR" else 1.0
            is_option = asset_class.lower() in ("optionen", "options", "option")

            positions.append({
                'name': symbol,
                'ticker': symbol,
                'quantity': quantity,
                'current_price': round((close_price if close_price != 0.0 else entry_price) * fx, 4),
                'current_value': round(value * fx, 2),
                'asset_type': "Option" if is_option else "Aktie",
                'currency': currency,
            })
        elif in_pos:
            in_pos = False                          # any new section ends positions block

    if not positions:
        return pd.DataFrame(
            columns=['name', 'ticker', 'quantity', 'current_price', 'current_value', 'asset_type']
        )
    return pd.DataFrame(positions)


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
