import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def trigger_rebuild() -> None:
    hook = settings.rebuild_webhook_url
    if not hook:
        return
    try:
        response = httpx.post(hook, timeout=15.0)
        response.raise_for_status()
        logger.info("Webhook de reconstrucción disparado correctamente")
    except httpx.HTTPError as exc:
        logger.warning("No se pudo disparar el webhook de reconstrucción: %s", exc)
