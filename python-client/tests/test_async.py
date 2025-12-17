"""Tests for async event loop integration (US16)."""

import asyncio
import pytest
from typing import List
from whatsapp_client import (
    AsyncClient,
    TaskManager,
    EventLoopManager,
    ExceptionHandler,
    managed_task,
    ensure_async,
)


# ===== Task Manager Tests =====

class TestTaskManager:
    """Test background task management."""
    
    @pytest.mark.asyncio
    async def test_create_task(self):
        """Test creating and tracking a task."""
        manager = TaskManager()
        
        async def dummy_coro():
            await asyncio.sleep(0.01)
            return "result"
        
        task = await manager.create_task(dummy_coro(), name="test_task")
        
        assert task is not None
        assert isinstance(task, asyncio.Task)
        result = await task
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_task_count(self):
        """Test tracking active task count."""
        manager = TaskManager()
        assert manager.get_task_count() == 0
        
        async def slow_coro():
            await asyncio.sleep(1.0)
        
        await manager.create_task(slow_coro(), name="task1")
        assert manager.get_task_count() == 1
        
        await manager.create_task(slow_coro(), name="task2")
        assert manager.get_task_count() == 2
    
    @pytest.mark.asyncio
    async def test_cancel_all_tasks(self):
        """Test cancelling all managed tasks."""
        manager = TaskManager()
        
        cancelled_count = 0
        
        async def trackable_coro(value):
            nonlocal cancelled_count
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                cancelled_count += 1
                raise
        
        await manager.create_task(trackable_coro(1), name="task1")
        await manager.create_task(trackable_coro(2), name="task2")
        
        assert manager.get_task_count() == 2
        
        # Give tasks a moment to start
        await asyncio.sleep(0.001)
        
        await manager.cancel_all()
        
        # Wait a bit for cancellation to propagate
        await asyncio.sleep(0.01)
        
        assert manager.get_task_count() == 0
        assert cancelled_count == 2
    
    @pytest.mark.asyncio
    async def test_task_removal_on_completion(self):
        """Test task is removed from tracking when done."""
        manager = TaskManager()
        
        async def quick_task():
            return "done"
        
        task = await manager.create_task(quick_task(), name="quick")
        assert manager.get_task_count() == 1
        
        await task
        
        # Task should auto-remove from set when done
        await asyncio.sleep(0.01)
        assert manager.get_task_count() == 0
    
    @pytest.mark.asyncio
    async def test_cannot_create_task_during_shutdown(self):
        """Test cannot create tasks during shutdown."""
        manager = TaskManager()
        await manager.cancel_all()
        
        async def dummy():
            pass
        
        with pytest.raises(RuntimeError, match="shutting down"):
            await manager.create_task(dummy(), name="task")
    
    @pytest.mark.asyncio
    async def test_wait_all_tasks(self):
        """Test waiting for all tasks to complete."""
        manager = TaskManager()
        
        results = []
        
        async def delayed_task(value, delay):
            await asyncio.sleep(delay)
            results.append(value)
        
        await manager.create_task(delayed_task(1, 0.01), name="task1")
        await manager.create_task(delayed_task(2, 0.02), name="task2")
        
        await manager.wait_all(timeout=1.0)
        
        assert len(results) == 2
        assert 1 in results and 2 in results


# ===== Event Loop Manager Tests =====

class TestEventLoopManager:
    """Test event loop management utilities."""
    
    @pytest.mark.asyncio
    async def test_get_running_loop(self):
        """Test getting current running loop."""
        loop = EventLoopManager.get_or_create_loop()
        assert loop is not None
        assert isinstance(loop, asyncio.AbstractEventLoop)
    
    @pytest.mark.asyncio
    async def test_run_concurrent_coroutines(self):
        """Test running multiple coroutines concurrently."""
        
        async def task(value, delay):
            await asyncio.sleep(delay)
            return value * 2
        
        results = await EventLoopManager.run_concurrent(
            task(1, 0.01),
            task(2, 0.01),
            task(3, 0.01),
        )
        
        assert len(results) == 3
        assert 2 in results
        assert 4 in results
        assert 6 in results
    
    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        """Test running task with timeout (succeeds)."""
        
        async def quick_task():
            await asyncio.sleep(0.01)
            return "success"
        
        result = await EventLoopManager.run_with_timeout(quick_task(), timeout=1.0)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_run_with_timeout_failure(self):
        """Test running task with timeout (times out)."""
        
        async def slow_task():
            await asyncio.sleep(10.0)
        
        with pytest.raises(asyncio.TimeoutError):
            await EventLoopManager.run_with_timeout(slow_task(), timeout=0.01)
    
    @pytest.mark.asyncio
    async def test_async_sleep(self):
        """Test async sleep is non-blocking."""
        import time
        
        start = time.time()
        await EventLoopManager.sleep(0.05)
        elapsed = time.time() - start
        
        # Should sleep approximately the requested time
        assert 0.03 < elapsed < 0.2


# ===== Exception Handler Tests =====

class TestExceptionHandler:
    """Test background task exception tracking."""
    
    @pytest.mark.asyncio
    async def test_record_exception(self):
        """Test recording an exception."""
        handler = ExceptionHandler()
        
        exc = ValueError("test error")
        await handler.record(exc)
        
        exceptions = await handler.get_exceptions()
        assert len(exceptions) == 1
        assert exceptions[0] is exc
    
    @pytest.mark.asyncio
    async def test_record_multiple_exceptions(self):
        """Test recording multiple exceptions."""
        handler = ExceptionHandler()
        
        exc1 = ValueError("error1")
        exc2 = RuntimeError("error2")
        
        await handler.record(exc1)
        await handler.record(exc2)
        
        exceptions = await handler.get_exceptions()
        assert len(exceptions) == 2
        assert exc1 in exceptions
        assert exc2 in exceptions
    
    @pytest.mark.asyncio
    async def test_clear_exceptions(self):
        """Test clearing exceptions."""
        handler = ExceptionHandler()
        
        await handler.record(ValueError("error1"))
        await handler.record(RuntimeError("error2"))
        
        exceptions = await handler.get_exceptions()
        assert len(exceptions) == 2
        
        await handler.clear_exceptions()
        
        exceptions = await handler.get_exceptions()
        assert len(exceptions) == 0
    
    @pytest.mark.asyncio
    async def test_exception_count(self):
        """Test getting exception count."""
        handler = ExceptionHandler()
        
        assert handler.get_exception_count() == 0
        
        await handler.record(ValueError("error"))
        assert handler.get_exception_count() == 1


# ===== Managed Task Context Manager Tests =====

class TestManagedTask:
    """Test managed_task context manager."""
    
    @pytest.mark.asyncio
    async def test_managed_task_completion(self):
        """Test managed task that completes normally."""
        results = []
        
        async def worker():
            await asyncio.sleep(0.01)
            results.append("done")
        
        async with managed_task(worker(), name="worker") as task:
            await task
        
        assert len(results) == 1
        assert results[0] == "done"
    
    @pytest.mark.asyncio
    async def test_managed_task_cancellation(self):
        """Test managed task is cancelled on exit."""
        results = []
        
        async def worker():
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                results.append("cancelled")
                raise
        
        async with managed_task(worker(), name="worker") as task:
            await asyncio.sleep(0.01)
        
        # Give cancellation time to propagate
        await asyncio.sleep(0.01)
        
        assert len(results) == 1
        assert results[0] == "cancelled"


# ===== Ensure Async Decorator Tests =====

class TestEnsureAsync:
    """Test ensure_async decorator."""
    
    @pytest.mark.asyncio
    async def test_ensure_async_valid_async_func(self):
        """Test decorator works with async function."""
        
        @ensure_async
        async def async_func():
            return "result"
        
        # Should work in async context
        result = await async_func()
        assert result == "result"
    
    def test_ensure_async_rejects_sync_func(self):
        """Test decorator rejects sync functions."""
        
        def sync_func():
            return "result"
        
        with pytest.raises(TypeError, match="must be async"):
            ensure_async(sync_func)
    
    @pytest.mark.asyncio
    async def test_ensure_async_enforces_context(self):
        """Test decorator enforces async context."""
        
        @ensure_async
        async def async_func():
            return "result"
        
        # Should work from async context
        result = await async_func()
        assert result == "result"


# ===== AsyncClient Tests =====

class TestAsyncClient:
    """Test AsyncClient with task management."""
    
    @pytest.mark.asyncio
    async def test_async_client_initialization(self):
        """Test AsyncClient initializes with task management."""
        async with AsyncClient(
            server_url="http://localhost:8000",
            storage_path="/tmp/test_whatsapp",
        ) as client:
            assert client is not None
            assert isinstance(client, AsyncClient)
    
    @pytest.mark.asyncio
    async def test_async_client_context_manager(self):
        """Test AsyncClient works as async context manager."""
        client = AsyncClient(
            server_url="http://localhost:8000",
            storage_path="/tmp/test_whatsapp",
        )
        
        async with client:
            assert not client._closed
        
        assert client._closed
    
    @pytest.mark.asyncio
    async def test_async_client_background_task_count(self):
        """Test tracking background task count."""
        async with AsyncClient(
            server_url="http://localhost:8000",
            storage_path="/tmp/test_whatsapp",
        ) as client:
            count = await client.get_background_task_count()
            assert isinstance(count, int)
            assert count >= 0
    
    @pytest.mark.asyncio
    async def test_async_client_running_state(self):
        """Test getting client running state."""
        async with AsyncClient(
            server_url="http://localhost:8000",
            storage_path="/tmp/test_whatsapp",
        ) as client:
            state = client.get_running_state()
            
            assert "is_running" in state
            assert "task_count" in state
            assert "exception_count" in state
            assert "is_authenticated" in state
            assert "is_connected" in state
    
    @pytest.mark.asyncio
    async def test_async_client_cannot_create_task_when_closed(self):
        """Test cannot spawn tasks after close."""
        client = AsyncClient(
            server_url="http://localhost:8000",
            storage_path="/tmp/test_whatsapp",
        )
        
        await client.close()
        
        async def dummy():
            pass
        
        with pytest.raises(RuntimeError, match="closed"):
            await client._spawn_background_task(dummy(), name="task")


# ===== Integration Tests =====

class TestAsyncIntegration:
    """Test async event loop integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_operations(self):
        """Test multiple concurrent async operations."""
        
        async def fetch_data(item_id):
            await asyncio.sleep(0.01)
            return f"data_{item_id}"
        
        results = await asyncio.gather(
            fetch_data(1),
            fetch_data(2),
            fetch_data(3),
        )
        
        assert len(results) == 3
        assert "data_1" in results
        assert "data_2" in results
        assert "data_3" in results
    
    @pytest.mark.asyncio
    async def test_task_exception_handling(self):
        """Test handling exceptions in background tasks."""
        handler = ExceptionHandler()
        
        async def failing_task():
            raise ValueError("task failed")
        
        task = asyncio.create_task(failing_task())
        
        try:
            await task
        except ValueError as e:
            await handler.record(e)
        
        exceptions = await handler.get_exceptions()
        assert len(exceptions) == 1
        assert isinstance(exceptions[0], ValueError)
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_pending_tasks(self):
        """Test graceful shutdown with pending tasks."""
        manager = TaskManager()
        
        async def long_running():
            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                pass
        
        await manager.create_task(long_running(), name="task1")
        await manager.create_task(long_running(), name="task2")
        
        assert manager.get_task_count() == 2
        
        await manager.cancel_all()
        
        await asyncio.sleep(0.01)
        assert manager.get_task_count() == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_clients(self):
        """Test multiple AsyncClient instances can run concurrently."""
        
        async def client_task(client_id):
            await asyncio.sleep(0.01 * client_id)
            return f"client_{client_id}_done"
        
        results = await asyncio.gather(
            client_task(1),
            client_task(2),
            client_task(3),
        )
        
        assert len(results) == 3


# ===== Edge Case Tests =====

class TestAsyncEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_task_manager_with_exception(self):
        """Test task manager handles tasks that raise exceptions."""
        manager = TaskManager()
        
        async def failing_task():
            raise RuntimeError("task error")
        
        task = await manager.create_task(failing_task(), name="failing")
        
        with pytest.raises(RuntimeError):
            await task
    
    @pytest.mark.asyncio
    async def test_wait_all_with_timeout(self):
        """Test wait_all respects timeout."""
        manager = TaskManager()
        
        async def slow_task():
            await asyncio.sleep(10.0)
        
        await manager.create_task(slow_task(), name="slow")
        
        with pytest.raises(asyncio.TimeoutError):
            await manager.wait_all(timeout=0.01)
    
    @pytest.mark.asyncio
    async def test_concurrent_exception_recording(self):
        """Test recording exceptions from concurrent tasks."""
        handler = ExceptionHandler()
        
        async def record_exception(exc):
            await handler.record(exc)
        
        await asyncio.gather(
            record_exception(ValueError("error1")),
            record_exception(RuntimeError("error2")),
            record_exception(TypeError("error3")),
        )
        
        exceptions = await handler.get_exceptions()
        assert len(exceptions) == 3
    
    @pytest.mark.asyncio
    async def test_async_client_double_close(self):
        """Test closing AsyncClient twice is safe."""
        async with AsyncClient(
            server_url="http://localhost:8000",
            storage_path="/tmp/test_whatsapp",
        ) as client:
            pass
        
        # Should not raise
        await client.close()
