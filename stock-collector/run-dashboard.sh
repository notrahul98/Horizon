#!/bin/sh
# Wrapper script to run the Nifty 150 Terminal Dashboard
# Ensures correct PORT and PYTHONPATH

export PORT="${PORT:-5000}"
export PYTHONPATH="/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages:${PYTHONPATH}"

cd /home/runner/workspace/stock-collector
exec /home/runner/workspace/.pythonlibs/bin/python dashboard.py
