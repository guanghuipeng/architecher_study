# gRPC C++ 源码阅读指引

> 目的：理解 RPC 框架的设计——序列化、多路复用、拦截器链。
> 源码：https://github.com/grpc/grpc
> 注意：gRPC 代码量大，主要看架构和核心概念，不追实现细节。

---

## 入口地图

```
grpc/
├── include/grpcpp/
│   ├── create_channel.h       ← 创建连接
│   ├── server_builder.h       ← 服务端构建
│   ├── completion_queue.h     ← 完成队列（异步核心）
│   └── impl/codegen/
│       ├── service_type.h     ← 服务定义
│       └── rpc_method.h       ← RPC 方法定义
├── src/core/
│   ├── surface/server.cc      ← 服务端实现
│   └── transport/             ← 传输层（HTTP/2）
└── examples/protos/           ← Proto 示例
```

---

## 阅读清单（Phase 2 使用）

### 第 1 次：理解 Proto → 代码生成（20 min）
- 找一个简单的 .proto 文件（如 `examples/protos/helloworld.proto`）
- 看生成的 `.grpc.pb.h` 文件，理解：
  - 生成的 Service 基类
  - 生成的 Stub（客户端代理类）
  - 序列化/反序列化代码在哪（.pb.h 中，由 protobuf 生成）
- **架构映射**：IDL（接口定义语言）+ 代码生成 = 开发时定义接口，编译时生成胶水代码。Qt 的 moc 也是这个模式！

### 第 2 次：同步 RPC 的调用链（20 min）
- `include/grpcpp/create_channel.h` → 理解 Channel 的创建
- Stub 的方法调用 → 底层实际做了什么？（序列化 → HTTP/2 → 网络 → 反序列化）
- 画一条调用链：客户端调用 SayHello() → stub → channel → HTTP/2 → 网络 → server → service 实现

### 第 3 次：理解 CompletionQueue（异步核心）（30 min）
- `include/grpcpp/completion_queue.h` → CompletionQueue 类
- 理解异步模式：向 CQ 注册一个 tag → 操作完成时 tag 出现在 CQ 中 → 应用从 CQ 取 tag 处理
- **架构映射**：gRPC 的 CompletionQueue 是 Proactor 模式——操作在内核/IO 线程完成，完成后通知应用。对比 Qt 的 EventLoop（Reactor 模式）。

### 第 4 次：拦截器链（20 min）
- 搜索 `Interceptor` 或 `ServerInterceptor` 相关头文件
- 理解拦截器是一个调用链：请求 → 拦截器1 → 拦截器2 → 实际处理函数 → 拦截器2 → 拦截器1 → 响应
- **架构映射**：责任链模式 + AOP（面向切面编程）。Qt 的 QIODevice 也有类似的链式处理（通过继承），但 gRPC 的拦截器更加灵活。

### 第 5 次：HTTP/2 传输层（20 min）
- 不需要看源码，读 gRPC 官方文档的 "gRPC over HTTP/2" 部分
- 理解：一个 HTTP/2 连接承载多个 stream（多路复用），每个 stream 承载一个 RPC 调用
- 理解 gRPC 的四种调用模式：一元 RPC、服务端流、客户端流、双向流
- **计网融入点**：对照计网卡片 Q11（HTTP/2），理解多路复用为什么解决了 HTTP/1.1 的队头阻塞

---

## 核心理解点

gRPC 的设计拆出几个独立关注点：
1. **IDL + 代码生成**（protobuf）——定义接口，编译时生成代码
2. **传输层**（HTTP/2）——多路复用、流控、帧格式
3. **拦截器**——可插拔的中间件（认证、日志、限流）
4. **负载均衡与命名解析**——服务发现

这四层互相独立，各自演化。好的架构设计就是这种——每一层只做一件事，接口清晰。

---

## 扩展思考（周五写作日使用）
1. 你的 Qt 产品的通信组件如果要升级为 RPC 框架，你会加哪些层？
2. gRPC 的拦截器和 Qt 信号槽的 filters/events 有什么区别？
3. 为什么 gRPC 选择 HTTP/2 而不是直接用 TCP？好处和代价是什么？
