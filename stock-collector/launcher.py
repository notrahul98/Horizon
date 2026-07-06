"""
Launcher script for the Nifty 150 Terminal Dashboard.
Sets up Python path and runs the Flask app via Gunicorn.
"""
import sys
import os

# Ensure venv packages are available
_venv_site = "/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages"
if os.path.isdir(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

# Import and run the Flask app
import dashboard

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 20702))
    dashboard.app.run(host="0.0.0.0", port=port, debug=False)
