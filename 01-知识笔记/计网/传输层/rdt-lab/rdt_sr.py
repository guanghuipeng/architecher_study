"""
RDT 实验 ---- Selective Repeat (SR)

GBN 的问题：一个包丢了，后面所有正确收到的包都要重传。
SR 的改进：只重传真正丢了的那个包，其他正确的不重传。

SR 的核心规则：
  - 接收方缓存乱序包（不再丢弃！）
  - 每个包独立确认（不是累积确认）
  - 每个包有独立的定时器
  - 只重传超时的那个包

和 GBN 的关键区别：
                    GBN                    SR
  ACK 类型          累积 ACK              逐个独立 ACK
  定时器            1个（最老的包）        每个未确认包 1 个
  丢包时重传        从丢的开始全部重发     只重传丢的那个
  乱序包            丢弃                  缓存
  接收方缓冲        不需要                 需要
  窗口约束          <= N-1                 <= N/2 (Sw+Rw <= 序号空间)

运行：
  python rdt_sr.py
"""

from typing import Optional, List, Dict
from rdt_channel import Packet, UnreliableChannel, checksum_ok, make_checksum


# ============================================================
#  流水线测试框架 (同 GBN)
# ============================================================

def run_test_pipelined(sender, receiver, channel, num_messages: int = 10,
                       max_rounds: int = 500, verbose: bool = True):
    """流水线版测试框架：每轮可发多个包。"""
    for i in range(num_messages):
        msg = f"MSG_{i}"
        sender.rdt_send(msg)

    round_count = 0
    while receiver.delivered_count < num_messages and round_count < max_rounds:
        round_count += 1

        # Drain sender
        while True:
            pkt = sender.outgoing_packet()
            if pkt is None:
                break
            delivered = channel.transmit(pkt, "S->R")
            if delivered is not None:
                receiver.incoming_packet(delivered)

        # ACKs back
        ack_pkt = receiver.outgoing_ack()
        if ack_pkt is not None:
            delivered = channel.transmit(ack_pkt, "R->S")
            if delivered is not None:
                sender.incoming_ack(delivered)

        sender.tick()

        if verbose and round_count <= 80:
            print(f"  [第{round_count}轮] sender窗口:[{sender.base},{sender.base + sender.window_size}) "
                  f"in_flight:{sorted(sender.in_flight.keys())} "
                  f"receiver已交付:{receiver.delivered_count}/{num_messages}")

    if verbose:
        if receiver.delivered_count == num_messages:
            print(f"\n[OK] 所有 {num_messages} 条消息成功交付! 用了 {round_count} 轮")
        else:
            print(f"\n[FAIL] 超时! 只交付了 {receiver.delivered_count}/{num_messages}")
        channel.stats()
        print(f"  发送方重传次数: {sender.retransmit_count}")

    return receiver.delivered_count == num_messages, round_count


# ============================================================
#  SR Sender ---- 请你完成 TODO
# ============================================================

class SenderSR:
    """
    SR 发送方

    窗口: [base, base + window_size)
    base — 窗口左边界（最老的未确认序号）
    nextseq — 下一个可用的序号

    和 GBN 的关键不同：
      1. 每个包有独立的定时器（timer_ticks[seq]）
      2. 收到 ACK(n) 只确认包 n 这一个包（不是累积确认！）
      3. 如果 n == base，窗口可以向前滑动（滑过所有连续已确认的包）
      4. 每个包超时也独立处理

    窗口大小约束：window_size <= SEQ_SPACE // 2
    """

    SEQ_SPACE = 16    # 序号空间
    MAX_SEQ = 65535   # 实际序号可以很大，用 mod 循环

    def __init__(self, window_size: int = 4, timeout: int = 20):
        self.window_size = window_size
        self.timeout = timeout

        # 滑动窗口
        self.base = 0
        self.nextseq = 0

        # 缓冲区
        self.pending_queue: List[str] = []
        self.packets: Dict[int, Packet] = {}          # {seq: Packet} 所有已打包但未发送的
        self.in_flight: Dict[int, Packet] = {}        # {seq: Packet} 已发送但未确认
        self.acked: set = set()                       # 已确认的 seq（但窗口还没滑动到的）

        # 每个包的独立定时器
        self.timer_ticks: Dict[int, int] = {}

        # 统计
        self.retransmit_count = 0

    # ========================================
    #  TODO ①：上层注入 + 尝试发送
    # ========================================
    def rdt_send(self, data: str):
        """放入队列，尝试打包发送。"""
        # ----- 你的代码 -----
        pass
        # --------------------

    # ========================================
    #  TODO ②：打包发送
    # ========================================
    def _try_send(self):
        """
        只要窗口有空位 + 队列有数据，就连续打包。

        你需要：
          1. 检查窗口是否已满：len(in_flight) >= window_size？
          2. 从 pending_queue 取数据
          3. 用 (self.base + len(self.in_flight) + len(self.packets)) % SEQ_SPACE 确定 seq
             或者维护一个 nextseq 指针
          4. 创建 Packet，计算校验和
          5. 放入 packets 字典（标记为"待发送"）
          6. 循环直到窗口满或队列空
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    # ========================================
    #  TODO ③：收到 ACK —— SR 的关键新逻辑
    # ========================================
    def incoming_ack(self, pkt: Packet):
        """
        收到 ACK 包。

        SR 的 ACK 是独立确认，不是累积确认！
        ACK(n) 只表示"包 n 收到了"，不表示 n 之前的都收到了。

        你需要：
          1. 校验和不通过 → 忽略
          2. 取出 ack_num
          3. 在 in_flight 中找到这个 seq → 已确认！
             - 从 in_flight 移除
             - 停止该 seq 的定时器
             - 加入 acked 集合
          4. 尝试滑动窗口：
             只要 base 在 acked 中，就一直前移 base
             while self.base in self.acked:
                 self.acked.remove(self.base)
                 self.base = (self.base + 1) % MAX_SEQ
          5. 调用 _try_send() —— 窗口有空位了
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    # ========================================
    #  TODO ④：定时器 —— SR 的核心
    # ========================================
    def tick(self):
        """
        每轮调用。

        和 GBN 不同，SR 的每个未确认包都有独立定时器。

        你需要：
          遍历 in_flight 中的所有 seq：
            1. timer_ticks[seq]++
            2. 如果 >= timeout：
               - 超时！重传这个包
               - retransmit_count++
               - 重置这个包的定时器
               - 把包放回"待发送"（或直接通过 _need_send 机制发出）
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    # ========================================
    #  TODO ⑤：产生要发送的包
    # ========================================
    def outgoing_packet(self) -> Optional[Packet]:
        """
        框架循环调用。

        SR 的挑战：packets 里可能有多个待发送的包。
        每次调用返回其中一个（含首次发送和重传）。

        提示：
          - 用一个队列或列表追踪待发送的包
          - 或者用 _send_queue 来管理
          - 重传的包也需要通过这里发出

        思路：维护 self._send_queue = [] (seq 列表)
              在 _try_send 时把新包的 seq 加入
              需要重传时也把 seq 加入
              这里按序返回
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    @property
    def pending(self) -> int:
        return len(self.pending_queue) + len(self.in_flight)


# ============================================================
#  SR Receiver ---- 请你完成 TODO
# ============================================================

class ReceiverSR:
    """
    SR 接收方

    和 GBN 的关键区别：
      - GBN：乱序包 → 丢弃
      - SR：  乱序包 → 缓存！（存在 buffer 里）

    窗口: [expected, expected + window_size)
    收到窗口内的任何包 → 缓存 + 发 ACK
    收到窗口外的包 → 忽略（或发 ACK，看实现）

    当 expected 序号的包到达 → 连续交付所有缓存中连续的包
    """

    def __init__(self, window_size: int = 4):
        self.window_size = window_size
        self.expected = 0           # 期望的下一个序号
        self.delivered_messages: List[str] = []
        self.buffer: Dict[int, str] = {}   # 缓存的乱序包 {seq: data}
        self._ack_to_send: Optional[Packet] = None

    # ========================================
    #  TODO ⑥：收到数据包 —— SR 接收方的核心
    # ========================================
    def incoming_packet(self, pkt: Packet):
        """
        收到数据包。

        和 GBN 完全不同！乱序包不丢弃，而是缓存。

        你需要：
          1. 校验和不通过 → 忽略
          2. 校验和通过：
             a. seq 是否在接收窗口内？
                窗口范围 = [self.expected, self.expected + self.window_size)
                （注意序号可能回绕，需要处理 mod）

                在窗口内：
                  - 缓存数据到 self.buffer[seq]
                  - 发 ACK(seq)（独立确认！）
                  - 如果 seq == self.expected：
                    连续交付！while self.expected in self.buffer:
                              交付 self.buffer.pop(self.expected)
                              self.expected++
                不在窗口内：
                  - 发 ACK(seq) 告知"我收到了"（可选，取决于实现）
                  - 或忽略
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    def deliver(self, data: str):
        self.delivered_messages.append(data)
        print(f"  [Receiver] [Deliver] 交付上层: '{data}'")

    def outgoing_ack(self) -> Optional[Packet]:
        ack = self._ack_to_send
        self._ack_to_send = None
        return ack

    @property
    def delivered_count(self) -> int:
        return len(self.delivered_messages)


# ============================================================
#  测试
# ============================================================

def run_one_test(name, window_size, error_rate, loss_rate, seed, num_msgs, timeout, max_rounds):
    """运行一次 SR 测试"""
    ch = UnreliableChannel(error_rate=error_rate, loss_rate=loss_rate, seed=seed, verbose=False)
    s, r = SenderSR(window_size=window_size, timeout=timeout), ReceiverSR(window_size=window_size)
    ok, rounds = run_test_pipelined(s, r, ch, num_messages=num_msgs, verbose=False, max_rounds=max_rounds)
    return {
        "name": name,
        "ok": ok,
        "rounds": rounds,
        "retrans": s.retransmit_count,
        "ch_sent": ch.total_sent,
        "ch_lost": ch.total_lost,
        "ch_corrupt": ch.total_corrupted,
    }


if __name__ == "__main__":
    results = []

    # 测试 1：无错误无丢包 — 验证流水线
    results.append(run_one_test("无错误无丢包 (窗口=4)", 4, 0.0, 0.0, 42, 10, 20, 200))

    # 测试 2：轻丢包 — 验证 SR 只重传丢的
    results.append(run_one_test("丢包 5% (窗口=4)", 4, 0.0, 0.05, 42, 10, 15, 300))

    # 测试 3：重丢包 — SR 应该比 GBN 更高效（少重传）
    results.append(run_one_test("丢包 10% (窗口=4)", 4, 0.0, 0.10, 123, 10, 15, 500))

    # 测试 4：丢包 + 出错
    results.append(run_one_test("丢包 10% + 出错 10% (窗口=4)", 4, 0.1, 0.1, 99, 10, 15, 500))

    # 测试 5：大窗口 — 验证窗口约束 w <= N/2
    results.append(run_one_test("大窗口 (窗口=8) + 丢包 10%", 8, 0.0, 0.1, 42, 15, 15, 500))

    # 测试 6：极端丢包 — 压力测试
    results.append(run_one_test("极端丢包 30% (窗口=4)", 4, 0.0, 0.3, 777, 8, 12, 500))

    # ---- 汇总报告 ----
    print("\n" + "=" * 70)
    print("  SR (Selective Repeat) 测试报告")
    print("=" * 70)
    passed = 0
    for i, r in enumerate(results, 1):
        status = "[OK]" if r["ok"] else "[FAIL]"
        if r["ok"]:
            passed += 1
        print(f"  {i}. {r['name']}")
        print(f"     {status} | {r['rounds']}轮 | 重传{r['retrans']}次 | "
              f"信道:发{r['ch_sent']}/丢{r['ch_lost']}/错{r['ch_corrupt']}")
    print(f"\n  总计: {passed}/{len(results)} 通过")
    if passed < len(results):
        print("  提示：如果中高丢包率测试失败，检查：")
        print("    1. 乱序包是否被正确缓存？")
        print("    2. 连续交付逻辑是否正确（while 循环）？")
        print("    3. 独立定时器是否正确处理？")
        print("    4. 窗口滑动时是否清理了旧定时器？")
