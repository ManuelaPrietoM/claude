"""
WhatsApp Daily Bot - Resumen matutino diario
============================================
Destinatario : +56997398737
Horario      : 8:00 AM hora Santiago, Chile (America/Santiago)
Estado       : DESHABILITADO — Activar BOT_ENABLED=True después de conectar
               los MCPs de WhatsApp y Google Calendar.

Datos incluidos:
  1. Precio dólar/CLP del día (mindicador.cl)
  2. Resumen bolsa americana — S&P 500, NASDAQ, Dow Jones (yfinance)
  3. Resumen política chilena (RSS → resumido por Claude Haiku)
  4. Eventos/reuniones del día (Google Calendar MCP)
"""

import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic
import feedparser
import requests
import yfinance as yf

# ─── Configuración ───────────────────────────────────────────────────────────

BOT_ENABLED   = False           # ← Cambiar a True al conectar los MCPs
WHATSAPP_TO   = "56997398737"
SANTIAGO_TZ   = ZoneInfo("America/Santiago")

# ─── Logger ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Obtención de datos
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_usd_clp() -> dict:
    """Tipo de cambio USD/CLP desde mindicador.cl (API pública, sin autenticación)."""
    try:
        r = requests.get("https://mindicador.cl/api/dolar", timeout=10)
        r.raise_for_status()
        serie = r.json().get("serie", [])
        if serie:
            return {"valor": serie[0]["valor"], "fecha": serie[0]["fecha"][:10]}
        return {"error": "Serie vacía"}
    except Exception as e:
        log.error("Error fetching USD/CLP: %s", e)
        return {"error": str(e)}


def fetch_us_market() -> dict:
    """Cierre anterior de los principales índices de EE.UU. via yfinance."""
    indices = {
        "S&P 500":   "^GSPC",
        "NASDAQ":    "^IXIC",
        "Dow Jones": "^DJI",
    }
    results = {}
    try:
        for name, symbol in indices.items():
            hist = yf.Ticker(symbol).history(period="2d")
            if len(hist) >= 2:
                prev = hist["Close"].iloc[-2]
                curr = hist["Close"].iloc[-1]
                pct  = ((curr - prev) / prev) * 100
                results[name] = {
                    "value":      round(curr, 2),
                    "change_pct": round(pct, 2),
                }
    except Exception as e:
        log.error("Error fetching market data: %s", e)
        results["error"] = str(e)
    return results


def fetch_chile_political_headlines() -> list[str]:
    """
    Titulares de política chilena desde fuentes RSS públicas.
    Filtra por palabras clave políticas.
    """
    feeds = [
        "https://www.latercera.com/feed/",
        "https://www.biobiochile.cl/lista/categorias/nacional/feed",
        "https://www.emol.com/rss/",
    ]
    keywords = {
        "gobierno", "presidente", "ministro", "ministra", "congreso", "senado",
        "diputado", "diputada", "política", "boric", "oposición", "coalición",
        "ley", "proyecto", "cámara", "plebiscito", "elección",
    }
    headlines: list[str] = []

    for url in feeds:
        try:
            for entry in feedparser.parse(url).entries:
                title = (entry.get("title") or "").strip()
                if any(kw in title.lower() for kw in keywords):
                    headlines.append(title)
                if len(headlines) >= 8:
                    break
        except Exception as e:
            log.warning("Error fetching feed %s: %s", url, e)

    return headlines[:8]


def fetch_calendar_events() -> list[str] | None:
    """
    Eventos de Google Calendar para hoy.

    STUB — Reemplazar con la llamada real al MCP de Google Calendar:

        today_start = datetime.now(SANTIAGO_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end   = today_start.replace(hour=23, minute=59, second=59)
        events = mcp.google_calendar.list_events(
            calendar_id="primary",
            time_min=today_start.isoformat(),
            time_max=today_end.isoformat(),
            single_events=True,
            order_by="startTime",
        )
        return [f"{e['start'].get('dateTime','')[:16]} – {e['summary']}" for e in events]

    Retorna None mientras el MCP no esté conectado.
    """
    # TODO: Conectar MCP de Google Calendar
    log.warning("Google Calendar MCP no conectado — omitiendo eventos")
    return None


def send_whatsapp(message: str) -> bool:
    """
    Envía el mensaje por WhatsApp al número configurado.

    STUB — Reemplazar con la llamada real al MCP de WhatsApp:

        mcp.whatsapp.send_message(
            to=WHATSAPP_TO,
            message=message,
        )
        return True

    Retorna False mientras el MCP no esté conectado.
    """
    # TODO: Conectar MCP de WhatsApp
    log.warning("WhatsApp MCP no conectado — mostrando mensaje en preview:")
    separator = "─" * 52
    print(f"\n{separator}\n{message}\n{separator}\n")
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Construcción del mensaje
# ═══════════════════════════════════════════════════════════════════════════════

def summarize_news_with_claude(headlines: list[str]) -> str:
    """
    Usa Claude Haiku para resumir los titulares políticos en ≤ 3 líneas con
    bullet points. Si no hay API key disponible, devuelve los titulares crudos.
    """
    if not headlines:
        return "• Sin titulares disponibles."

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY no configurada — usando titulares sin resumir")
        return "\n".join(f"• {h}" for h in headlines[:3])

    client = anthropic.Anthropic(api_key=api_key)
    prompt = (
        "Resume estos titulares de política chilena en MÁXIMO 3 líneas concisas. "
        "Usa bullet points (•). Solo hechos, sin opinión ni introducción:\n\n"
        + "\n".join(f"- {h}" for h in headlines)
    )
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=250,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        log.error("Error calling Claude API: %s", e)
        return "\n".join(f"• {h}" for h in headlines[:3])


def build_message(
    usd_clp: dict,
    market: dict,
    chile_summary: str,
    events: list[str] | None,
) -> str:
    """Ensambla el texto final del mensaje de WhatsApp."""
    now     = datetime.now(SANTIAGO_TZ)
    day_str = now.strftime("%-d de %B de %Y")

    lines: list[str] = [f"☀️ *Buenos días! Resumen del {day_str}*\n"]

    # ── Dólar ──
    if "valor" in usd_clp:
        lines.append(f"💵 *Dólar hoy:* ${usd_clp['valor']:,.0f} CLP")
    else:
        lines.append("💵 *Dólar:* No disponible")
    lines.append("")

    # ── Bolsa americana ──
    lines.append("📈 *Bolsa americana (cierre anterior):*")
    if market and "error" not in market:
        for name, d in market.items():
            arrow = "▲" if d["change_pct"] >= 0 else "▼"
            sign  = "+" if d["change_pct"] >= 0 else ""
            lines.append(
                f"  {arrow} {name}: {d['value']:,.2f} ({sign}{d['change_pct']:.2f}%)"
            )
    else:
        lines.append("  No disponible")
    lines.append("")

    # ── Política chilena ──
    lines.append("🇨🇱 *Política nacional:*")
    for ln in chile_summary.splitlines():
        if ln.strip():
            lines.append(f"  {ln.strip()}")
    lines.append("")

    # ── Calendario ──
    if events is not None:
        lines.append("📆 *Tus eventos de hoy:*")
        if events:
            for ev in events:
                lines.append(f"  • {ev}")
        else:
            lines.append("  Sin eventos agendados")
    else:
        lines.append("📆 _Calendario pendiente de conexión_")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Punto de entrada
# ═══════════════════════════════════════════════════════════════════════════════

def run() -> None:
    """Recopila datos, construye el mensaje y lo envía por WhatsApp."""
    if not BOT_ENABLED:
        log.info(
            "Bot DESHABILITADO. "
            "Activa BOT_ENABLED = True en daily_bot.py después de conectar "
            "los MCPs de WhatsApp y Google Calendar."
        )
        return

    log.info("Iniciando bot diario — %s", datetime.now(SANTIAGO_TZ).isoformat())

    usd_clp       = fetch_usd_clp()
    market        = fetch_us_market()
    headlines     = fetch_chile_political_headlines()
    chile_summary = summarize_news_with_claude(headlines)
    events        = fetch_calendar_events()

    message = build_message(usd_clp, market, chile_summary, events)
    sent    = send_whatsapp(message)

    if sent:
        log.info("✓ Mensaje enviado a +%s", WHATSAPP_TO)
    else:
        log.warning("✗ Mensaje no enviado (MCP no conectado)")


if __name__ == "__main__":
    run()
