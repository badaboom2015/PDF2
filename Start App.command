#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
# Open browser after Flask has had 1.5s to start
(sleep 1.5 && open http://localhost:8080) &
python app.py
