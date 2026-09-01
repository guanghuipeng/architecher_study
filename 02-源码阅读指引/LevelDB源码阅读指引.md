# LevelDB 源码阅读指引

> 目的：通过一个代码量小（~2 万行 C++）、架构清晰的存储引擎，理解存储系统的基本分层。
> 源码：https://github.com/google/leveldb
> 前置：C++ 基础即可，LevelDB 代码可读性极高。

---

## 入口地图

```
leveldb/
├── include/leveldb/
│   ├── db.h             ← 对外接口（DB 类）
│   ├── options.h        ← 读写选项
│   ├── write_batch.h    ← 批量写
│   └── iterator.h       ← 迭代器接口
├── db/
│   ├── db_impl.h/cc     ← DB 实现的核心入口
│   ├── version_set.h/cc ← 版本管理（MVCC）
│   ├── version_edit.h/cc← 版本变更记录
│   ├── log_reader.h/cc  ← WAL 日志读
│   ├── log_writer.h/cc  ← WAL 日志写
│   └── memtable.h/cc    ← 内存表（写缓冲）
├── table/
│   ├── table.h/cc       ← SSTable 文件格式
│   ├── table_builder.cc ← 构建 SSTable
│   ├── block.h/cc       ← SSTable 内的数据块
│   ├── block_builder.cc ← 构建数据块
│   ├── filter_block.h   ← 布隆过滤器
│   ├── two_level_iterator.h ← 两级迭代器
│   └── merger.h/cc      ← 归并迭代器
├── util/
│   ├── cache.cc         ← LRU 缓存
│   ├── arena.h/cc       ← 内存池
│   ├── bloom.cc         ← 布隆过滤器实现
│   └── coding.h/cc      ← 变长编码
└── port/                ← 平台适配
```

---

## Phase 1（Month 7）阅读清单

### 第 1 次：看架构分层（20 min）
不读代码，先看目录结构，回答：
1. 哪些是接口层（include/）？哪些是实现层？
2. db/ 和 table/ 的关系是什么？（db 是上层，table 是存储格式层）
3. util/ 提供什么？
4. **架构映射**：LevelDB 是典型的分层架构——接口层 → 逻辑层(db) → 存储格式层(table) → 工具层(util)

### 第 2 次：读一条写入的主流程（30 min，分 2 天）
- Day 1：`include/leveldb/db.h` → 看 DB::Put() 接口
- 然后看 `db/db_impl.cc` → `DBImpl::Put()` → 发现它把 Put 转成了 WriteBatch
- Day 2：`db/db_impl.cc` → `DBImpl::Write()` 函数
  - 理解：① 先写 WAL 日志 ② 再写 MemTable ③ 如果 MemTable 满了则触发 Compaction
  - **数据库融入点**：WAL = Write-Ahead Log，事务的原子性和持久性就靠它。对比你的 SQLite/MySQL 使用的 journal 机制。

### 第 3 次：MemTable 和跳表（20 min）
- 文件：`db/memtable.h` + `db/memtable.cc`
- 理解 MemTable 就是内存中的有序数据结构（跳表）
- `util/arena.h` → Arena 内存池如何管理 MemTable 的内存
- **OS 融入点**：Arena 减少频繁 malloc/free，对比 OS 卡片 Q16-17（malloc 和内存碎片）

---

## Phase 2（Month 11）阅读清单

### 第 4 次：SSTable 文件格式（30 min，分 2 天）
- Day 1：`table/table.h` → Table 类的接口
- `table/block.h` → 数据块的结构
- Day 2：`table/table_builder.cc` → 看 TableBuilder::Add() 怎么写数据
- `table/filter_block.h` → 布隆过滤器的位置
- **数据库融入点**：对照基础卡片 Q12-Q13，理解 SSTable 是不可变文件——写完后不再修改（和 B+Tree 的原地更新不同）

### 第 5 次：Compaction（合并压缩）（30 min）
- 文件：`db/version_set.cc` → 理解 Version 和 VersionEdit
- Compaction 就是把多个 SSTable 合并成新的 SSTable，删除重复和过期的 key
- **思考**：LSM-Tree 的写放大（write amplification）从哪来？（每次合并都要重写数据）
- **数据库融入点**：对照 Q12——LSM-Tree 写入快（顺序写），读取慢（可能查多个文件），B+Tree 写入慢（随机写），读取快

### 第 6 次：缓存系统（20 min）
- 文件：`util/cache.cc` → LRU 缓存实现
- `table/table.cc` → Table::Open() 时怎么用缓存
- **OS 融入点**：对比 OS 基础知识 Q22（page cache），用户态缓存和内核态缓存的分工和协同

---

## 扩展思考（周五写作日使用）
1. LevelDB 为什么用跳表而不用 B+Tree 做 MemTable？（跳表实现简单，并发友好）
2. 如果你的 Qt 产品需要一个本地嵌入式存储，LevelDB 适合吗？和 SQLite 比各有什么优劣？
3. 画一张写入流程图：Put → WAL → MemTable → flush → SSTable → Compaction
