#!/bin/bash
# update.sh -- Actualiza la app desde GitHub y reconstruye el contenedor
# Uso desde la PC: ssh admin@100.104.88.116 "cd /mnt/Luis/Finanzas && bash update.sh"

set -e

echo '>>> Pulling latest changes from GitHub...'
git pull origin main

echo '>>> Rebuilding and restarting container...'
docker compose up -d --build

echo '>>> Done. App running at http://100.104.88.116:8501'
