# Flask端口复用扩展

这个扩展允许多个Flask应用共享同一个端口运行，通过一个主控服务器来分发请求到不同的应用实例。非常适合微服务架构或需要在同一端口部署多个独立应用的场景。

## ✨ 特性

- 🚀 **多应用单端口**: 让无数个Flask应用共享一个端口
- ⚡ **高性能**: 内置请求限流、连接池、异步处理等优化
- 🔧 **简单易用**: 只需一行代码即可启用端口复用
- 📊 **监控统计**: 实时性能监控和请求统计
- 🛡️ **故障保护**: 熔断器、超时保护、错误处理
- 🎯 **路径路由**: 基于URL前缀的智能请求分发

## 🚀 快速开始

### 基本使用

```python
from flask import Flask, jsonify
from flask_port_extension import enable_port_sharing

# 创建你的Flask应用
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Hello from my app!"})

# 启用端口复用（指定路径前缀）
enable_port_sharing(app, prefix="/myapp")

# 运行应用（这会启动轮询模式）
app.run()
```

### 运行多个应用

```python
import threading
import time
from flask import Flask
from flask_port_extension import enable_port_sharing, start_master_server

# 先启动主控服务器
start_master_server(host='127.0.0.1', port=5000)

# 创建第一个应用
app1 = Flask(__name__)
@app1.route('/')
def app1_home():
    return {"message": "这是应用1"}

enable_port_sharing(app1, prefix="/app1")

# 创建第二个应用
app2 = Flask(__name__)
@app2.route('/')
def app2_home():
    return {"message": "这是应用2"}

enable_port_sharing(app2, prefix="/app2")

# 在不同线程中运行应用
threading.Thread(target=lambda: app1.run(), daemon=True).start()
threading.Thread(target=lambda: app2.run(), daemon=True).start()

# 现在你可以访问:
# http://127.0.0.1:5000/app1/ -> 应用1
# http://127.0.0.1:5000/app2/ -> 应用2
```

## 📖 API 文档

### 主要函数

#### `enable_port_sharing(app, prefix="", master_host='127.0.0.1', master_port=5000)`

为Flask应用启用端口复用功能。

**参数:**
- `app` (Flask): Flask应用实例
- `prefix` (str): 应用的URL路径前缀，例如 "/api/v1"
- `master_host` (str): 主控服务器地址，默认 '127.0.0.1'
- `master_port` (int): 主控服务器端口，默认 5000

**返回:**
- `str`: 应用的唯一ID

#### `start_master_server(host='127.0.0.1', port=5000)`

手动启动主控服务器。

**参数:**
- `host` (str): 服务器监听地址
- `port` (int): 服务器监听端口

#### `get_master_server_status()`

获取主控服务器的状态信息。

**返回:**
- `dict`: 包含服务器状态、注册应用数量等信息

### 主控服务器管理端点

当主控服务器运行时，以下管理端点可用：

- `GET /_master/health` - 健康检查
- `GET /_master/apps` - 获取所有注册应用列表
- `GET /_master/stats` - 获取全局性能统计
- `GET /_master/stats/<app_id>` - 获取特定应用的性能统计

## ⚡ 性能优化

### 启用性能优化

```python
from flask_port_extension.performance import enable_performance_optimization

# 启用性能优化
enable_performance_optimization(
    max_requests_per_second=200,  # 全局每秒最大请求数
    max_requests_per_app=100,     # 每个应用每秒最大请求数
    max_connections=200,          # 最大连接数
    max_workers=100               # 最大工作线程数
)
```

### 性能特性

- **请求限流**: 防止系统过载
- **连接池管理**: 优化连接资源使用
- **异步处理**: 提高并发处理能力
- **性能监控**: 实时统计和指标收集
- **熔断器**: 故障自动恢复机制

## 🔧 高级配置

### 自定义性能参数

```python
from flask_port_extension.performance import PerformanceOptimizer

optimizer = PerformanceOptimizer(
    enable_monitoring=True,
    enable_throttling=True,
    enable_connection_pool=True,
    enable_async_processing=True,
    max_requests_per_second=500,
    max_requests_per_app=200,
    max_connections=1000,
    max_workers=200
)
```

### 应用优化

```python
from flask_port_extension.utils import optimize_flask_app

# 为应用添加额外优化
app = optimize_flask_app(
    app,
    enable_gzip=True,      # 启用Gzip压缩
    enable_caching=True,   # 启用缓存
    cache_timeout=300      # 缓存超时时间
)
```

## 🧪 运行演示

### 运行完整演示

```bash
cd flask-port-extension
python demo.py
```

### 运行单个应用示例

```bash
python examples.py single
```

### 运行多应用示例

```bash
python examples.py multi
```

### 运行性能测试

```bash
python examples.py perf
```

## 📊 监控和统计

### 获取性能统计

```python
from flask_port_extension import get_master_server_status
from flask_port_extension.performance import get_performance_optimizer

# 获取服务器状态
status = get_master_server_status()
print(f"活跃应用数: {status['active_apps']}")

# 获取性能统计
optimizer = get_performance_optimizer()
stats = optimizer.get_performance_stats()
print(f"平均响应时间: {stats['avg_duration']:.3f}秒")
```

### 通过HTTP获取统计

```bash
# 获取健康状态
curl http://127.0.0.1:5000/_master/health

# 获取应用列表
curl http://127.0.0.1:5000/_master/apps

# 获取性能统计
curl http://127.0.0.1:5000/_master/stats
```

## 🏗️ 架构原理

### 系统架构

```
外部请求 → 主控服务器 → 请求分发器 → 应用队列 → Flask应用
          ↑                                      ↓
       端口5000                               轮询响应
```

### 核心组件

1. **主控服务器 (MasterServer)**: 真正绑定端口的Flask服务器
2. **应用注册器 (AppRegistry)**: 管理所有注册的Flask应用
3. **请求分发器 (RequestDispatcher)**: 根据URL前缀分发请求
4. **应用包装器 (AppWrapper)**: 重写Flask应用的run方法
5. **性能优化器 (PerformanceOptimizer)**: 提供各种性能优化功能

### 工作流程

1. 调用 `enable_port_sharing()` 注册应用到主控服务器
2. 应用的 `run()` 方法被重写为轮询模式
3. 主控服务器接收外部请求，根据URL前缀找到对应应用
4. 请求通过队列传递给应用
5. 应用处理请求并通过响应队列返回结果
6. 主控服务器将响应返回给客户端

## 🔧 配置选项

### 环境变量

- `FLASK_PORT_SHARING_HOST`: 主控服务器主机地址（默认: 127.0.0.1）
- `FLASK_PORT_SHARING_PORT`: 主控服务器端口（默认: 5000）
- `FLASK_PORT_SHARING_LOG_LEVEL`: 日志级别（默认: INFO）

### 性能调优建议

1. **密集型应用**: 增加 `max_workers` 和 `max_requests_per_second`
2. **大文件传输**: 增加队列超时时间和连接池大小
3. **高并发场景**: 启用异步处理和请求批处理
4. **资源受限环境**: 降低各项限制参数

## 🛠️ 依赖要求

```
Flask>=2.0.0
Werkzeug>=2.0.0
requests>=2.25.0
```

可选依赖（用于额外优化）:
```
flask-compress>=1.0.0  # Gzip压缩
flask-caching>=1.10.0  # 缓存支持
```

## 📝 注意事项

1. **线程安全**: 所有组件都是线程安全的
2. **内存管理**: 队列有大小限制，防止内存溢出
3. **错误处理**: 完善的错误处理和恢复机制
4. **资源清理**: 应用停止时会自动清理资源

## 🚨 限制和注意事项

- 每个应用必须有唯一的URL前缀
- 不支持WebSocket长连接（需要额外实现）
- 静态文件服务需要特殊处理
- 某些Flask扩展可能需要适配

## 🤝 贡献

欢迎提交问题和功能请求！

## 📄 许可证


MIT License
