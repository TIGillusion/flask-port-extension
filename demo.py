"""
Flask端口复用演示脚本
运行这个脚本来测试端口复用功能
"""

import threading
import time
import requests
from flask import Flask, jsonify, request
from . import enable_port_sharing, start_master_server

def create_user_api():
    """用户管理API"""
    app = Flask(__name__)
    
    users = [
        {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
        {"id": 2, "name": "李四", "email": "lisi@example.com"}
    ]
    
    @app.route('/')
    def home():
        return jsonify({
            "message": "用户管理API",
            "version": "1.0",
            "endpoints": ["/users", "/users/<id>"]
        })
    
    @app.route('/users', methods=['GET'])
    def get_users():
        return jsonify({"users": users, "count": len(users)})
    
    @app.route('/users/<int:user_id>', methods=['GET'])
    def get_user(user_id):
        user = next((u for u in users if u['id'] == user_id), None)
        if user:
            return jsonify(user)
        return jsonify({"error": "用户未找到"}), 404
    
    @app.route('/users', methods=['POST'])
    def create_user():
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"error": "缺少用户名"}), 400
        
        new_user = {
            "id": len(users) + 1,
            "name": data.get("name"),
            "email": data.get("email", "")
        }
        users.append(new_user)
        return jsonify(new_user), 201
    
    return app

def create_product_api():
    """产品管理API"""
    app = Flask(__name__)
    
    products = [
        {"id": 1, "name": "笔记本电脑", "price": 5999.99, "category": "电子产品"},
        {"id": 2, "name": "手机", "price": 2999.99, "category": "电子产品"},
        {"id": 3, "name": "书籍", "price": 39.99, "category": "图书"}
    ]
    
    @app.route('/')
    def home():
        return jsonify({
            "message": "产品管理API",
            "version": "1.0",
            "endpoints": ["/products", "/products/<id>", "/categories"]
        })
    
    @app.route('/products', methods=['GET'])
    def get_products():
        category = request.args.get('category')
        if category:
            filtered_products = [p for p in products if p['category'] == category]
            return jsonify({"products": filtered_products, "count": len(filtered_products)})
        return jsonify({"products": products, "count": len(products)})
    
    @app.route('/products/<int:product_id>', methods=['GET'])
    def get_product(product_id):
        product = next((p for p in products if p['id'] == product_id), None)
        if product:
            return jsonify(product)
        return jsonify({"error": "产品未找到"}), 404
    
    @app.route('/categories', methods=['GET'])
    def get_categories():
        categories = list(set(p['category'] for p in products))
        return jsonify({"categories": categories})
    
    @app.route('/products', methods=['POST'])
    def create_product():
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"error": "缺少产品名称"}), 400
        
        new_product = {
            "id": len(products) + 1,
            "name": data.get("name"),
            "price": data.get("price", 0),
            "category": data.get("category", "其他")
        }
        products.append(new_product)
        return jsonify(new_product), 201
    
    return app

def run_demo():
    """运行完整演示"""
    print("🚀 启动Flask端口复用演示")
    print("=" * 50)
    
    # 启动主控服务器
    print("1. 启动主控服务器...")
    start_master_server(host='127.0.0.1', port=5000)
    time.sleep(1)
    
    # 创建并注册应用
    print("2. 创建用户管理API...")
    user_app = create_user_api()
    user_app_id = enable_port_sharing(user_app, prefix="/api/users")
    
    print("3. 创建产品管理API...")
    product_app = create_product_api()
    product_app_id = enable_port_sharing(product_app, prefix="/api/products")
    
    # 启动应用（在后台线程中）
    def run_user_app():
        print("📱 用户API开始轮询...")
        user_app.run()
    
    def run_product_app():
        print("🛍️ 产品API开始轮询...")
        product_app.run()
    
    user_thread = threading.Thread(target=run_user_app, daemon=True)
    product_thread = threading.Thread(target=run_product_app, daemon=True)
    
    user_thread.start()
    time.sleep(0.5)
    product_thread.start()
    time.sleep(2)  # 等待应用完全启动
    
    print("\n✅ 所有应用已启动！")
    print("\n🌐 可用的API端点:")
    print("   主控服务器状态: http://127.0.0.1:5000/_master/health")
    print("   应用列表: http://127.0.0.1:5000/_master/apps")
    print("   性能统计: http://127.0.0.1:5000/_master/stats")
    print("\n   用户API:")
    print("     http://127.0.0.1:5000/api/users/")
    print("     http://127.0.0.1:5000/api/users/users")
    print("     http://127.0.0.1:5000/api/users/users/1")
    print("\n   产品API:")
    print("     http://127.0.0.1:5000/api/products/")
    print("     http://127.0.0.1:5000/api/products/products")
    print("     http://127.0.0.1:5000/api/products/categories")
    
    # 运行一些测试请求
    print("\n🧪 运行测试请求...")
    test_requests()
    
    print("\n⏱️ 运行性能测试...")
    performance_test()
    
    print("\n✨ 演示完成！按 Ctrl+C 退出")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 演示结束")

def test_requests():
    """测试请求功能"""
    base_url = "http://127.0.0.1:5000"
    
    tests = [
        ("GET", f"{base_url}/_master/health", "主控服务器健康检查"),
        ("GET", f"{base_url}/_master/apps", "获取应用列表"),
        ("GET", f"{base_url}/api/users/", "用户API首页"),
        ("GET", f"{base_url}/api/users/users", "获取用户列表"),
        ("GET", f"{base_url}/api/products/", "产品API首页"),
        ("GET", f"{base_url}/api/products/products", "获取产品列表"),
        ("GET", f"{base_url}/api/products/categories", "获取产品分类"),
    ]
    
    for method, url, description in tests:
        try:
            response = requests.request(method, url, timeout=5)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {status} {description}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {description}: 错误 - {e}")

def performance_test():
    """性能测试"""
    import concurrent.futures
    
    base_url = "http://127.0.0.1:5000"
    
    def make_request(i):
        try:
            response = requests.get(f"{base_url}/api/users/users", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    # 并发测试
    num_requests = 50
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_requests)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    end_time = time.time()
    success_rate = sum(results) / len(results) * 100
    duration = end_time - start_time
    
    print(f"   📊 总请求数: {num_requests}")
    print(f"   📈 成功率: {success_rate:.1f}%")
    print(f"   ⏱️ 总耗时: {duration:.2f}秒")
    print(f"   🚀 每秒请求数: {num_requests/duration:.2f} RPS")
    
    # 获取性能统计
    try:
        stats_response = requests.get(f"{base_url}/_master/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"   📊 平均响应时间: {stats.get('avg_duration', 0):.3f}秒")
            print(f"   📉 错误率: {stats.get('error_rate', 0):.1f}%")
    except Exception as e:
        print(f"   ⚠️ 获取统计信息失败: {e}")

if __name__ == "__main__":
    run_demo()