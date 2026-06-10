import os
import json
import numpy as np
from flask import Flask, render_template, request, jsonify
from flask.json.provider import DefaultJSONProvider
from werkzeug.utils import secure_filename

from parsers import load_portfolio
from analysis import calculate_portfolio_stats, guess_asset_type
from ai_comment import generate_portfolio_comment


class NumpyJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


app = Flask(__name__)
app.json_provider_class = NumpyJSONProvider
app.json = NumpyJSONProvider(app)
app.config["UPLOAD_FOLDER"] = "/tmp"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {"csv", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Handle file upload and generate portfolio analysis."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Nur CSV oder PDF Dateien erlaubt"}), 400
    
    try:
        # Save and process file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        
        # Parse portfolio
        df = load_portfolio(filepath)
        
        # Add asset type if missing
        if "asset_type" not in df.columns:
            df["asset_type"] = df.apply(
                lambda row: guess_asset_type(
                    row.get("name", ""),
                    row.get("ticker", "")
                ),
                axis=1
            )
        
        # Calculate stats
        stats, df_with_weights = calculate_portfolio_stats(df)
        
        # Generate AI comment
        ai_comment = generate_portfolio_comment(
            stats,
            df_with_weights,
            stats["concentration_risk"]
        )
        
        # Prepare response
        response = {
            "total_value": stats["total_value"],
            "num_positions": stats["num_positions"],
            "top_5": stats["top_5"],
            "concentration_warnings": stats["concentration_risk"]["warnings"],
            "concentration_risk": stats["concentration_risk"],
            "asset_breakdown": stats["asset_breakdown"],
            "ai_comment": ai_comment,
            "positions": df_with_weights[
                ["name", "ticker", "quantity", "current_price", "current_value", "weight_pct", "asset_type"]
            ].to_dict("records"),
        }
        
        # Cleanup
        os.remove(filepath)
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
