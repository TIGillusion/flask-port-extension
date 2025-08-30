"""
Flask端口复用扩展使用示例
"""

from flask import Flask, jsonify, request
from . import enable_port_sharing, start_master_server, get_master_server_status
import threading
import time

def create_demo_app1():
    """创建演示应用1 - 用户管理API"""
    app = Flask(__name__)
    
    users = [
        {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
        {"id": 2, "name": "李四", "email": "lisi@example.com"}
    ]
    
    @app.route('/')
    def home():
        return jsonify({"message": "用户管理API", "app": "demo_app1"})
    
    @app.route('/users', methods=['GET'])
    def get_users():
        return jsonify(users)
    
    @app.route('/users/<int:user_id>', methods=['GET'])
    def get_user(user_id):
        user = next((u for u in users if u['id'] == user_id), None)
        if user:
            return jsonify(user)
        return jsonify({"error": "用户未找到"}), 404
    
    @app.route('/users', methods=['POST'])
    def create_user():
        data = request.get_json()
        new_user = {
            "id": len(users) + 1,
            "name": data.get("name"),
            "email": data.get("email")
        }
        users.append(new_user)
        return jsonify(new_user), 201
    
    return app

def create_demo_app2():
    """创建演示应用2 - 产品管理API"""
    app = Flask(__name__)
    
    products = [
        {"id": 1, "name": "笔记本电脑", "price": 5999.99},
        {"id": 2, "name": "手机", "price": 2999.99}
    ]
    
    @app.route('/')
    def home():
        return jsonify({"message": "产品管理API", "app": "demo_app2"})
    
    @app.route('/products', methods=['GET'])
    def get_products():
        return jsonify(products)
    
    @app.route('/products/<int:product_id>', methods=['GET'])
    def get_product(product_id):
        product = next((p for p in products if p['id'] == product_id), None)
        if product:
            return jsonify(product)
        return jsonify({"error": "产品未找到"}), 404
    
    @app.route('/products', methods=['POST'])
    def create_product():
        data = request.get_json()
        new_product = {
            "id": len(products) + 1,
            "name": data.get("name"),
            "price": data.get("price")
        }
        products.append(new_product)
        return jsonify(new_product), 201
    
    return app

def run_example_single_app():
    """运行单个应用的示例"""
    print("=== 单个应用示例 ===")
    
    # 创建应用
    app = create_demo_app1()
    
    # 启用端口复用（使用默认前缀）
    app_id = enable_port_sharing(app)
    print(f"应用ID: {app_id}")
    
    # 运行应用（这会启动轮询模式）
    print("启动应用中...")
    app.run(debug=True)

def run_example_multi_apps():
    """运行多个应用的示例"""
    print("=== 多个应用示例 ===")
    
    # 先启动主控服务器
    start_master_server(host='127.0.0.1', port=5000)
    
    # 创建应用1
    app1 = create_demo_app1()
    app1_id = enable_port_sharing(app1, prefix="/users")
    
    # 创建应用2
    app2 = create_demo_app2()
    app2_id = enable_port_sharing(app2, prefix="/products")
    
    def run_app1():
        print("启动用户管理应用...")
        app1.run()
    
    def run_app2():
        print("启动产品管理应用...")
        app2.run()
    
    # 在不同线程中运行应用
    thread1 = threading.Thread(target=run_app1, daemon=True)
    thread2 = threading.Thread(target=run_app2, daemon=True)
    
    thread1.start()
    time.sleep(1)  # 稍微延迟启动第二个应用
    thread2.start()
    
    print("两个应用都已启动！")
    print("测试URL:")
    print("  用户API: http://127.0.0.1:5000/users/")
    print("  产品API: http://127.0.0.1:5000/products/")
    print("  服务器状态: http://127.0.0.1:5000/_master/health")
    print("  应用列表: http://127.0.0.1:5000/_master/apps")
    
    try:
        # 保持主线程运行
        while True:
            status = get_master_server_status()
            print(f"\n当前状态: {status['active_apps']}/{status['registered_apps']} 应用活跃")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n正在关闭...")

def run_performance_test():
    """运行性能测试"""
    print("=== 性能测试 ===")
    
    import requests
    import concurrent.futures
    import time
    
    # 启动主控服务器
    start_master_server()
    
    # 创建测试应用
    app = create_demo_app1()
    enable_port_sharing(app, prefix="/test")
    
    def run_app():
        app.run()
    
    # 启动应用
    app_thread = threading.Thread(target=run_app, daemon=True)
    app_thread.start()
    time.sleep(2)  # 等待应用启动
    
    # 性能测试
    base_url = "http://127.0.0.1:5000/test"
    
    def make_request(i):
        try:
            response = requests.get(f"{base_url}/users", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"请求 {i} 失败: {e}")
            return False
    
    # 并发测试
    num_requests = 100
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_requests)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    end_time = time.time()
    success_rate = sum(results) / len(results) * 100
    duration = end_time - start_time
    
    print(f"性能测试结果:")
    print(f"  总请求数: {num_requests}")
    print(f"  成功率: {success_rate:.1f}%")
    print(f"  总耗时: {duration:.2f}秒")
    print(f"  每秒请求数: {num_requests/duration:.2f} RPS")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == "single":
            run_example_single_app()
        elif test_type == "multi":
            run_example_multi_apps()
        elif test_type == "perf":
            run_performance_test()
        else:
            print("可用的测试类型: single, multi, perf")
    else:
        print("请指定测试类型: single, multi, perf")
        print("例如: python examples.py multi")