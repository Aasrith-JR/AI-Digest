"""
Async task runner for background operations.
Uses asyncio for async task management with optional multiprocessing for CPU-bound tasks.
"""
import asyncio
import logging
from typing import Callable, Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

# Thread pool for I/O-bound operations
_thread_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gui_thread")

# Process pool for CPU-bound operations
_process_executor: Optional[ProcessPoolExecutor] = None


def get_process_executor() -> ProcessPoolExecutor:
    """Get or create process pool executor."""
    global _process_executor
    if _process_executor is None:
        _process_executor = ProcessPoolExecutor(max_workers=2)
    return _process_executor


class TaskResult:
    """Result of a background task."""

    def __init__(
        self,
        task_id: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        self.task_id = task_id
        self.success = success
        self.result = result
        self.error = error
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration = None
        if started_at and completed_at:
            self.duration = (completed_at - started_at).total_seconds()


class BackgroundTaskRunner:
    """
    Manages background tasks with async execution.
    Supports both async coroutines and sync functions.
    """

    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, TaskResult] = {}
        self._task_counter = 0

    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        self._task_counter += 1
        return f"task_{self._task_counter}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    async def run_async(
        self,
        coro: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Run an async coroutine in the background.
        Returns the task ID immediately.
        """
        task_id = task_id or self._generate_task_id()
        started_at = datetime.utcnow()

        async def wrapped_task():
            try:
                result = await coro(*args, **kwargs)
                self.results[task_id] = TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    started_at=started_at,
                    completed_at=datetime.utcnow()
                )
                logger.info(f"Task {task_id} completed successfully")
            except Exception as e:
                self.results[task_id] = TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    started_at=started_at,
                    completed_at=datetime.utcnow()
                )
                logger.error(f"Task {task_id} failed: {e}")
                logger.debug(traceback.format_exc())

        task = asyncio.create_task(wrapped_task())
        self.tasks[task_id] = task
        return task_id

    async def run_in_thread(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Run a sync function in a thread pool.
        Good for I/O-bound blocking operations.
        """
        task_id = task_id or self._generate_task_id()
        started_at = datetime.utcnow()

        async def wrapped_task():
            loop = asyncio.get_event_loop()
            try:
                # Run in thread pool
                partial_func = partial(func, *args, **kwargs)
                result = await loop.run_in_executor(_thread_executor, partial_func)
                self.results[task_id] = TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    started_at=started_at,
                    completed_at=datetime.utcnow()
                )
                logger.info(f"Thread task {task_id} completed successfully")
            except Exception as e:
                self.results[task_id] = TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    started_at=started_at,
                    completed_at=datetime.utcnow()
                )
                logger.error(f"Thread task {task_id} failed: {e}")

        task = asyncio.create_task(wrapped_task())
        self.tasks[task_id] = task
        return task_id

    async def run_in_process(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Run a sync function in a process pool.
        Good for CPU-bound operations.
        Note: func and args must be picklable.
        """
        task_id = task_id or self._generate_task_id()
        started_at = datetime.utcnow()

        async def wrapped_task():
            loop = asyncio.get_event_loop()
            try:
                executor = get_process_executor()
                partial_func = partial(func, *args, **kwargs)
                result = await loop.run_in_executor(executor, partial_func)
                self.results[task_id] = TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    started_at=started_at,
                    completed_at=datetime.utcnow()
                )
                logger.info(f"Process task {task_id} completed successfully")
            except Exception as e:
                self.results[task_id] = TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    started_at=started_at,
                    completed_at=datetime.utcnow()
                )
                logger.error(f"Process task {task_id} failed: {e}")

        task = asyncio.create_task(wrapped_task())
        self.tasks[task_id] = task
        return task_id

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the result of a completed task."""
        return self.results.get(task_id)

    def is_running(self, task_id: str) -> bool:
        """Check if a task is still running."""
        task = self.tasks.get(task_id)
        return task is not None and not task.done()

    async def wait_for(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """Wait for a task to complete and return its result."""
        task = self.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        await asyncio.wait_for(task, timeout=timeout)
        return self.results[task_id]

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self.tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def cleanup_old_results(self, max_age_seconds: float = 3600):
        """Remove results older than max_age_seconds."""
        now = datetime.utcnow()
        to_remove = []

        for task_id, result in self.results.items():
            if result.completed_at:
                age = (now - result.completed_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.results[task_id]
            if task_id in self.tasks:
                del self.tasks[task_id]

        return len(to_remove)


# Global task runner instance
task_runner = BackgroundTaskRunner()


async def run_digest_async(persona: Optional[str] = None):
    """
    Run the digest pipeline asynchronously.
    This is a background task that can be triggered from the GUI.
    """
    from services.config import load_config
    from services.database import Database
    from services.vector_store import VectorStore
    from services.digest_tracker import DigestTracker
    from services.llm import OllamaClient
    from workflows.pipeline_factory import create_pipelines_from_config
    from delivery.file_delivery import FileDelivery
    from gui.multi_user_delivery import MultiUserEmailDelivery
    from datetime import date

    config = load_config()
    today = date.today().isoformat()

    # Initialize services
    llm = OllamaClient(base_url=config.OLLAMA_BASE_URL, model=config.OLLAMA_MODEL)
    db = Database(config.DATABASE_PATH)
    vector_store = VectorStore(config.FAISS_INDEX_PATH)
    tracker = DigestTracker(db, vector_store)

    # Create pipelines
    pipelines = create_pipelines_from_config(
        pipelines_config=config.pipelines,
        llm=llm,
        tracker=tracker,
    )

    # Filter by persona if specified
    if persona:
        pipelines = [p for p in pipelines if p.name == persona]

    # Initialize delivery
    deliveries = [FileDelivery()]

    if config.EMAIL_ENABLED:
        deliveries.append(
            MultiUserEmailDelivery(
                smtp_host=config.EMAIL_SMTP_HOST,
                smtp_port=config.EMAIL_SMTP_PORT,
                username=config.EMAIL_USERNAME,
                password=config.EMAIL_PASSWORD,
                sender=config.EMAIL_FROM,
                colors=config.email_colors.model_dump(),
            )
        )

    results = []

    for pipeline in pipelines:
        try:
            entries = await pipeline.run()

            if entries:
                for delivery in deliveries:
                    await delivery.deliver(
                        persona=pipeline.name,
                        digest_date=today,
                        entries=entries,
                    )
                results.append({
                    'pipeline': pipeline.name,
                    'entries': len(entries),
                    'status': 'success'
                })
            else:
                results.append({
                    'pipeline': pipeline.name,
                    'entries': 0,
                    'status': 'no_content'
                })
        except Exception as e:
            results.append({
                'pipeline': pipeline.name,
                'status': 'error',
                'error': str(e)
            })

    return results
