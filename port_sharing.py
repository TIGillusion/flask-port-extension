"""
Flask端口复用核心实现
"""

import threading
import time
import queue
import uuid
import json
import requests
from typing import Dict, Any, Optional, Callable
from flask import Flask, request, jsonify, Response
from werkzeug.serving import make_server
import asyncio
import concurrent.futures
from dataclasses import dataclass, asdict
import logging
from .performance import get_performance_optimizer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AppRequest:
    """应用请求数据结构"""
    request_id: str
    app_prefix: str
    method: str
    path: str
    headers: Dict[str, str]
    data: bytes
    query_string: str

@dataclass
class AppResponse:
    """应用响应数据结构"""
    request_id: str
    status_code: int
    headers: Dict[str, str]
    data: bytes

class AppRegistry:
    """应用注册器 - 管理所有注册的Flask应用"""
    
    def __init__(self):
        self.apps: Dict[str, Dict[str, Any]] = {}
        self.request_queues: Dict[str, queue.Queue] = {}
        self.response_queues: Dict[str, queue.Queue] = {}
        self.app_threads: Dict[str, threading.Thread] = {}
        self.lock = threading.RLock()
    
    def register_app(self, app_id: str, prefix: str, app: Flask) -> bool:
        """注册一个Flask应用"""
        with self.lock:
            if prefix in self.apps:
                logger.warning(f"应用前缀 '{prefix}' 已存在")
                return False
            
            self.apps[prefix] = {
                'app_id': app_id,
                'app': app,
                'prefix': prefix,
                'active': False
            }
            self.request_queues[app_id] = queue.Queue(maxsize=1000)  # 限制队列大小防止内存溢出
            self.response_queues[app_id] = queue.Queue(maxsize=1000)
            
            logger.info(f"应用已注册: {app_id} -> {prefix}")
            return True
    
    def unregister_app(self, app_id: str) -> bool:
        """注销一个Flask应用"""
        with self.lock:
            prefix_to_remove = None
            for prefix, app_info in self.apps.items():
                if app_info['app_id'] == app_id:
                    prefix_to_remove = prefix
                    break
            
            if prefix_to_remove:
                del self.apps[prefix_to_remove]
                if app_id in self.request_queues:
                    del self.request_queues[app_id]
                if app_id in self.response_queues:
                    del self.response_queues[app_id]
                if app_id in self.app_threads:
                    del self.app_threads[app_id]
                
                logger.info(f"应用已注销: {app_id}")
                return True
            return False
    
    def get_app_by_prefix(self, path: str) -> Optional[str]:
        """根据请求路径获取对应的应用ID"""
        with self.lock:
            # 找到最长匹配的前缀
            best_match = ""
            best_app_id = None
            
            for prefix, app_info in self.apps.items():
                if path.startswith(prefix) and len(prefix) > len(best_match):
                    best_match = prefix
                    best_app_id = app_info['app_id']
            
            return best_app_id
    
    def set_app_active(self, app_id: str, active: bool):
        """设置应用的活跃状态"""
        with self.lock:
            for app_info in self.apps.values():
                if app_info['app_id'] == app_id:
                    app_info['active'] = active
                    break

class RequestDispatcher:
    """请求分发器 - 处理请求的路由和分发"""
    
    def __init__(self, registry: AppRegistry):
        self.registry = registry
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)  # 线程池优化
    
    def dispatch_request(self, flask_request) -> Response:
        """分发请求到对应的应用"""
        start_time = time.time()
        path = flask_request.path
        app_id = self.registry.get_app_by_prefix(path)
        
        if not app_id:
            return Response("未找到匹配的应用", status=404)
        
        # 获取性能优化器
        optimizer = get_performance_optimizer()
        
        # 检查是否应该处理请求（限流）
        if not optimizer.should_process_request(app_id):
            return Response("请求频率超限", status=429)
        
        # 创建请求对象
        app_request = AppRequest(
            request_id=str(uuid.uuid4()),
            app_prefix=path,
            method=flask_request.method,
            path=path,
            headers=dict(flask_request.headers),
            data=flask_request.get_data(),
            query_string=flask_request.query_string.decode('utf-8')
        )
        
        try:
            # 将请求放入应用的请求队列
            self.registry.request_queues[app_id].put(app_request, timeout=5)
            
            # 等待响应
            response = self.registry.response_queues[app_id].get(timeout=30)
            
            if response.request_id != app_request.request_id:
                logger.error(f"响应ID不匹配: 期望 {app_request.request_id}, 得到 {response.request_id}")
                duration = time.time() - start_time
                optimizer.record_request_metrics(app_id, duration, 500)
                return Response("内部错误", status=500)
            
            # 记录性能指标
            duration = time.time() - start_time
            optimizer.record_request_metrics(app_id, duration, response.status_code)
            
            # 构建Flask响应
            flask_response = Response(
                response.data,
                status=response.status_code,
                headers=response.headers
            )
            return flask_response
            
        except queue.Full:
            logger.error(f"应用 {app_id} 的请求队列已满")
            duration = time.time() - start_time
            optimizer.record_request_metrics(app_id, duration, 503)
            return Response("服务繁忙", status=503)
        except queue.Empty:
            logger.error(f"应用 {app_id} 响应超时")
            duration = time.time() - start_time
            optimizer.record_request_metrics(app_id, duration, 504)
            return Response("请求超时", status=504)
        except Exception as e:
            logger.error(f"分发请求时出错: {e}")
            duration = time.time() - start_time
            optimizer.record_request_metrics(app_id, duration, 500)
            return Response("内部错误", status=500)

class MasterServer:
    """主控服务器 - 真正占用端口的Flask服务器"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5000):
        self.host = host
        self.port = port
        self.registry = AppRegistry()
        self.dispatcher = RequestDispatcher(self.registry)
        self.master_app = Flask(__name__)
        self.server = None
        self.running = False
        self.server_thread = None
        
        # 设置路由
        self.setup_routes()
    
    def setup_routes(self):
        """设置主控服务器的路由"""
        
        @self.master_app.route('/_master/health', methods=['GET'])
        def health_check():
            """健康检查端点"""
            return jsonify({
                'status': 'healthy',
                'registered_apps': len(self.registry.apps),
                'active_apps': sum(1 for app in self.registry.apps.values() if app['active'])
            })
        
        @self.master_app.route('/_master/apps', methods=['GET'])
        def list_apps():
            """列出所有注册的应用"""
            apps_info = []
            with self.registry.lock:
                for prefix, app_info in self.registry.apps.items():
                    apps_info.append({
                        'app_id': app_info['app_id'],
                        'prefix': prefix,
                        'active': app_info['active']
                    })
            return jsonify(apps_info)
        
        @self.master_app.route('/_master/stats', methods=['GET'])
        def get_stats():
            """获取性能统计信息"""
            app_id = request.args.get('app_id')
            optimizer = get_performance_optimizer()
            stats = optimizer.get_performance_stats(app_id)
            return jsonify(stats)
        
        @self.master_app.route('/_master/stats/<app_id>', methods=['GET'])
        def get_app_stats(app_id):
            """获取特定应用的性能统计"""
            optimizer = get_performance_optimizer()
            stats = optimizer.get_performance_stats(app_id)
            return jsonify(stats)
        
        @self.master_app.before_request
        def before_request():
            """在每个请求前执行的钩子"""
            # 跳过主控路由
            if request.path.startswith('/_master/'):
                return None
            
            # 分发到对应的应用
            return self.dispatcher.dispatch_request(request)
    
    def start(self):
        """启动主控服务器"""
        if self.running:
            logger.warning("主控服务器已在运行中")
            return
        
        self.server = make_server(self.host, self.port, self.master_app, threaded=True)
        self.running = True
        
        def run_server():
            logger.info(f"主控服务器启动在 {self.host}:{self.port}")
            self.server.serve_forever()
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # 等待服务器启动
        time.sleep(0.5)
        
    def stop(self):
        """停止主控服务器"""
        if not self.running:
            return
        
        self.running = False
        if self.server:
            self.server.shutdown()
        
        if self.server_thread:
            self.server_thread.join(timeout=5)
        
        logger.info("主控服务器已停止")

class AppWrapper:
    """应用包装器 - 重写Flask应用的run方法"""
    
    def __init__(self, app: Flask, app_id: str, prefix: str, master_server: MasterServer):
        self.app = app
        self.app_id = app_id
        self.prefix = prefix
        self.master_server = master_server
        self.running = False
        self.polling_thread = None
        
        # 保存原始的run方法
        self.original_run = app.run
        
        # 重写run方法
        app.run = self.wrapped_run
    
    def wrapped_run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        """重写的run方法 - 启动轮询而不是真正的服务器"""
        logger.info(f"应用 {self.app_id} 开始轮询模式运行")
        
        # 注册到主控服务器
        if not self.master_server.registry.register_app(self.app_id, self.prefix, self.app):
            logger.error(f"注册应用失败: {self.app_id}")
            return
        
        # 设置为活跃状态
        self.master_server.registry.set_app_active(self.app_id, True)
        
        # 启动轮询线程
        self.running = True
        self.polling_thread = threading.Thread(target=self.polling_loop, daemon=True)
        self.polling_thread.start()
        
        try:
            # 保持主线程运行
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info(f"应用 {self.app_id} 收到中断信号")
        finally:
            self.stop()
    
    def polling_loop(self):
        """轮询循环 - 处理来自主控服务器的请求"""
        logger.info(f"应用 {self.app_id} 开始轮询循环")
        
        while self.running:
            try:
                # 从请求队列获取请求
                app_request = self.master_server.registry.request_queues[self.app_id].get(timeout=1)
                
                # 处理请求
                response = self.process_request(app_request)
                
                # 将响应放入响应队列
                self.master_server.registry.response_queues[self.app_id].put(response, timeout=5)
                
            except queue.Empty:
                # 轮询超时，继续下一次循环
                continue
            except queue.Full:
                logger.error(f"应用 {self.app_id} 的响应队列已满")
            except Exception as e:
                logger.error(f"应用 {self.app_id} 轮询循环出错: {e}")
                time.sleep(0.1)  # 避免疯狂循环
        
        logger.info(f"应用 {self.app_id} 轮询循环结束")
    
    def process_request(self, app_request: AppRequest) -> AppResponse:
        """处理单个请求"""
        try:
            # 移除前缀，获取应用内的路径
            app_path = app_request.path
            if app_path.startswith(self.prefix):
                app_path = app_path[len(self.prefix):] or '/'
            
            # 创建测试客户端
            with self.app.test_client() as client:
                # 构建请求参数
                kwargs = {
                    'method': app_request.method,
                    'path': app_path,
                    'headers': app_request.headers,
                    'query_string': app_request.query_string
                }
                
                if app_request.data:
                    kwargs['data'] = app_request.data
                
                # 发送请求到应用
                response = client.open(**kwargs)
                
                # 构建响应对象
                app_response = AppResponse(
                    request_id=app_request.request_id,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    data=response.get_data()
                )
                
                return app_response
                
        except Exception as e:
            logger.error(f"处理请求时出错: {e}")
            return AppResponse(
                request_id=app_request.request_id,
                status_code=500,
                headers={'Content-Type': 'text/plain'},
                data=f"内部错误: {str(e)}".encode('utf-8')
            )
    
    def stop(self):
        """停止应用轮询"""
        self.running = False
        self.master_server.registry.set_app_active(self.app_id, False)
        
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
        
        # 注销应用
        self.master_server.registry.unregister_app(self.app_id)
        logger.info(f"应用 {self.app_id} 已停止")

# 全局主控服务器实例
_master_server: Optional[MasterServer] = None
_master_server_lock = threading.Lock()

def get_or_create_master_server(host: str = '127.0.0.1', port: int = 5000) -> MasterServer:
    """获取或创建主控服务器实例"""
    global _master_server
    
    with _master_server_lock:
        if _master_server is None:
            _master_server = MasterServer(host, port)
            _master_server.start()
        return _master_server

def enable_port_sharing(app: Flask, prefix: str = "", 
                       master_host: str = '127.0.0.1', 
                       master_port: int = 5000) -> str:
    """
    为Flask应用启用端口复用功能
    
    Args:
        app: Flask应用实例
        prefix: 应用的路径前缀，例如 "/api/v1"
        master_host: 主控服务器主机地址
        master_port: 主控服务器端口
    
    Returns:
        应用ID
    """
    # 生成唯一的应用ID
    app_id = str(uuid.uuid4())
    
    # 确保前缀格式正确
    if prefix and not prefix.startswith('/'):
        prefix = '/' + prefix
    if prefix == '/':
        prefix = ''
    
    # 获取或创建主控服务器
    master_server = get_or_create_master_server(master_host, master_port)
    
    # 创建应用包装器
    wrapper = AppWrapper(app, app_id, prefix, master_server)
    
    logger.info(f"为应用启用端口复用: {app_id} -> {prefix}")
    return app_id

def start_master_server(host: str = '127.0.0.1', port: int = 5000):
    """手动启动主控服务器"""
    master_server = get_or_create_master_server(host, port)
    logger.info(f"主控服务器已在 {host}:{port} 上运行")

def get_master_server_status() -> Dict[str, Any]:
    """获取主控服务器状态"""
    global _master_server
    
    if _master_server is None:
        return {'status': 'not_running'}
    
    with _master_server.registry.lock:
        return {
            'status': 'running' if _master_server.running else 'stopped',
            'host': _master_server.host,
            'port': _master_server.port,
            'registered_apps': len(_master_server.registry.apps),
            'active_apps': sum(1 for app in _master_server.registry.apps.values() if app['active']),
            'apps': [
                {
                    'app_id': app_info['app_id'],
                    'prefix': prefix,
                    'active': app_info['active']
                }
                for prefix, app_info in _master_server.registry.apps.items()
            ]
        }