#!/usr/bin/env bash
set -euo pipefail

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Running Skill_HV (forwarding any extra args to main.py)..."
python main.py --candidates-dir data/candidates "$@"
