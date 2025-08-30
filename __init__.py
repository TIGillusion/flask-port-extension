"""
Flask端口复用扩展

这个模块允许多个Flask应用共享同一个端口运行，
通过一个主控服务器来分发请求到不同的应用实例。
"""

from .port_sharing import enable_port_sharing, start_master_server, get_master_server_status

__version__ = "1.0.0"
__all__ = ["enable_port_sharing", "start_master_server", "get_master_server_status"]