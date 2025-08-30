"""
快速开始示例 - 最简单的使用方式
"""

from flask import Flask, jsonify
import sys
import os

# 添加模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_port_extension import enable_port_sharing

def create_simple_app():
    """创建一个简单的Flask应用"""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return jsonify({
            "message": "欢迎使用Flask端口复用扩展！",
            "description": "这是一个通过端口复用运行的Flask应用",
            "features": [
                "多应用单端口",
                "高性能优化", 
                "实时监控",
                "自动负载均衡"
            ]
        })
    
    @app.route('/api/hello')
    def hello():
        return jsonify({
            "greeting": "你好！",
            "timestamp": "现在",
            "app": "quick_start_demo"
        })
    
    @app.route('/api/status')
    def status():
        return jsonify({
            "status": "运行中",
            "mode": "端口复用模式",
            "performance": "已优化"
        })
    
    return app

def main():
    """主函数"""
    print("🚀 Flask端口复用扩展 - 快速开始")
    print("=" * 40)
    
    # 创建应用
    print("1. 创建Flask应用...")
    app = create_simple_app()
    
    # 启用端口复用
    print("2. 启用端口复用功能...")
    app_id = enable_port_sharing(app, prefix="/demo")
    
    print(f"✅ 应用注册成功！应用ID: {app_id}")
    print(f"🌐 访问地址: http://127.0.0.1:5000/demo/")
    print(f"📊 主控面板: http://127.0.0.1:5000/_master/health")
    
    print("\n3. 启动应用（轮询模式）...")
    print("💡 提示：这不会占用新端口，而是通过主控服务器复用端口！")
    
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        print("\n👋 应用已停止")

if __name__ == "__main__":
    main()