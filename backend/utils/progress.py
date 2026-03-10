"""
Progress Tracker - SSE-based progress tracking for long-running operations
"""
import asyncio
import time
from typing import Dict, Optional, Callable, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import json
import threading


class ProgressStage(str, Enum):
    """Progress stages for project analysis"""
    UPLOADING = "uploading"
    SCANNING = "scanning"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    DEPENDENCIES = "dependencies"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ProgressState:
    """Progress state"""
    stage: ProgressStage
    progress: float  # 0-100
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "progress": round(self.progress, 1),
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event"""
        data = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"data: {data}\n\n"


class ProgressTracker:
    """
    Progress tracker for long-running operations
    Thread-safe and supports multiple listeners via callbacks
    """
    
    def __init__(self):
        self._states: Dict[str, ProgressState] = {}
        self._lock = threading.RLock()
        self._listeners: Dict[str, list] = {}  # task_id -> list of callbacks
        self._queues: Dict[str, asyncio.Queue] = {}  # task_id -> queue for SSE
    
    def create_task(self, task_id: str, initial_message: str = "Starting...") -> None:
        """Create a new progress tracking task"""
        with self._lock:
            self._states[task_id] = ProgressState(
                stage=ProgressStage.UPLOADING,
                progress=0.0,
                message=initial_message,
            )
            self._listeners[task_id] = []
            self._queues[task_id] = asyncio.Queue()
    
    def update(
        self,
        task_id: str,
        stage: Optional[ProgressStage] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update progress state"""
        with self._lock:
            if task_id not in self._states:
                return
            
            state = self._states[task_id]
            
            if stage is not None:
                state.stage = stage
            if progress is not None:
                state.progress = min(100.0, max(0.0, progress))
            if message is not None:
                state.message = message
            if details is not None:
                state.details.update(details)
            state.timestamp = time.time()
            
            # Notify listeners
            self._notify_listeners(task_id, state)
    
    def _notify_listeners(self, task_id: str, state: ProgressState) -> None:
        """Notify all listeners of state change"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Call synchronous callbacks
        for callback in self._listeners.get(task_id, []):
            try:
                callback(state)
            except Exception as e:
                logger.warning(f"Progress callback failed for task {task_id}: {e}")
        
        # Put in async queue for SSE - use call_soon_threadsafe for thread safety
        if task_id in self._queues:
            try:
                queue = self._queues[task_id]
                # Try to get running event loop
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(lambda: queue.put_nowait(state))
                except RuntimeError as e:
                    # No running loop - this is expected when called from non-async context
                    logger.debug(f"No running event loop for task {task_id}: {e}")
                except Exception as e:
                    logger.warning(f"Failed to schedule queue put for task {task_id}: {e}")
            except Exception as e:
                logger.warning(f"Failed to notify SSE queue for task {task_id}: {e}")
    
    def get_state(self, task_id: str) -> Optional[ProgressState]:
        """Get current progress state"""
        with self._lock:
            return self._states.get(task_id)
    
    def complete(self, task_id: str, message: str = "Complete") -> None:
        """Mark task as complete"""
        self.update(
            task_id,
            stage=ProgressStage.COMPLETE,
            progress=100.0,
            message=message,
        )
    
    def error(self, task_id: str, error_message: str) -> None:
        """Mark task as errored"""
        self.update(
            task_id,
            stage=ProgressStage.ERROR,
            message=error_message,
            details={"error": True},
        )
    
    def remove_task(self, task_id: str) -> None:
        """Remove task and cleanup"""
        with self._lock:
            self._states.pop(task_id, None)
            self._listeners.pop(task_id, None)
            self._queues.pop(task_id, None)
    
    def add_listener(self, task_id: str, callback: Callable[[ProgressState], None]) -> None:
        """Add a callback listener for progress updates"""
        with self._lock:
            if task_id in self._listeners:
                self._listeners[task_id].append(callback)
    
    async def progress_generator(self, task_id: str) -> AsyncGenerator[str, None]:
        """Generate SSE events for progress updates"""
        # Wait for task to be created (with timeout)
        max_wait = 30  # seconds
        wait_interval = 0.1
        elapsed = 0
        
        queue = None
        while elapsed < max_wait:
            with self._lock:
                if task_id in self._queues:
                    queue = self._queues[task_id]
                    break
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval
        
        if not queue:
            # Task not found or timed out
            yield f"data: {json.dumps({'error': 'Task not found', 'task_id': task_id})}\n\n"
            return
        
        try:
            while True:
                state = await queue.get()
                yield state.to_sse()
                
                if state.stage in (ProgressStage.COMPLETE, ProgressStage.ERROR):
                    break
        finally:
            self.remove_task(task_id)


# Global progress tracker instance
progress_tracker = ProgressTracker()
