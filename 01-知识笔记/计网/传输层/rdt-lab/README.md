# RDT 协议编程实验

## 文件结构

```
rdt-lab/
  rdt_channel.py   - 不可靠信道模拟器 + 测试框架 (已完成)
  rdt_1_0.py       - rdt1.0: 完美信道 (已完成, 阅读 + 运行)
  rdt_2_0.py       - rdt2.0: bit 出错, ACK/NAK (TODO 待填充)
  rdt_3_0.py       - rdt3.0: 丢包 + 出错, Stop-and-Wait 完整版 (已完成)
```

## 实验步骤

### Step 1: 运行 rdt1.0, 理解框架
```bash
cd rdt-lab
python rdt_1_0.py
```
观察:
- 完美信道上 3 条消息全部正确交付
- 不可靠信道上损坏的消息也被"交付"了 → 这就是为什么需要校验和

### Step 2: 完成 rdt2.0 (TODO 练习)
打开 `rdt_2_0.py`, 找到所有 `# TODO` 标记, 实现:
- Sender: rdt_send(), incoming_ack()
- Receiver: incoming_packet()

完成后运行:
```bash
python rdt_2_0.py
```
预期: 30% 出错率下仍能正确交付

### Step 3: 研究 rdt3.0
阅读 `rdt_3_0.py`, 理解:
- 序号只有 0 和 1 为什么够用
- 收到坏 ACK/NAK 为什么"忽略等超时"
- 定时器如何用轮次模拟

实验:
```bash
python rdt_3_0.py
```
修改 `timeout` 参数观察效果:
- timeout=5 → 过早超时, 大量不必要重传
- timeout=30 → 超时太慢, 浪费时间
- timeout=15 → 适中

### Step 4: 自行修改参数实验
编辑 `rdt_3_0.py` 底部的测试代码:
```python
# 试不同的信道参数
ch = UnreliableChannel(error_rate=0.0, loss_rate=0.5, seed=42)
# 试不同的 timeout
s = Sender3_0(timeout=5)  # vs timeout=30
```

## 扩展挑战 (可选)

1. **实现 rdt2.1**: 在 rdt2.0 基础上加序号, 解决坏 ACK/NAK 问题
2. **实现 rdt2.2**: 用重复 ACK 替代 NAK (NAK-free)
3. **实现 GBN**: 流水线 + 累积 ACK + 一个定时器
4. **实现 SR**: 流水线 + 逐个 ACK + 每包一个定时器 + 接收方缓冲
5. **观察性能**: 用 `channel.stats()` 统计重传次数, 对比 Stop-and-Wait vs GBN vs SR 的效率
