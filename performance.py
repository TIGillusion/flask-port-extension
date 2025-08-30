"""
性能优化模块
提供针对密集型请求的优化功能
"""

import threading
import queue
import time
import weakref
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class RequestMetrics:
    """请求指标"""
    timestamp: float
    duration: float
    status_code: int
    app_id: str

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics: deque = deque(maxlen=window_size)
        self.lock = threading.Lock()
        
        # 统计数据
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.total_requests = 0
        self.total_errors = 0
    
    def record_request(self, app_id: str, duration: float, status_code: int):
        """记录一个请求的指标"""
        with self.lock:
            metric = RequestMetrics(
                timestamp=time.time(),
                duration=duration,
                status_code=status_code,
                app_id=app_id
            )
            self.metrics.append(metric)
            
            # 更新统计
            self.request_counts[app_id] += 1
            self.total_requests += 1
            
            if status_code >= 400:
                self.error_counts[app_id] += 1
                self.total_errors += 1
    
    def get_stats(self, app_id: Optional[str] = None) -> Dict:
        """获取统计信息"""
        with self.lock:
            if not self.metrics:
                return {"message": "暂无数据"}
            
            # 过滤指定应用的指标
            filtered_metrics = [
                m for m in self.metrics 
                if app_id is None or m.app_id == app_id
            ]
            
            if not filtered_metrics:
                return {"message": f"应用 {app_id} 暂无数据"}
            
            # 计算统计信息
            durations = [m.duration for m in filtered_metrics]
            recent_metrics = [m for m in filtered_metrics if time.time() - m.timestamp < 60]  # 最近1分钟
            
            stats = {
                "total_requests": len(filtered_metrics),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "requests_per_minute": len(recent_metrics),
                "error_rate": sum(1 for m in filtered_metrics if m.status_code >= 400) / len(filtered_metrics) * 100
            }
            
            if app_id:
                stats["app_id"] = app_id
            
            return stats

class RequestThrottler:
    """请求限流器"""
    
    def __init__(self, max_requests_per_second: int = 100, max_requests_per_app: int = 50):
        self.max_requests_per_second = max_requests_per_second
        self.max_requests_per_app = max_requests_per_app
        
        # 全局请求计数
        self.global_request_times: deque = deque()
        
        # 每个应用的请求计数
        self.app_request_times: Dict[str, deque] = defaultdict(lambda: deque())
        
        self.lock = threading.Lock()
    
    def should_allow_request(self, app_id: str) -> bool:
        """检查是否应该允许请求"""
        current_time = time.time()
        
        with self.lock:
            # 清理过期的记录（超过1秒）
            cutoff_time = current_time - 1.0
            
            # 清理全局记录
            while self.global_request_times and self.global_request_times[0] < cutoff_time:
                self.global_request_times.popleft()
            
            # 清理应用记录
            app_times = self.app_request_times[app_id]
            while app_times and app_times[0] < cutoff_time:
                app_times.popleft()
            
            # 检查是否超过限制
            if len(self.global_request_times) >= self.max_requests_per_second:
                logger.warning("全局请求频率超限")
                return False
            
            if len(app_times) >= self.max_requests_per_app:
                logger.warning(f"应用 {app_id} 请求频率超限")
                return False
            
            # 记录当前请求
            self.global_request_times.append(current_time)
            app_times.append(current_time)
            
            return True

class ConnectionPool:
    """连接池管理器"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.active_connections: Dict[str, List[weakref.ref]] = defaultdict(list)
        self.connection_count = 0
        self.lock = threading.Lock()
    
    def acquire_connection(self, app_id: str) -> bool:
        """获取连接"""
        with self.lock:
            if self.connection_count >= self.max_connections:
                logger.warning("连接池已满")
                return False
            
            self.connection_count += 1
            # 这里可以添加实际的连接对象管理
            return True
    
    def release_connection(self, app_id: str):
        """释放连接"""
        with self.lock:
            if self.connection_count > 0:
                self.connection_count -= 1

class AsyncRequestProcessor:
    """异步请求处理器"""
    
    def __init__(self, max_workers: int = 50):
        self.max_workers = max_workers
        self.executor = None
        self.running = False
    
    def start(self):
        """启动异步处理器"""
        if not self.running:
            from concurrent.futures import ThreadPoolExecutor
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            self.running = True
            logger.info(f"异步处理器启动，最大工作线程数: {self.max_workers}")
    
    def stop(self):
        """停止异步处理器"""
        if self.running and self.executor:
            self.executor.shutdown(wait=True)
            self.running = False
            logger.info("异步处理器已停止")
    
    def submit_task(self, func: Callable, *args, **kwargs):
        """提交异步任务"""
        if self.executor:
            return self.executor.submit(func, *args, **kwargs)
        else:
            logger.error("异步处理器未启动")
            return None

class PerformanceOptimizer:
    """性能优化器 - 集成所有优化功能"""
    
    def __init__(self, 
                 enable_monitoring: bool = True,
                 enable_throttling: bool = True,
                 enable_connection_pool: bool = True,
                 enable_async_processing: bool = True,
                 max_requests_per_second: int = 100,
                 max_requests_per_app: int = 50,
                 max_connections: int = 100,
                 max_workers: int = 50):
        
        self.monitor = PerformanceMonitor() if enable_monitoring else None
        self.throttler = RequestThrottler(max_requests_per_second, max_requests_per_app) if enable_throttling else None
        self.connection_pool = ConnectionPool(max_connections) if enable_connection_pool else None
        self.async_processor = AsyncRequestProcessor(max_workers) if enable_async_processing else None
        
        if self.async_processor:
            self.async_processor.start()
    
    def should_process_request(self, app_id: str) -> bool:
        """检查是否应该处理请求"""
        if self.throttler:
            return self.throttler.should_allow_request(app_id)
        return True
    
    def record_request_metrics(self, app_id: str, duration: float, status_code: int):
        """记录请求指标"""
        if self.monitor:
            self.monitor.record_request(app_id, duration, status_code)
    
    def get_performance_stats(self, app_id: Optional[str] = None) -> Dict:
        """获取性能统计"""
        if self.monitor:
            return self.monitor.get_stats(app_id)
        return {"message": "性能监控未启用"}
    
    def cleanup(self):
        """清理资源"""
        if self.async_processor:
            self.async_processor.stop()

# 全局性能优化器实例
_performance_optimizer: Optional[PerformanceOptimizer] = None
_optimizer_lock = threading.Lock()

def get_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器实例"""
    global _performance_optimizer
    
    with _optimizer_lock:
        if _performance_optimizer is None:
            _performance_optimizer = PerformanceOptimizer()
        return _performance_optimizer

def enable_performance_optimization(
    max_requests_per_second: int = 100,
    max_requests_per_app: int = 50,
    max_connections: int = 100,
    max_workers: int = 50
) -> PerformanceOptimizer:
    """启用性能优化功能"""
    global _performance_optimizer
    
    with _optimizer_lock:
        if _performance_optimizer is None:
            _performance_optimizer = PerformanceOptimizer(
                max_requests_per_second=max_requests_per_second,
                max_requests_per_app=max_requests_per_app,
                max_connections=max_connections,
                max_workers=max_workers
            )
            logger.info("性能优化已启用")
        return _performance_optimizer