"""AsyncClient wrapper with enhanced async event loop integration."""

import asyncio
import logging
from typing import Optional, Callable, Any, List, Dict
from .client import WhatsAppClient
from .async_utils import TaskManager, ExceptionHandler

logger = logging.getLogger(__name__)


class AsyncClient(WhatsAppClient):
    """
    Enhanced WhatsApp Client with full async event loop integration.
    
    Features:
    - Background task management with leak prevention
    - Graceful shutdown with task cancellation
    - Exception tracking from background tasks
    - Multiple concurrent client support
    - Clean resource cleanup
    
    All I/O operations are fully asynchronous (no blocking calls).
    
    Example:
        >>> async with AsyncClient(server_url="...") as client:
        ...     await client.login("user", "password")
        ...     
        ...     @client.on_message
        ...     async def handle(msg):
        ...         await client.send_message(msg.from_user, f"Echo: {msg.content}")
        ...     
        ...     # Keep running
        ...     await asyncio.Event().wait()
    """
    
    def __init__(
        self,
        server_url: str,
        storage_path: str = "~/.whatsapp_client",
        auto_connect: bool = True,
        log_level: str = "INFO",
    ) -> None:
        """
        Initialize AsyncClient.
        
        Args:
            server_url: Base URL of backend
            storage_path: Path for local storage
            auto_connect: Auto-connect WebSocket on login
            log_level: Logging level
        """
        super().__init__(
            server_url=server_url,
            storage_path=storage_path,
            auto_connect=auto_connect,
            log_level=log_level,
        )
        
        # Async-specific management
        self._task_manager = TaskManager()
        self._exception_handler = ExceptionHandler()
        self._background_tasks: Dict[str, asyncio.Task] = {}
        self._is_running = False
    
    async def _spawn_background_task(
        self,
        coro,
        name: str,
    ) -> asyncio.Task:
        """
        Spawn a managed background task.
        
        Args:
            coro: Coroutine to run
            name: Task name for tracking
            
        Returns:
            Task object
            
        Raises:
            RuntimeError: If client is closed
        """
        if self._closed:
            raise RuntimeError("Cannot spawn task - client is closed")
        
        task = await self._task_manager.create_task(coro, name=name)
        self._background_tasks[name] = task
        
        # Handle task exceptions
        def exception_callback(t):
            if t.cancelled():
                return
            
            try:
                exc = t.exception()
                if exc:
                    logger.error(f"Background task error ({name}): {exc}")
                    asyncio.create_task(
                        self._exception_handler.record(exc)
                    )
            except asyncio.CancelledError:
                pass
        
        task.add_done_callback(exception_callback)
        return task
    
    async def run(self) -> None:
        """
        Run the client (keeps event loop alive).
        
        Waits for WebSocket connection and processes messages.
        Handles reconnection and background tasks.
        
        Example:
            >>> async with AsyncClient(...) as client:
            ...     await client.login("user", "password")
            ...     await client.run()
        """
        if self._is_running:
            raise RuntimeError("Client is already running")
        
        self._is_running = True
        logger.info("Client started running")
        
        try:
            # Spawn connection monitor task
            await self._spawn_background_task(
                self._monitor_connection(),
                name="connection_monitor",
            )
            
            # Keep running until closed
            while not self._closed:
                await asyncio.sleep(0.1)
                
                # Check for background task exceptions
                exceptions = await self._exception_handler.get_exceptions()
                if exceptions:
                    logger.warning(
                        f"Detected {len(exceptions)} background task exception(s)"
                    )
        
        except asyncio.CancelledError:
            logger.info("Client run cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in client run: {e}")
            raise
        finally:
            self._is_running = False
            logger.info("Client stopped running")
    
    async def _monitor_connection(self) -> None:
        """
        Monitor WebSocket connection status.
        
        Handles reconnection with exponential backoff.
        """
        reconnect_delay = 1.0
        max_delay = 60.0
        
        try:
            while not self._closed:
                # Check connection status
                if not self.is_connected and self.is_authenticated:
                    logger.debug("Attempting to reconnect")
                    try:
                        await self._connect_websocket()
                        reconnect_delay = 1.0  # Reset on success
                    except Exception as e:
                        logger.debug(f"Reconnection failed: {e}")
                        await asyncio.sleep(reconnect_delay)
                        reconnect_delay = min(reconnect_delay * 2, max_delay)
                else:
                    # Connection is good or not authenticated
                    await asyncio.sleep(1.0)
        
        except asyncio.CancelledError:
            logger.debug("Connection monitor cancelled")
            raise
    
    async def close(self) -> None:
        """
        Close client and cancel all background tasks.
        
        Ensures clean shutdown with:
        - All background tasks cancelled
        - WebSocket disconnected
        - Resources cleaned up
        - No task leaks
        """
        if self._closed:
            return
        
        logger.info("Closing AsyncClient with task cleanup")
        
        try:
            # Cancel all background tasks
            logger.debug(
                f"Cancelling {self._task_manager.get_task_count()} task(s)"
            )
            await self._task_manager.cancel_all()
            self._background_tasks.clear()
            
            # Call parent close
            await super().close()
        
        except Exception as e:
            logger.error(f"Error during close: {e}")
            raise
    
    async def get_background_task_count(self) -> int:
        """
        Get number of active background tasks.
        
        Returns:
            Number of tasks
        """
        return self._task_manager.get_task_count()
    
    async def get_background_exceptions(self) -> List[Exception]:
        """
        Get all exceptions from background tasks.
        
        Returns:
            List of exceptions
        """
        return await self._exception_handler.get_exceptions()
    
    async def clear_background_exceptions(self) -> None:
        """Clear recorded background task exceptions."""
        await self._exception_handler.clear_exceptions()
    
    def get_running_state(self) -> Dict[str, Any]:
        """
        Get current running state for monitoring.
        
        Returns:
            Dictionary with:
            - is_running: Whether client is actively running
            - task_count: Number of background tasks
            - exception_count: Number of recorded exceptions
            - is_authenticated: Authentication status
            - is_connected: WebSocket connection status
        """
        return {
            "is_running": self._is_running,
            "task_count": self._task_manager.get_task_count(),
            "exception_count": self._exception_handler.get_exception_count(),
            "is_authenticated": self.is_authenticated,
            "is_connected": self.is_connected,
        }
    
    async def wait_all_tasks(self, timeout: Optional[float] = None) -> None:
        """
        Wait for all background tasks to complete.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        await self._task_manager.wait_all(timeout=timeout)
