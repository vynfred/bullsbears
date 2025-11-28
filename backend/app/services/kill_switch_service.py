# backend/app/services/kill_switch_service.py
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def is_kill_switch_active(vix: float, spy_drop: float) -> bool:
    """
    Kill switch: VIX > threshold AND SPY drop > threshold
    """
    if vix > settings.KILL_SWITCH_VIX_THRESHOLD and spy_drop < -settings.KILL_SWITCH_SPY_DROP_PCT:
        logger.warning(f"KILL SWITCH ACTIVE: VIX={vix} SPY_drop={spy_drop}%")
        return True
    return False