# Qt 源码阅读指引

> 目的：用你已经熟悉的 Qt 作为架构教材，理解它内部的架构决策。
> Qt 源码地址：https://code.qt.io/cgit/qt/qtbase.git/ 或 GitHub mirror。
> 本指引假设你使用 Qt5 或 Qt6，结构基本一致。

---

## 入口地图

```
qtbase/src/
├── corelib/          ← Phase 1 重点：核心库
│   ├── kernel/       ← 元对象系统、信号槽、事件循环
│   ├── thread/       ← 多线程
│   ├── io/           ← 文件 I/O
│   ├── plugin/       ← 插件系统
│   └── tools/        ← 工具类（容器、字符串等）
├── gui/              ← 图形系统
├── widgets/          ← 控件库
├── network/          ← 网络模块
│   └── socket/       ← QTcpSocket 等
└── sql/              ← 数据库驱动
```

---

## Phase 1 阅读清单（按顺序）

### 第 1 次：模块划分（30 min）
不读代码，只看目录结构：
1. 打开 `qtbase/src/`，列出所有子目录
2. 理解每个子目录的职责
3. 看 `corelib/kernel/` 下的文件列表，感受"内核"的粒度
4. **思考**：Qt 是怎么分层的？为何 corelib 在 gui 下面？这样分层有什么好处？（面向 Phase 1 的"架构风格"主题）

### 第 2 次：元对象系统入门（30 min）
- 文件：`corelib/kernel/qobject.h` → 看 QObject 类的声明（前 200 行）
- 找 Q_OBJECT 宏 → 理解它展开后生成什么（在 qobjectdefs.h 中）
- 找 `QMetaObject` 类声明 → 理解元数据的存储结构
- **架构映射**：这是"反射模式"在 C++ 中的实现，C++ 没有原生反射，Qt 通过 moc（元对象编译器）预处理来实现。

### 第 3 次：信号槽机制（30 min，分 2 天）
- Day 1：`corelib/kernel/qobject.cpp` → 找 `QObject::connect()` 函数实现
  - 理解信号槽的连接存储（QObjectPrivate::Connection）
  - 理解连接类型：AutoConnection / DirectConnection / QueuedConnection
- Day 2：`corelib/kernel/qobject.cpp` → 找 `QMetaObject::activate()` 函数
  - 理解信号发射时发生了什么
  - 理解 Qt::QueuedConnection 如何通过事件系统实现跨线程
- **架构映射**：观察者模式 + 事件驱动。为什么 Qt 不直接让信号 = 函数指针？因为要支持跨线程队列调用和动态信号槽。

### 第 4 次：事件循环（30 min，分 2 天）
- Day 1：`corelib/kernel/qabstracteventdispatcher.h` → 接口定义
  - 理解 EventDispatcher 的抽象：processEvents、registerSocketNotifier
- Day 2：`corelib/kernel/qeventloop.cpp` → `QEventLoop::exec()` 
  - 理解事件循环的主循环结构
  - 理解 Qt 在不同平台怎么选底层实现（select/poll/epoll/kqueue）
- **OS 融入点**：对照 OS 基础卡片 Q24（epoll 原理），理解 Qt 的事件循环在 Linux 下基于 epoll。

### 第 5 次：插件系统（20 min）
- 文件：`corelib/plugin/qpluginloader.cpp`
- `corelib/plugin/qfactoryinterface.h`
- 理解 Qt 的插件机制：接口类（QFactoryInterface）+ 加载器（QPluginLoader）+ 元数据
- **架构映射**：微内核模式——Qt 应用通过插件扩展功能，核心框架不知道插件的实现。

### 第 6 次：Model/View 框架（20 min）
- 文件：`corelib/itemmodels/qabstractitemmodel.h`
- 理解 QAbstractItemModel 的接口：index、data、rowCount
- 理解 QModelIndex 的设计——为什么用 createIndex(row, col, internalPointer) 而不是存指针？
- **架构映射**：分层模式 + 适配器模式。Model 不知道 View 长什么样，View 不知道数据从哪来。

### 第 7 次：网络模块（20 min）
- 文件：`network/socket/qtcpsocket.h` → QTcpSocket 类声明
- `network/socket/qiodevice.h` → QIODevice 基类
- 理解继承链：QIODevice → QAbstractSocket → QTcpSocket
- **架构映射**：模板方法模式——QIODevice 定义读写的框架，子类实现具体的读写逻辑。

---

## 持续阅读建议

- 每次只看 1-2 个函数或一个类的声明，不要贪多
- 读完一个类后，在你的项目里追溯它的使用——你是怎么调它的
- 记录每个"原来如此"的时刻（周五写作日用）
