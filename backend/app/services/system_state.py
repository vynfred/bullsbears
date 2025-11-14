"""
System State Management for BullsBears
Manages global system ON/OFF state via Firebase
Default state: OFF (no automated tasks run until admin turns system ON)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .push_picks_to_firebase import FirebaseService

logger = logging.getLogger(__name__)


class SystemState:
    """
    Manages global system state (ON/OFF)
    All automated tasks must check this before running
    """
    
    SYSTEM_PATH = "/system/state"
    
    @staticmethod
    async def get_state() -> Dict[str, Any]:
        """
        Get current system state from Firebase
        Returns: {
            "status": "ON" | "OFF",
            "last_updated": ISO timestamp,
            "updated_by": "admin" | "system",
            "data_primed": True | False
        }
        """
        try:
            async with FirebaseService() as fb:
                state = await fb.get_data(SystemState.SYSTEM_PATH)
                
                # If no state exists, initialize with OFF
                if not state:
                    logger.info("No system state found, initializing to OFF")
                    await SystemState.set_state("OFF", updated_by="system")
                    return {
                        "status": "OFF",
                        "last_updated": datetime.now().isoformat(),
                        "updated_by": "system",
                        "data_primed": False
                    }
                
                return state
                
        except Exception as e:
            logger.error(f"Failed to get system state: {str(e)}")
            # Fail-safe: return OFF if we can't read state
            return {
                "status": "OFF",
                "last_updated": datetime.now().isoformat(),
                "updated_by": "system",
                "data_primed": False,
                "error": str(e)
            }
    
    @staticmethod
    async def set_state(status: str, updated_by: str = "admin", data_primed: Optional[bool] = None) -> bool:
        """
        Set system state to ON or OFF
        Args:
            status: "ON" or "OFF"
            updated_by: Who triggered the change (admin, system, etc.)
            data_primed: Optional flag to update data_primed status
        Returns:
            True if successful, False otherwise
        """
        try:
            if status not in ["ON", "OFF"]:
                logger.error(f"Invalid system status: {status}")
                return False
            
            # Get current state to preserve data_primed if not specified
            current_state = await SystemState.get_state()
            
            state_data = {
                "status": status,
                "last_updated": datetime.now().isoformat(),
                "updated_by": updated_by,
                "data_primed": data_primed if data_primed is not None else current_state.get("data_primed", False)
            }
            
            async with FirebaseService() as fb:
                success = await fb.update_data(SystemState.SYSTEM_PATH, state_data)
                
                if success:
                    logger.info(f"✅ System state set to {status} by {updated_by}")
                    return True
                else:
                    logger.error(f"Failed to set system state to {status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to set system state: {str(e)}")
            return False
    
    @staticmethod
    async def is_system_on() -> bool:
        """
        Check if system is ON
        This is the method all automated tasks should call
        Returns: True if system is ON, False otherwise
        """
        try:
            state = await SystemState.get_state()
            return state.get("status") == "ON"
        except Exception as e:
            logger.error(f"Failed to check system state: {str(e)}")
            # Fail-safe: return False if we can't determine state
            return False
    
    @staticmethod
    async def mark_data_primed(primed: bool = True) -> bool:
        """
        Mark that data has been primed (90-day OHLC loaded)
        Args:
            primed: True if data is primed, False otherwise
        Returns:
            True if successful, False otherwise
        """
        try:
            current_state = await SystemState.get_state()
            current_state["data_primed"] = primed
            current_state["last_updated"] = datetime.now().isoformat()
            
            async with FirebaseService() as fb:
                success = await fb.update_data(SystemState.SYSTEM_PATH, current_state)
                
                if success:
                    logger.info(f"✅ Data primed status set to {primed}")
                    return True
                else:
                    logger.error(f"Failed to set data primed status")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to mark data primed: {str(e)}")
            return False

