# Redis 源码阅读指引

> 目的：通过一个代码可读性极高的 C 项目，理解事件驱动、Reactor 模式、主从复制、集群。
> 源码：https://github.com/redis/redis
> 注意：Redis 代码约 10 万行，我们只看几个核心文件，不需要通读。

---

## 入口地图

```
redis/src/
├── server.h/c          ← 服务端核心（数据结构定义 + 主循环）
├── ae.h/ae.c           ← 事件驱动库（React 模式核心）
├── ae_epoll.c          ← epoll 封装（Linux）
├── ae_select.c         ← select 封装（跨平台）
├── networking.c        ← 客户端连接处理
├── db.c                ← 数据库操作（键值存储）
├── rdb.c               ← RDB 持久化
├── aof.c               ← AOF 持久化
├── replication.c       ← 主从复制
├── sentinel.c          ← Sentinel 高可用
├── cluster.c           ← 集群模式
├── dict.h/c            ← 哈希表实现
├── sds.h/c             ← 动态字符串
├── ziplist.c           ← 压缩列表（小数据优化）
├── zskiplist.c         ← 跳表（ZSet 底层结构）
└── object.c            ← 对象系统
```

---

## Phase 2 阅读清单（按顺序）

### 第 1 次：事件驱动核心（30 min，2 天）
- Day 1：`ae.h` → 理解 aeEventLoop 结构体
  - 只看三个字段：`events`（注册的事件）、`fired`（就绪的事件）、`apidata`（平台相关数据）
  - 理解 aeFileEvent：fd + mask(可读/可写) + 回调函数
- Day 2：`ae.c` → `aeMain()` 函数（主循环，不到 20 行）
  - `aeProcessEvents()` → 核心：调 aeApiPoll 等待事件 → 遍历就绪事件 → 回调
- **计网融入点**：对照计网卡片 Q24-Q25，理解 Redis 为什么在 Linux 下用 epoll 而不是 select

### 第 2 次：Reactor 模式全景（20 min）
- `ae.c` + `ae_epoll.c` → 看 aeCreateFileEvent 怎么注册事件
- 对比 `ae_select.c` → 看不同平台的差异
- **架构映射**：Redis 是经典的单线程 Reactor 模式——一个线程通过 epoll 管理所有客户端连接。这和 Qt 的 EventLoop 是同一个模式！

### 第 3 次：客户端连接处理（20 min）
- `networking.c` → 找 `acceptTcpHandler()` 函数
- 理解：新连接进来 → accept → 创建 client → 注册可读事件 → 回调 readQueryFromClient
- `readQueryFromClient()` → 读取请求 → 解析 RESP 协议 → 执行命令

### 第 4 次：RDB 持久化（20 min）
- `rdb.c` → 找 `rdbSave()` 和 `rdbLoad()` 
- 理解 RDB 是快照：某个时刻的内存数据全量写入磁盘
- **数据库融入点**：对比基础卡片 Q18（ACID），RDB 满足了持久性，但可能丢失最近写入（两次快照之间的数据）

### 第 5 次：AOF 持久化（20 min）
- `aof.c` → 找 `feedAppendOnlyFile()` 
- 理解 AOF 是写前日志（类似 WAL）：每条写命令先追加到 AOF 文件
- **数据库融入点**：AOF ≈ 数据库的 WAL 日志，对照 LevelDB 的 log_writer。为什么 AOF 文件会越来越大？因为命令只追加不删除。

### 第 6 次：主从复制（30 min，2 天）
- Day 1：`replication.c` → `replicationSetMaster()` 和 `syncWithMaster()`
- 理解全量同步：从库连主库 → 主库 fork 子进程做 RDB 快照 → 发送给从库 → 从库加载
- Day 2：`replication.c` → 部分同步（PSYNC）
- 理解复制积压缓冲区（replication backlog），记录主库的写命令用于增量同步
- **分布式融入点**：CAP 中 Redis 主从是 AP 还是 CP？（默认 AP，主从异步复制可能丢数据）

### 第 7 次：Sentinel 故障检测（20 min）
- `sentinel.c` → 理解 Sentinel 如何判定主库下线（主观下线 SDOWN → 客观下线 ODOWN）
- 理解哨兵之间通过 Pub/Sub 通道通信
- **分布式融入点**：故障检测的"多数派"原则，和 Raft 的选举有什么相似之处？

### 第 8 次：Cluster 分片（20 min）
- `cluster.c` → 理解 16384 个槽位的分配
- 理解 MOVED 重定向：客户端请求到了错误的节点，返回正确的节点地址
- **数据库融入点**：对比基础卡片 Q23（分库分表策略），Redis Cluster 是哈希分片，没有代理层

---

## 扩展思考（周五写作日使用）
1. 你的 Qt 产品如果需要一个缓存层，你会选 Redis 还是内存缓存？为什么？
2. Redis 的单线程 Reactor 和 Qt 的 EventLoop 有什么异同？
3. 如果有 10000 个客户端连 Redis，它怎么处理？（epoll 一个线程全搞定——这就是事件驱动 vs 多线程的区别）
