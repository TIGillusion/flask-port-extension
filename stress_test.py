"""
压力测试和性能基准测试
"""

import threading
import time
import requests
import concurrent.futures
import statistics
from flask import Flask, jsonify
from . import enable_port_sharing, start_master_server
from .performance import enable_performance_optimization

def create_load_test_app(name: str):
    """创建用于负载测试的应用"""
    app = Flask(name)
    
    @app.route('/')
    def home():
        return jsonify({
            "message": f"负载测试应用 {name}",
            "timestamp": time.time(),
            "app": name
        })
    
    @app.route('/heavy')
    def heavy_computation():
        """模拟重计算任务"""
        # 模拟一些计算工作
        result = sum(i * i for i in range(1000))
        return jsonify({
            "result": result,
            "app": name,
            "computation": "heavy"
        })
    
    @app.route('/light')
    def light_computation():
        """模拟轻量任务"""
        return jsonify({
            "message": "轻量任务完成",
            "app": name,
            "computation": "light"
        })
    
    return app

class LoadTester:
    """负载测试器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
    
    def make_request(self, endpoint: str, request_id: int) -> dict:
        """发送单个请求并记录结果"""
        start_time = time.time()
        
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            duration = time.time() - start_time
            
            result = {
                'request_id': request_id,
                'endpoint': endpoint,
                'status_code': response.status_code,
                'duration': duration,
                'success': response.status_code == 200,
                'timestamp': start_time
            }
            
            with self.lock:
                self.results.append(result)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = {
                'request_id': request_id,
                'endpoint': endpoint,
                'status_code': 0,
                'duration': duration,
                'success': False,
                'error': str(e),
                'timestamp': start_time
            }
            
            with self.lock:
                self.results.append(result)
            
            return result
    
    def run_concurrent_test(self, endpoint: str, num_requests: int, max_workers: int = 20):
        """运行并发测试"""
        print(f"\n🚀 开始并发测试: {endpoint}")
        print(f"   请求数: {num_requests}, 并发数: {max_workers}")
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.make_request, endpoint, i) 
                for i in range(num_requests)
            ]
            
            # 等待所有请求完成
            concurrent.futures.wait(futures)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # 分析结果
        self.analyze_results(endpoint, total_duration)
    
    def analyze_results(self, endpoint: str, total_duration: float):
        """分析测试结果"""
        endpoint_results = [r for r in self.results if r['endpoint'] == endpoint]
        
        if not endpoint_results:
            print("   ❌ 没有结果数据")
            return
        
        # 计算统计信息
        success_count = sum(1 for r in endpoint_results if r['success'])
        error_count = len(endpoint_results) - success_count
        success_rate = (success_count / len(endpoint_results)) * 100
        
        durations = [r['duration'] for r in endpoint_results if r['success']]
        if durations:
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            p95_duration = statistics.quantiles(durations, n=20)[18]  # 95th percentile
        else:
            avg_duration = min_duration = max_duration = p95_duration = 0
        
        rps = len(endpoint_results) / total_duration
        
        # 输出结果
        print(f"\n📊 测试结果 - {endpoint}:")
        print(f"   ✅ 成功请求: {success_count}")
        print(f"   ❌ 失败请求: {error_count}")
        print(f"   📈 成功率: {success_rate:.1f}%")
        print(f"   ⚡ 每秒请求数: {rps:.2f} RPS")
        print(f"   ⏱️ 平均响应时间: {avg_duration:.3f}秒")
        print(f"   🏃 最快响应: {min_duration:.3f}秒")
        print(f"   🐌 最慢响应: {max_duration:.3f}秒")
        print(f"   📊 95th百分位: {p95_duration:.3f}秒")
    
    def clear_results(self):
        """清空测试结果"""
        with self.lock:
            self.results.clear()

def run_basic_load_test():
    """运行基本负载测试"""
    print("🏋️ 启动基本负载测试")
    print("=" * 50)
    
    # 启动主控服务器
    print("1. 启动主控服务器...")
    start_master_server(host='127.0.0.1', port=5000)
    time.sleep(1)
    
    # 启用性能优化
    print("2. 启用性能优化...")
    enable_performance_optimization(
        max_requests_per_second=200,
        max_requests_per_app=100,
        max_workers=50
    )
    
    # 创建测试应用
    print("3. 创建测试应用...")
    app1 = create_load_test_app("load_app_1")
    app2 = create_load_test_app("load_app_2")
    
    enable_port_sharing(app1, prefix="/load1")
    enable_port_sharing(app2, prefix="/load2")
    
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
    time.sleep(3)  # 等待应用完全启动
    
    print("4. 应用启动完成，开始负载测试...")
    
    # 创建负载测试器
    tester = LoadTester("http://127.0.0.1:5000")
    
    # 测试不同场景
    test_scenarios = [
        ("/load1/", "应用1轻量请求", 50, 10),
        ("/load1/heavy", "应用1重量请求", 20, 5),
        ("/load2/light", "应用2轻量请求", 50, 10),
        ("/_master/health", "健康检查", 30, 5),
    ]
    
    for endpoint, description, num_requests, max_workers in test_scenarios:
        print(f"\n🎯 测试场景: {description}")
        tester.run_concurrent_test(endpoint, num_requests, max_workers)
        time.sleep(2)  # 间隔时间
    
    # 获取最终性能统计
    print("\n📈 获取性能统计...")
    try:
        stats_response = requests.get("http://127.0.0.1:5000/_master/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"   📊 总请求数: {stats.get('total_requests', 0)}")
            print(f"   ⏱️ 平均响应时间: {stats.get('avg_duration', 0):.3f}秒")
            print(f"   📉 错误率: {stats.get('error_rate', 0):.2f}%")
            print(f"   🚀 每分钟请求数: {stats.get('requests_per_minute', 0)}")
    except Exception as e:
        print(f"   ⚠️ 获取统计失败: {e}")

def run_stress_test():
    """运行压力测试"""
    print("\n🔥 启动压力测试")
    print("=" * 50)
    
    # 启动系统
    start_master_server(host='127.0.0.1', port=5000)
    time.sleep(1)
    
    # 创建多个应用模拟真实场景
    apps = []
    threads = []
    
    for i in range(5):  # 创建5个应用
        app = create_load_test_app(f"stress_app_{i}")
        enable_port_sharing(app, prefix=f"/stress{i}")
        
        def run_app(app_instance=app):
            app_instance.run()
        
        thread = threading.Thread(target=run_app, daemon=True)
        thread.start()
        threads.append(thread)
        time.sleep(0.2)
    
    time.sleep(5)  # 等待所有应用启动
    
    print("5个应用已启动，开始压力测试...")
    
    tester = LoadTester("http://127.0.0.1:5000")
    
    # 高强度测试
    stress_tests = [
        ("/stress0/", 100, 20),
        ("/stress1/heavy", 50, 15),
        ("/stress2/light", 150, 25),
        ("/stress3/", 80, 15),
        ("/stress4/heavy", 40, 10),
    ]
    
    print(f"\n🎯 同时对5个应用进行压力测试...")
    
    # 并行运行所有压力测试
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(stress_tests)) as executor:
        futures = [
            executor.submit(tester.run_concurrent_test, endpoint, num_req, workers)
            for endpoint, num_req, workers in stress_tests
        ]
        
        concurrent.futures.wait(futures)
    
    print("\n🏁 压力测试完成！")

def run_endurance_test(duration_minutes: int = 5):
    """运行耐久性测试"""
    print(f"\n⏰ 启动{duration_minutes}分钟耐久性测试")
    print("=" * 50)
    
    # 启动系统
    start_master_server(host='127.0.0.1', port=5000)
    time.sleep(1)
    
    app = create_load_test_app("endurance_app")
    enable_port_sharing(app, prefix="/endurance")
    
    def run_app():
        app.run()
    
    app_thread = threading.Thread(target=run_app, daemon=True)
    app_thread.start()
    time.sleep(3)
    
    tester = LoadTester("http://127.0.0.1:5000")
    
    end_time = time.time() + (duration_minutes * 60)
    request_count = 0
    
    print(f"开始持续{duration_minutes}分钟的请求...")
    
    while time.time() < end_time:
        # 每秒发送5个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(tester.make_request, "/endurance/light", request_count + i)
                for i in range(5)
            ]
            concurrent.futures.wait(futures)
        
        request_count += 5
        time.sleep(1)
        
        # 每分钟输出一次进度
        if request_count % 300 == 0:
            minutes_elapsed = (time.time() - (end_time - duration_minutes * 60)) / 60
            print(f"   ⏱️ {minutes_elapsed:.1f}分钟已过，发送了 {request_count} 个请求")
    
    print(f"\n✅ 耐久性测试完成！总共发送了 {request_count} 个请求")
    
    # 分析最终结果
    tester.analyze_results("/endurance/light", duration_minutes * 60)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == "basic":
            run_basic_load_test()
        elif test_type == "stress":
            run_stress_test()
        elif test_type == "endurance":
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            run_endurance_test(duration)
        else:
            print("可用的测试类型:")
            print("  basic    - 基本负载测试")
            print("  stress   - 压力测试")
            print("  endurance [分钟] - 耐久性测试（默认5分钟）")
    else:
        print("请指定测试类型:")
        print("  python stress_test.py basic")
        print("  python stress_test.py stress")
        print("  python stress_test.py endurance 10")