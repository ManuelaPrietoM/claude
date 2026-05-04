#!/usr/bin/env bash
# setup_cron.sh — Instala el bot como cron job (alternativa robusta a scheduler.py)
#
# Uso:
#   bash setup_cron.sh install    # Instala el cron job (deshabilitado por defecto)
#   bash setup_cron.sh remove     # Elimina el cron job
#   bash setup_cron.sh status     # Muestra el cron job activo
#
# El cron job está comentado hasta que ejecutes `bash setup_cron.sh install`
# y luego edites el crontab para descomentar la línea.

set -euo pipefail

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(command -v python3)"
LOG_FILE="$BOT_DIR/bot.log"
CRON_MARKER="# whatsapp-daily-bot"

# Cron: 8:00 AM hora Santiago = TZ=America/Santiago
CRON_LINE="TZ=America/Santiago 0 8 * * * $PYTHON $BOT_DIR/daily_bot.py >> $LOG_FILE 2>&1  $CRON_MARKER"

case "${1:-help}" in
  install)
    # Agrega solo si no existe ya
    if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
      echo "El cron job ya existe:"
      crontab -l | grep "$CRON_MARKER"
    else
      (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
      echo "Cron job instalado:"
      crontab -l | grep "$CRON_MARKER"
      echo ""
      echo "NOTA: El bot sigue deshabilitado (BOT_ENABLED=False en daily_bot.py)."
      echo "Actívalo después de conectar los MCPs de WhatsApp y Google Calendar."
    fi
    ;;
  remove)
    if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
      crontab -l | grep -vF "$CRON_MARKER" | crontab -
      echo "Cron job eliminado."
    else
      echo "No se encontró cron job con marker '$CRON_MARKER'."
    fi
    ;;
  status)
    echo "=== Cron jobs activos ==="
    crontab -l 2>/dev/null || echo "(ninguno)"
    echo ""
    echo "=== Últimas 20 líneas del log ==="
    [ -f "$LOG_FILE" ] && tail -20 "$LOG_FILE" || echo "(sin log todavía)"
    ;;
  *)
    echo "Uso: bash setup_cron.sh [install|remove|status]"
    ;;
esac
