"""
Launcher script for the Nifty 150 Terminal Dashboard.
Runs the Flask app via Gunicorn.
"""
import os

# Import and run the Flask app
import dashboard

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 20702))
    dashboard.app.run(host="0.0.0.0", port=port, debug=False)
