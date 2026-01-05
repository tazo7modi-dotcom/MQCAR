#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Creating persistent directory..."

mkdir -p /var/data

echo "Applying Database Migrations..."

flask db upgrade