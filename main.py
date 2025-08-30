"""
Flask端口复用扩展 - 主入口文件

这个模块提供了让多个Flask应用共享同一个端口的功能。

基本使用方法:
    from pytools.flask_port_extension import enable_port_sharing
    
    app = Flask(__name__)
    enable_port_sharing(app, prefix="/myapp")
    app.run()  # 这会启动轮询模式而不是真正的服务器

高级使用方法:
    # 手动启动主控服务器
    from pytools.flask_port_extension import start_master_server
    start_master_server(host='0.0.0.0', port=8080)
    
    # 启用性能优化
    from pytools.flask_port_extension.performance import enable_performance_optimization
    enable_performance_optimization(max_requests_per_second=200)
"""

from . import enable_port_sharing, start_master_server, get_master_server_status
from .performance import enable_performance_optimization, get_performance_optimizer
from .utils import (
    validate_app_prefix, 
    check_master_server_health, 
    wait_for_master_server,
    create_simple_flask_app
)

__all__ = [
    'enable_port_sharing',
    'start_master_server', 
    'get_master_server_status',
    'enable_performance_optimization',
    'get_performance_optimizer',
    'validate_app_prefix',
    'check_master_server_health',
    'wait_for_master_server',
    'create_simple_flask_app'
]

def main():
    """主函数 - 可以直接运行演示"""
    print("Flask端口复用扩展")
    print("运行演示请使用: python -m pytools.flask_port_extension.demo")

if __name__ == "__main__":
    main()
