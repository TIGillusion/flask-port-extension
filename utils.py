"""
工具函数模块
"""

import json
import time
import logging
from typing import Dict, Any, Optional
from flask import Flask
from .port_sharing import get_master_server_status

logger = logging.getLogger(__name__)

def validate_app_prefix(prefix: str) -> str:
    """验证和标准化应用前缀"""
    if not prefix:
        return ""
    
    # 确保以/开头
    if not prefix.startswith('/'):
        prefix = '/' + prefix
    
    # 移除末尾的/
    if prefix.endswith('/') and len(prefix) > 1:
        prefix = prefix[:-1]
    
    return prefix

def check_master_server_health(host: str = '127.0.0.1', port: int = 5000, timeout: int = 5) -> bool:
    """检查主控服务器是否健康"""
    try:
        import requests
        response = requests.get(f"http://{host}:{port}/_master/health", timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"检查主控服务器健康状态失败: {e}")
        return False

def wait_for_master_server(host: str = '127.0.0.1', port: int = 5000, 
                          max_wait_time: int = 30, check_interval: float = 0.5) -> bool:
    """等待主控服务器启动"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        if check_master_server_health(host, port):
            logger.info(f"主控服务器已就绪: {host}:{port}")
            return True
        
        time.sleep(check_interval)
    
    logger.error(f"等待主控服务器超时: {max_wait_time}秒")
    return False

def get_app_info_by_prefix(prefix: str) -> Optional[Dict[str, Any]]:
    """根据前缀获取应用信息"""
    try:
        status = get_master_server_status()
        if status['status'] != 'running':
            return None
        
        for app in status['apps']:
            if app['prefix'] == prefix:
                return app
        
        return None
    except Exception as e:
        logger.error(f"获取应用信息失败: {e}")
        return None

def create_simple_flask_app(name: str, routes: Dict[str, Callable] = None) -> Flask:
    """创建一个简单的Flask应用，用于测试"""
    app = Flask(name)
    
    @app.route('/')
    def home():
        return {"message": f"这是 {name} 应用", "app": name}
    
    @app.route('/health')
    def health():
        return {"status": "healthy", "app": name, "timestamp": time.time()}
    
    # 添加自定义路由
    if routes:
        for path, handler in routes.items():
            app.add_url_rule(path, endpoint=f"{name}_{path.replace('/', '_')}", view_func=handler)
    
    return app

def measure_request_performance(func: Callable) -> Callable:
    """装饰器：测量请求处理性能"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"请求处理耗时: {duration:.3f}秒")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"请求处理失败，耗时: {duration:.3f}秒，错误: {e}")
            raise
    return wrapper

class RequestBatcher:
    """请求批处理器 - 将多个请求合并处理以提高效率"""
    
    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests: List[Any] = []
        self.lock = threading.Lock()
        self.last_batch_time = time.time()
    
    def add_request(self, request_data: Any) -> bool:
        """添加请求到批处理队列"""
        with self.lock:
            self.pending_requests.append(request_data)
            
            # 检查是否应该触发批处理
            should_process = (
                len(self.pending_requests) >= self.batch_size or
                time.time() - self.last_batch_time > self.batch_timeout
            )
            
            if should_process:
                self.process_batch()
                return True
            
            return False
    
    def process_batch(self):
        """处理批量请求"""
        if not self.pending_requests:
            return
        
        batch = self.pending_requests.copy()
        self.pending_requests.clear()
        self.last_batch_time = time.time()
        
        logger.info(f"处理批量请求: {len(batch)} 个")
        
        # 这里可以添加实际的批处理逻辑
        # 例如数据库批量操作等

class CircuitBreaker:
    """熔断器 - 防止系统过载"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """通过熔断器调用函数"""
        with self.lock:
            if self.state == "OPEN":
                # 检查是否可以进入半开状态
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info("熔断器进入半开状态")
                else:
                    raise Exception("熔断器开启，请求被拒绝")
            
            try:
                result = func(*args, **kwargs)
                
                # 成功调用，重置失败计数
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failure_count = 0
                    logger.info("熔断器恢复到关闭状态")
                
                return result
                
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.warning(f"熔断器开启，失败次数: {self.failure_count}")
                
                raise e

def optimize_flask_app(app: Flask, 
                      enable_gzip: bool = True,
                      enable_caching: bool = True,
                      cache_timeout: int = 300) -> Flask:
    """为Flask应用添加性能优化"""
    
    if enable_gzip:
        try:
            from flask_compress import Compress
            Compress(app)
            logger.info("已启用Gzip压缩")
        except ImportError:
            logger.warning("flask-compress未安装，跳过Gzip压缩")
    
    if enable_caching:
        try:
            from flask_caching import Cache
            cache = Cache(app, config={'CACHE_TYPE': 'simple'})
            
            # 添加缓存装饰器到应用
            app.cache = cache
            logger.info("已启用应用缓存")
        except ImportError:
            logger.warning("flask-caching未安装，跳过缓存功能")
    
    return app

def create_load_balancer(apps: List[Flask], strategy: str = "round_robin"):
    """创建负载均衡器"""
    
    class LoadBalancer:
        def __init__(self, apps: List[Flask], strategy: str):
            self.apps = apps
            self.strategy = strategy
            self.current_index = 0
            self.lock = threading.Lock()
        
        def get_next_app(self) -> Flask:
            """获取下一个应用（根据负载均衡策略）"""
            with self.lock:
                if self.strategy == "round_robin":
                    app = self.apps[self.current_index]
                    self.current_index = (self.current_index + 1) % len(self.apps)
                    return app
                else:
                    # 默认返回第一个应用
                    return self.apps[0] if self.apps else None
    
    return LoadBalancer(apps, strategy)