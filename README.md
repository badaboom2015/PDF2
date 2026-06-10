# Depot-MVP

Kleines MVP zur Analyse von Depotauszügen (PDF/CSV).

Ziel:
- Datei einlesen (PDF oder CSV)
- Positionen erkennen
- Strukturierte Ausgabe: Wertpapier, Ticker, Stückzahl, aktueller Wert, Gewichtung, Asset-Typ
- Einfache Analyse: Depotgesamtwert, Top-5, Konzentrationshinweise
- KI-Kommentar (Open-Source Modell)
- Mini-Frontend mit Upload

Schnellstart:

1. Virtuelle Umgebung erstellen

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. App starten

```bash
export FLASK_APP=app.py
flask run
```

3. Im Browser `http://127.0.0.1:5000` öffnen
