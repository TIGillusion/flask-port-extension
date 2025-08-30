"""
配置管理模块
"""

import os
from typing import Dict, Any

class Config:
    """默认配置"""
    
    # 主控服务器配置
    MASTER_HOST = os.getenv('FLASK_PORT_SHARING_HOST', '127.0.0.1')
    MASTER_PORT = int(os.getenv('FLASK_PORT_SHARING_PORT', '5000'))
    
    # 性能配置
    MAX_REQUESTS_PER_SECOND = int(os.getenv('MAX_REQUESTS_PER_SECOND', '100'))
    MAX_REQUESTS_PER_APP = int(os.getenv('MAX_REQUESTS_PER_APP', '50'))
    MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', '100'))
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '50'))
    
    # 队列配置
    REQUEST_QUEUE_SIZE = int(os.getenv('REQUEST_QUEUE_SIZE', '1000'))
    RESPONSE_QUEUE_SIZE = int(os.getenv('RESPONSE_QUEUE_SIZE', '1000'))
    
    # 超时配置
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    RESPONSE_TIMEOUT = int(os.getenv('RESPONSE_TIMEOUT', '5'))
    
    # 日志配置
    LOG_LEVEL = os.getenv('FLASK_PORT_SHARING_LOG_LEVEL', 'INFO')
    
    # 监控配置
    ENABLE_MONITORING = os.getenv('ENABLE_MONITORING', 'true').lower() == 'true'
    ENABLE_THROTTLING = os.getenv('ENABLE_THROTTLING', 'true').lower() == 'true'
    ENABLE_CONNECTION_POOL = os.getenv('ENABLE_CONNECTION_POOL', 'true').lower() == 'true'
    ENABLE_ASYNC_PROCESSING = os.getenv('ENABLE_ASYNC_PROCESSING', 'true').lower() == 'true'
    
    # 熔断器配置
    CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv('CIRCUIT_BREAKER_FAILURE_THRESHOLD', '5'))
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.getenv('CIRCUIT_BREAKER_RECOVERY_TIMEOUT', '60'))

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    MAX_REQUESTS_PER_SECOND = 50
    MAX_REQUESTS_PER_APP = 25

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    MAX_REQUESTS_PER_SECOND = 500
    MAX_REQUESTS_PER_APP = 200
    MAX_CONNECTIONS = 1000
    MAX_WORKERS = 200

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    LOG_LEVEL = 'ERROR'
    MAX_REQUESTS_PER_SECOND = 20
    MAX_REQUESTS_PER_APP = 10

# 配置字典
config_dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': Config
}

def get_config(env: str = None) -> Config:
    """获取配置类"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'default')
    
    return config_dict.get(env, Config)

def load_config_from_file(config_file: str) -> Dict[str, Any]:
    """从文件加载配置"""
    config = {}
    
    if os.path.exists(config_file):
        try:
            if config_file.endswith('.json'):
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            elif config_file.endswith('.yaml') or config_file.endswith('.yml'):
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            else:
                # 假设是Python配置文件
                import importlib.util
                spec = importlib.util.spec_from_file_location("config", config_file)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                
                config = {
                    key: getattr(config_module, key)
                    for key in dir(config_module)
                    if not key.startswith('_')
                }
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    return config