import os
from flask import Flask, render_template, jsonify, request
from config import Config
import database
from routes.api import api_bp


def create_app(config_class=Config):
    """Application factory for AI Life Assistant."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize database
    database.init_app(app)
    with app.app_context():
        database.init_db()

    # Register blueprints
    app.register_blueprint(api_bp)

    # Web Views
    @app.route("/")
    def index():
        return render_template("index.html")

    # Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Endpoint not found."}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal server error."}), 500
        return render_template("500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] AI Life Assistant starting on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=app.config.get("DEBUG", False))
