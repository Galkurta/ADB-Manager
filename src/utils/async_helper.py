"""
Async Helper - Safe async task execution for qasync

Provides utilities to safely run async tasks without RuntimeError conflicts.
qasync has a fundamental limitation where it can't handle concurrent async tasks.
This module provides a global lock to serialize async operations.
"""

import asyncio
import logging
from typing import Coroutine, Any, Optional

logger = logging.getLogger(__name__)

# Global flag to prevent concurrent async operations
_async_busy = False


def is_async_busy() -> bool:
    """Check if an async operation is currently running"""
    return _async_busy


def safe_ensure_future(coro: Coroutine[Any, Any, Any]) -> Optional[asyncio.Task]:
    """
    Schedule an async coroutine safely.
    If another async operation is busy, the coroutine is dropped with a warning.
    
    Args:
        coro: Coroutine to schedule
        
    Returns:
        Task if scheduled successfully, None otherwise
    """
    global _async_busy
    
    if _async_busy:
        logger.debug("Dropping async task - another operation is in progress")
        # Close the coroutine to prevent warning
        coro.close()
        return None
    
    async def wrapped():
        global _async_busy
        _async_busy = True
        try:
            return await coro
        except asyncio.CancelledError:
            logger.debug("Task cancelled")
        except RuntimeError as e:
            if "Cannot enter into task" in str(e):
                logger.debug(f"Task conflict: {e}")
            else:
                logger.error(f"Runtime error: {e}")
        except Exception as e:
            logger.error(f"Task error: {e}")
        finally:
            _async_busy = False
    
    try:
        return asyncio.ensure_future(wrapped())
    except RuntimeError as e:
        logger.debug(f"Failed to schedule task: {e}")
        coro.close()
        return None
