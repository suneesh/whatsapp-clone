"""Async utilities and task management for WhatsApp Client."""

import asyncio
import logging
from typing import Optional, List, Set, Callable, Any, Coroutine
from contextlib import asynccontextmanager
import inspect

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Manages background tasks for AsyncClient.
    
    Tracks all created tasks, handles cancellation, and ensures clean shutdown.
    Prevents task leaks by maintaining a registry of active tasks.
    
    Example:
        >>> manager = TaskManager()
        >>> task = await manager.create_task(my_coro())
        >>> await manager.cancel_all()
    """
    
    def __init__(self) -> None:
        """Initialize task manager."""
        self._tasks: Set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
        self._is_shutting_down = False
    
    async def create_task(
        self,
        coro: Coroutine,
        name: Optional[str] = None,
    ) -> asyncio.Task:
        """
        Create and track a background task.
        
        Args:
            coro: Coroutine to run
            name: Optional task name for debugging
            
        Returns:
            Created task object
            
        Raises:
            RuntimeError: If manager is shutting down
        """
        if self._is_shutting_down:
            raise RuntimeError("Task manager is shutting down")
        
        async with self._lock:
            task = asyncio.create_task(coro, name=name)
            self._tasks.add(task)
            
            # Remove from set when done
            task.add_done_callback(self._tasks.discard)
            
            logger.debug(f"Created task: {name or task.get_name()}")
            return task
    
    async def cancel_all(self) -> None:
        """
        Cancel all tracked tasks gracefully.
        
        Waits for all tasks to complete cancellation.
        """
        self._is_shutting_down = True
        
        async with self._lock:
            if not self._tasks:
                logger.debug("No tasks to cancel")
                return
            
            logger.info(f"Cancelling {len(self._tasks)} task(s)")
            
            # Cancel all tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for cancellation to complete
            if self._tasks:
                try:
                    await asyncio.gather(*self._tasks, return_exceptions=True)
                except asyncio.CancelledError:
                    pass
            
            self._tasks.clear()
            logger.info("All tasks cancelled")
    
    async def wait_all(self, timeout: Optional[float] = None) -> None:
        """
        Wait for all tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        async with self._lock:
            if not self._tasks:
                return
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for {len(self._tasks)} task(s)")
                raise
    
    def get_task_count(self) -> int:
        """Get number of active tasks."""
        return len(self._tasks)
    
    def is_shutting_down(self) -> bool:
        """Check if manager is shutting down."""
        return self._is_shutting_down


class EventLoopManager:
    """
    Manages event loop lifecycle and task execution.
    
    Provides utilities for:
    - Running async code from sync context
    - Creating isolated event loops
    - Handling multiple concurrent clients
    - Graceful shutdown
    
    Example:
        >>> async def client_task():
        ...     async with AsyncClient(...) as client:
        ...         await client.login(...)
        ...
        >>> asyncio.run(client_task())
    """
    
    @staticmethod
    def get_or_create_loop() -> asyncio.AbstractEventLoop:
        """
        Get current event loop or create new one.
        
        Returns:
            Event loop instance
            
        Note:
            - Returns running loop if called from async context
            - Creates new loop if none exists
            - Thread-safe for single thread
        """
        try:
            loop = asyncio.get_running_loop()
            logger.debug("Using running event loop")
            return loop
        except RuntimeError:
            # No running loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
                logger.debug("Using existing event loop")
                return loop
            except RuntimeError:
                # Create new loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.debug("Created new event loop")
                return loop
    
    @staticmethod
    async def run_concurrent(*coros: Coroutine) -> List[Any]:
        """
        Run multiple coroutines concurrently.
        
        Args:
            *coros: Coroutines to run
            
        Returns:
            List of results in order
            
        Example:
            >>> results = await run_concurrent(
            ...     client1.login(...),
            ...     client2.login(...)
            ... )
        """
        results = await asyncio.gather(*coros, return_exceptions=False)
        return results
    
    @staticmethod
    async def run_with_timeout(
        coro: Coroutine,
        timeout: float,
    ) -> Any:
        """
        Run coroutine with timeout.
        
        Args:
            coro: Coroutine to run
            timeout: Timeout in seconds
            
        Returns:
            Coroutine result
            
        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {timeout}s")
            raise
    
    @staticmethod
    async def sleep(delay: float) -> None:
        """
        Async sleep (non-blocking).
        
        Args:
            delay: Sleep duration in seconds
            
        Note:
            Always use this instead of time.sleep() in async code
        """
        await asyncio.sleep(delay)


class AsyncContextManager:
    """
    Base class for async context managers.
    
    Provides common async resource management pattern.
    Subclasses should implement:
    - async_init(): Initialize resources
    - async_cleanup(): Clean up resources
    """
    
    def __init__(self) -> None:
        """Initialize context manager."""
        self._initialized = False
        self._closed = False
    
    async def async_init(self) -> None:
        """Initialize async resources. Override in subclasses."""
        pass
    
    async def async_cleanup(self) -> None:
        """Clean up async resources. Override in subclasses."""
        pass
    
    async def __aenter__(self):
        """Enter async context."""
        if self._initialized:
            raise RuntimeError("Already initialized")
        
        await self.async_init()
        self._initialized = True
        logger.debug(f"Entered {self.__class__.__name__} context")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context and cleanup."""
        if self._closed:
            return
        
        try:
            await self.async_cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            if exc_type is None:
                raise
        
        self._closed = True
        logger.debug(f"Exited {self.__class__.__name__} context")


@asynccontextmanager
async def managed_task(
    coro: Coroutine,
    name: Optional[str] = None,
):
    """
    Context manager for background tasks.
    
    Ensures task is cancelled on exit.
    
    Args:
        coro: Coroutine to run
        name: Optional task name
        
    Example:
        >>> async with managed_task(my_coro(), name="worker") as task:
        ...     await asyncio.sleep(1)
        ... # Task automatically cancelled
    """
    task = asyncio.create_task(coro, name=name)
    logger.debug(f"Started managed task: {name or task.get_name()}")
    
    try:
        yield task
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Cancelled task: {name or task.get_name()}")


def ensure_async(func: Callable) -> Callable:
    """
    Decorator to ensure function is called from async context.
    
    Args:
        func: Async function to wrap
        
    Returns:
        Wrapped function that verifies async context
        
    Raises:
        RuntimeError: If not called from async context
        
    Example:
        >>> @ensure_async
        ... async def my_func():
        ...     pass
    """
    if not inspect.iscoroutinefunction(func):
        raise TypeError(f"{func.__name__} must be async")
    
    async def wrapper(*args, **kwargs):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError(
                f"{func.__name__}() can only be called from async context"
            )
        return await func(*args, **kwargs)
    
    return wrapper


class ExceptionHandler:
    """
    Handles exceptions in background tasks.
    
    Tracks exceptions from background tasks and provides access.
    """
    
    def __init__(self) -> None:
        """Initialize exception handler."""
        self._exceptions: List[Exception] = []
        self._lock = asyncio.Lock()
    
    async def record(self, exc: Exception) -> None:
        """
        Record an exception from background task.
        
        Args:
            exc: Exception to record
        """
        async with self._lock:
            self._exceptions.append(exc)
            logger.error(f"Recorded exception: {exc}")
    
    async def get_exceptions(self) -> List[Exception]:
        """
        Get all recorded exceptions.
        
        Returns:
            List of exceptions
        """
        async with self._lock:
            return self._exceptions.copy()
    
    async def clear_exceptions(self) -> None:
        """Clear recorded exceptions."""
        async with self._lock:
            self._exceptions.clear()
    
    def get_exception_count(self) -> int:
        """Get number of recorded exceptions."""
        return len(self._exceptions)
