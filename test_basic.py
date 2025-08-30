"""
基本功能测试
"""

import unittest
import threading
import time
import requests
from flask import Flask, jsonify
from . import enable_port_sharing, start_master_server, get_master_server_status

class TestFlaskPortSharing(unittest.TestCase):
    """Flask端口复用基本功能测试"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 启动主控服务器
        start_master_server(host='127.0.0.1', port=5001)  # 使用不同端口避免冲突
        time.sleep(1)  # 等待服务器启动
    
    def setUp(self):
        """每个测试前的设置"""
        self.base_url = "http://127.0.0.1:5001"
        self.test_apps = []
        self.test_threads = []
    
    def tearDown(self):
        """每个测试后的清理"""
        # 清理测试应用
        for app_thread in self.test_threads:
            if app_thread.is_alive():
                # 注意：在实际实现中需要优雅关闭
                pass
    
    def create_test_app(self, name: str):
        """创建测试应用"""
        app = Flask(name)
        
        @app.route('/')
        def home():
            return jsonify({
                "message": f"这是{name}应用",
                "app_name": name,
                "timestamp": time.time()
            })
        
        @app.route('/test')
        def test_endpoint():
            return jsonify({
                "test": True,
                "app": name
            })
        
        return app
    
    def test_master_server_health(self):
        """测试主控服务器健康检查"""
        response = requests.get(f"{self.base_url}/_master/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('registered_apps', data)
        self.assertIn('active_apps', data)
    
    def test_single_app_registration(self):
        """测试单个应用注册"""
        # 创建测试应用
        app = self.create_test_app("test_app")
        app_id = enable_port_sharing(app, prefix="/test", 
                                   master_host='127.0.0.1', master_port=5001)
        
        self.assertIsNotNone(app_id)
        self.assertIsInstance(app_id, str)
        
        # 启动应用
        def run_app():
            app.run()
        
        app_thread = threading.Thread(target=run_app, daemon=True)
        app_thread.start()
        self.test_threads.append(app_thread)
        
        # 等待应用启动
        time.sleep(2)
        
        # 测试应用访问
        response = requests.get(f"{self.base_url}/test/")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['app_name'], 'test_app')
        
        # 测试子路由
        response = requests.get(f"{self.base_url}/test/test")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['test'])
        self.assertEqual(data['app'], 'test_app')
    
    def test_multiple_apps_registration(self):
        """测试多个应用注册"""
        # 创建两个测试应用
        app1 = self.create_test_app("app1")
        app2 = self.create_test_app("app2")
        
        app1_id = enable_port_sharing(app1, prefix="/app1", 
                                    master_host='127.0.0.1', master_port=5001)
        app2_id = enable_port_sharing(app2, prefix="/app2", 
                                    master_host='127.0.0.1', master_port=5001)
        
        # 启动应用
        def run_app1():
            app1.run()
        
        def run_app2():
            app2.run()
        
        thread1 = threading.Thread(target=run_app1, daemon=True)
        thread2 = threading.Thread(target=run_app2, daemon=True)
        
        thread1.start()
        time.sleep(0.5)
        thread2.start()
        time.sleep(2)
        
        self.test_threads.extend([thread1, thread2])
        
        # 测试两个应用都可以访问
        response1 = requests.get(f"{self.base_url}/app1/")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.json()['app_name'], 'app1')
        
        response2 = requests.get(f"{self.base_url}/app2/")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['app_name'], 'app2')
        
        # 测试应用列表API
        apps_response = requests.get(f"{self.base_url}/_master/apps")
        self.assertEqual(apps_response.status_code, 200)
        
        apps = apps_response.json()
        self.assertIsInstance(apps, list)
        self.assertGreaterEqual(len(apps), 2)
    
    def test_nonexistent_route(self):
        """测试不存在的路由"""
        response = requests.get(f"{self.base_url}/nonexistent/path")
        self.assertEqual(response.status_code, 404)
    
    def test_performance_stats(self):
        """测试性能统计功能"""
        # 先创建一个应用并发送一些请求
        app = self.create_test_app("perf_test")
        enable_port_sharing(app, prefix="/perf", 
                           master_host='127.0.0.1', master_port=5001)
        
        def run_app():
            app.run()
        
        app_thread = threading.Thread(target=run_app, daemon=True)
        app_thread.start()
        self.test_threads.append(app_thread)
        time.sleep(2)
        
        # 发送一些测试请求
        for _ in range(5):
            requests.get(f"{self.base_url}/perf/")
            time.sleep(0.1)
        
        # 检查性能统计
        stats_response = requests.get(f"{self.base_url}/_master/stats")
        self.assertEqual(stats_response.status_code, 200)
        
        stats = stats_response.json()
        if 'total_requests' in stats:
            self.assertGreater(stats['total_requests'], 0)

class TestPerformanceOptimization(unittest.TestCase):
    """性能优化功能测试"""
    
    def test_request_throttling(self):
        """测试请求限流功能"""
        from .performance import RequestThrottler
        
        throttler = RequestThrottler(max_requests_per_second=2, max_requests_per_app=2)
        
        # 前两个请求应该被允许
        self.assertTrue(throttler.should_allow_request("test_app"))
        self.assertTrue(throttler.should_allow_request("test_app"))
        
        # 第三个请求应该被拒绝
        self.assertFalse(throttler.should_allow_request("test_app"))
    
    def test_performance_monitor(self):
        """测试性能监控功能"""
        from .performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # 记录一些请求指标
        monitor.record_request("test_app", 0.1, 200)
        monitor.record_request("test_app", 0.2, 200)
        monitor.record_request("test_app", 0.15, 404)
        
        # 获取统计信息
        stats = monitor.get_stats("test_app")
        
        self.assertEqual(stats['total_requests'], 3)
        self.assertAlmostEqual(stats['avg_duration'], 0.15, places=2)
        self.assertAlmostEqual(stats['error_rate'], 33.33, places=1)

class TestUtilityFunctions(unittest.TestCase):
    """工具函数测试"""
    
    def test_validate_app_prefix(self):
        """测试应用前缀验证"""
        from .utils import validate_app_prefix
        
        # 测试各种前缀格式
        self.assertEqual(validate_app_prefix("api"), "/api")
        self.assertEqual(validate_app_prefix("/api"), "/api")
        self.assertEqual(validate_app_prefix("/api/"), "/api")
        self.assertEqual(validate_app_prefix(""), "")
        self.assertEqual(validate_app_prefix("/"), "")
    
    def test_create_simple_flask_app(self):
        """测试简单Flask应用创建"""
        from .utils import create_simple_flask_app
        
        app = create_simple_flask_app("test")
        
        # 测试应用是否正确创建
        self.assertIsInstance(app, Flask)
        self.assertEqual(app.name, "test")
        
        # 测试默认路由
        with app.test_client() as client:
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            
            data = response.get_json()
            self.assertIn("test", data['app'])

def run_tests():
    """运行所有测试"""
    print("🧪 运行Flask端口复用扩展测试...")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskPortSharing))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceOptimization))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    if success:
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 有测试失败！")
        exit(1)