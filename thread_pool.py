import threading
import queue
import time
from typing import Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkerState(Enum):
    """Enum for worker states"""
    IDLE = "idle"
    WORKING = "working"
    SHUTDOWN = "shutdown"


@dataclass
class Task:
    """Represents a task to be executed"""
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class ResilienceMetrics:
    """Thread-safe metrics collection"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._tasks_dropped = 0
    
    def increment_completed(self):
        with self._lock:
            self._tasks_completed += 1
    
    def increment_failed(self):
        with self._lock:
            self._tasks_failed += 1
    
    def increment_dropped(self):
        with self._lock:
            self._tasks_dropped += 1
    
    def get_stats(self):
        """Thread-safe read of metrics"""
        with self._lock:
            return {
                'completed': self._tasks_completed,
                'failed': self._tasks_failed,
                'dropped': self._tasks_dropped
            }


class ResilientThreadPool:
    """
    Resilient asynchronous worker thread pool with:
    - Backpressure handling via bounded queue
    - Thread-safe counter access with locks
    - Graceful handling of consumer drops
    - Worker health monitoring
    """
    
    def __init__(
        self,
        num_workers: int = 4,
        queue_size: int = 100,
        task_timeout: float = 30.0,
        worker_check_interval: float = 5.0
    ):
        """
        Initialize thread pool.
        
        Args:
            num_workers: Number of worker threads
            queue_size: Maximum queue size for backpressure
            task_timeout: Timeout for task execution
            worker_check_interval: Interval to check worker health
        """
        self.num_workers = num_workers
        self.task_timeout = task_timeout
        self.worker_check_interval = worker_check_interval
        
        # Task queue with maxsize for backpressure
        self.task_queue = queue.Queue(maxsize=queue_size)
        
        # Metrics with thread-safe access
        self.metrics = ResilienceMetrics()
        
        # Worker state tracking
        self._worker_lock = threading.Lock()
        self._worker_states = {}
        self._active_workers = set()
        
        # Shutdown signal
        self._shutdown_event = threading.Event()
        
        # Start workers
        self.workers = []
        self._start_workers()
        
        # Start health monitor
        self._monitor_thread = threading.Thread(
            target=self._monitor_workers,
            daemon=True
        )
        self._monitor_thread.start()
    
    def _start_workers(self):
        """Start all worker threads"""
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                daemon=False,
                name=f"Worker-{i}"
            )
            worker.start()
            self.workers.append(worker)
            
            with self._worker_lock:
                self._worker_states[i] = WorkerState.IDLE
                self._active_workers.add(i)
    
    def _worker_loop(self, worker_id: int):
        """Main worker loop"""
        logger.info(f"Worker {worker_id} started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get task with timeout to allow graceful shutdown checks
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Mark worker as busy
                with self._worker_lock:
                    self._worker_states[worker_id] = WorkerState.WORKING
                
                try:
                    # Execute task with timeout protection
                    result = self._execute_task_with_timeout(task)
                    self.metrics.increment_completed()
                    logger.info(f"Worker {worker_id} completed task")
                    
                except Exception as e:
                    self.metrics.increment_failed()
                    logger.error(f"Worker {worker_id} task failed: {e}")
                
                finally:
                    self.task_queue.task_done()
                    # Mark worker as idle
                    with self._worker_lock:
                        self._worker_states[worker_id] = WorkerState.IDLE
            
            except Exception as e:
                # Catastrophic error - log and continue
                logger.error(f"Worker {worker_id} encountered error: {e}")
                self.metrics.increment_dropped()
        
        logger.info(f"Worker {worker_id} shutting down")
        with self._worker_lock:
            self._worker_states[worker_id] = WorkerState.SHUTDOWN
            self._active_workers.discard(worker_id)
    
    def _execute_task_with_timeout(self, task: Task) -> Any:
        """Execute task with timeout protection"""
        try:
            # Simple timeout via threading (for CPU-bound tasks)
            result = task.func(*task.args, **task.kwargs)
            return result
        except Exception as e:
            raise e
    
    def _monitor_workers(self):
        """Monitor worker health and restart if needed"""
        while not self._shutdown_event.is_set():
            try:
                time.sleep(self.worker_check_interval)
                
                # Check for dead workers and restart if needed
                with self._worker_lock:
                    for i, worker in enumerate(self.workers):
                        if not worker.is_alive() and i in self._active_workers:
                            logger.warning(f"Worker {i} died, restarting...")
                            self.metrics.increment_dropped()
                            
                            # Restart worker
                            new_worker = threading.Thread(
                                target=self._worker_loop,
                                args=(i,),
                                daemon=False,
                                name=f"Worker-{i}-restarted"
                            )
                            new_worker.start()
                            self.workers[i] = new_worker
            
            except Exception as e:
                logger.error(f"Monitor thread error: {e}")
    
    def submit_task(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        block: bool = True,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Submit task to pool with backpressure handling.
        
        Args:
            func: Callable to execute
            args: Positional arguments
            kwargs: Keyword arguments
            block: Whether to block on full queue
            timeout: Timeout for blocking put
        
        Returns:
            True if task queued, False if rejected due to backpressure
        """
        if self._shutdown_event.is_set():
            logger.warning("Pool is shutdown, rejecting task")
            return False
        
        task = Task(func, args, kwargs)
        
        try:
            self.task_queue.put(task, block=block, timeout=timeout)
            return True
        except queue.Full:
            logger.warning("Task queue full, backpressure applied")
            self.metrics.increment_dropped()
            return False
    
    def get_queue_size(self) -> int:
        """Thread-safe read of queue size"""
        return self.task_queue.qsize()
    
    def get_metrics(self) -> dict:
        """Get thread-safe metrics snapshot"""
        return self.metrics.get_stats()
    
    def get_worker_stats(self) -> dict:
        """Get thread-safe worker statistics"""
        with self._worker_lock:
            stats = {
                'total_workers': self.num_workers,
                'active_workers': len(self._active_workers),
                'worker_states': {
                    wid: state.value 
                    for wid, state in self._worker_states.items()
                }
            }
        return stats
    
    def shutdown(self, wait: bool = True):
        """Graceful shutdown"""
        logger.info("Initiating shutdown...")
        self._shutdown_event.set()
        
        if wait:
            # Wait for queue to drain
            self.task_queue.join()
            
            # Wait for all workers to finish
            for worker in self.workers:
                worker.join(timeout=5.0)
            
            logger.info("Shutdown complete")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# Example usage
if __name__ == "__main__":
    def sample_task(task_id: int, duration: float = 0.5):
        """Sample task that simulates work"""
        time.sleep(duration)
        return f"Task {task_id} completed"
    
    def failing_task():
        """Task that fails"""
        raise ValueError("Intentional failure")
    
    # Use context manager for automatic cleanup
    with ResilientThreadPool(num_workers=4, queue_size=50) as pool:
        # Submit tasks
        for i in range(10):
            pool.submit_task(sample_task, args=(i,))
        
        # Submit some failing tasks
        for i in range(3):
            pool.submit_task(failing_task)
        
        # Submit more tasks
        for i in range(10, 15):
            pool.submit_task(sample_task, args=(i, 0.2))
        
        # Monitor progress
        time.sleep(2)
        print(f"Queue size: {pool.get_queue_size()}")
        print(f"Metrics: {pool.get_metrics()}")
        print(f"Worker stats: {pool.get_worker_stats()}")
        
        # Wait for completion
        time.sleep(5)
        print(f"Final metrics: {pool.get_metrics()}")
        print(f"Final worker stats: {pool.get_worker_stats()}")
