"""
Scheduler del WhatsApp Daily Bot
=================================
Ejecuta daily_bot.run() todos los días a las 08:00 AM hora Santiago (America/Santiago).

Uso:
    python scheduler.py            # Inicia el scheduler en primer plano
    python scheduler.py --test     # Ejecuta el bot ahora mismo (para probar datos)
    python scheduler.py --preview  # Muestra el mensaje sin enviar (ignora BOT_ENABLED)
"""

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import daily_bot

log = logging.getLogger(__name__)
SANTIAGO_TZ = ZoneInfo("America/Santiago")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # ── Modo --preview: muestra el mensaje ignorando BOT_ENABLED ──────────────
    if "--preview" in sys.argv:
        print("Modo PREVIEW — generando mensaje de muestra (no se envía)...\n")
        usd_clp       = daily_bot.fetch_usd_clp()
        market        = daily_bot.fetch_us_market()
        headlines     = daily_bot.fetch_chile_political_headlines()
        chile_summary = daily_bot.summarize_news_with_claude(headlines)
        events        = daily_bot.fetch_calendar_events()
        msg           = daily_bot.build_message(usd_clp, market, chile_summary, events)
        print(msg)
        return

    # ── Modo --test: ejecuta run() inmediatamente ─────────────────────────────
    if "--test" in sys.argv:
        print("Modo TEST — ejecutando bot ahora mismo...")
        daily_bot.run()
        return

    # ── Modo normal: scheduler bloqueante ────────────────────────────────────
    scheduler = BlockingScheduler(timezone=str(SANTIAGO_TZ))
    scheduler.add_job(
        daily_bot.run,
        trigger=CronTrigger(hour=8, minute=0, timezone=str(SANTIAGO_TZ)),
        id="whatsapp_daily_bot",
        name="WhatsApp Daily Briefing 8 AM Santiago",
        misfire_grace_time=300,   # 5 min de gracia si el proceso estaba caído
        coalesce=True,            # no acumular disparos perdidos
    )

    next_run = scheduler.get_jobs()[0].next_run_time
    log.info("Scheduler iniciado.")
    log.info("Próxima ejecución: %s", next_run)
    log.info("Presiona Ctrl+C para detener.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler detenido.")


if __name__ == "__main__":
    main()
