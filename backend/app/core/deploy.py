import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def trigger_rebuild() -> None:
    hook = settings.VERCEL_DEPLOY_HOOK
    if not hook:
        return
    try:
        response = httpx.post(hook, timeout=15.0)
        response.raise_for_status()
        logger.info("Deploy hook disparado correctamente")
    except httpx.HTTPError as exc:
        logger.warning("No se pudo disparar el deploy hook: %s", exc)
