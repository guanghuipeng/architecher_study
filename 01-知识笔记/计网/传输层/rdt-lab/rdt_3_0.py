"""
RDT 实验 ---- rdt 3.0：信道会丢包！加定时器

rdt2.2 解决了 bit 错误，但假设信道不会丢包。
rdt3.0 面对的是真实的不可靠信道：包可能彻底消失（数据包或 ACK）。

新增机制：定时器（Timer）
  何时启动？ 发送包时（_packet_unsent = False 后，timer_ticks = 0）
  何时检查？ tick() 每轮被调用一次
  超时了？   重传 + 重启定时器
  何时停止？ 收到正确的 ACK

rdt3.0 的设计哲学：
  "收到坏 ACK？忽略。收到重复 ACK？忽略。
   所有这些不确定性问题，最终都由定时器超时来兜底。"
  定时器是最后的安全网。

运行：
  python rdt_3_0.py
"""

from typing import Optional
from rdt_channel import Packet, UnreliableChannel, checksum_ok, make_checksum, run_test


# ============================================================
#  rdt 3.0 Sender ---- 请你完成 TODO
# ============================================================

class Sender3_0:
    """
    rdt3.0 发送方 —— 在 rdt2.2 基础上加了定时器

    状态：同 rdt2.2, 4 个状态
    新变量：
      timer_ticks   — 定时器已计数的轮次
      timeout       — 超时阈值（轮次），构造函数传入
      retransmit_count — 统计：总重传次数
    """

    WAIT_CALL_0 = 0
    WAIT_ACK_0 = 1
    WAIT_CALL_1 = 2
    WAIT_ACK_1 = 3

    def __init__(self, timeout: int = 20):
        self.state = self.WAIT_CALL_0
        self.timeout = timeout
        self.pending_queue = []
        self.current_pkt = None
        self._packet_unsent = False

        # 定时器相关
        self.timer_ticks = 0
        self.retransmit_count = 0

    # ========================================
    #  TODO ①：上层有数据要发送 + 打包
    # ========================================
    def rdt_send(self, data: str):
        """
        同 rdt2.2：
          空闲 → 确定序号 → Packet(seq_num=seq, data=data) → 算校验和
               → current_pkt = pkt, _packet_unsent = True
               → timer_ticks = 0  （新增！启动定时器）
          忙   → 放入 pending_queue
        """
        # ----- 你的代码 -----
        if self.state == self.WAIT_CALL_0:
          seq = 0
          pkt = Packet(seq_num=seq, data=data)
          pkt.checksum = make_checksum(pkt)
          self.current_pkt = pkt
          self._packet_unsent = True
          self.state = self.WAIT_ACK_0
          self.timer_ticks = 0
        elif self.state == self.WAIT_CALL_1:
          seq = 1
          pkt = Packet(seq_num=seq, data=data)
          pkt.checksum = make_checksum(pkt)
          self.current_pkt = pkt
          self._packet_unsent = True
          self.state = self.WAIT_ACK_1
          self.timer_ticks = 0
        else:
          self.pending_queue.append(data)
        pass
        # --------------------

    # ========================================
    #  TODO ②：收到 ACK
    # ========================================
    def incoming_ack(self, pkt: Packet):
        """
        收到 ACK 包。

        注意：rdt3.0 对重复 ACK 不再当 NAK 处理！
        重复 ACK 直接忽略 —— 丢包统一由定时器兜底。

        你需要：
          1. 校验和不通过 → 忽略
          2. 校验和通过：
             ack_num 和当前期望的匹配？
               → 新 ACK！切状态
               → timer_ticks = 0（停止定时器，下次发送才重启）
               → 如果队列有排队的消息 → 组装发送新包
             ack_num 不匹配？
               → 忽略（让定时器兜底）
        """
        # ----- 你的代码 -----
        if not checksum_ok(pkt):
          pass
        if not pkt.is_ack:
          pass
        self.timer_ticks = 0
        if self.state == self.WAIT_ACK_0 and pkt.ack_num == 0:
          self.timer_ticks = 0
          self.state = self.WAIT_CALL_1
          if self.pending_queue:
            self.rdt_send(self.pending_queue.pop(0))
        elif self.state == self.WAIT_ACK_1 and pkt.ack_num == 1:
          self.state = self.WAIT_CALL_0
          if self.pending_queue:
            self.rdt_send(self.pending_queue.pop(0))
        else:
          pass
        pass
        # --------------------

    # ========================================
    #  TODO ③：定时器 —— rdt3.0 的核心新功能！
    # ========================================
    def tick(self):
        """
        每轮调用一次。

        你需要：
          如果正在等 ACK（state in [WAIT_ACK_0, WAIT_ACK_1]）:
            timer_ticks += 1
            如果 timer_ticks >= timeout:
              - 超时了！重传当前包
              - 重新计算校验和
              - _packet_unsent = True
              - retransmit_count += 1
              - timer_ticks = 0（重启定时器）
        """
        # ----- 你的代码 -----
        if self.state == self.WAIT_ACK_0 or self.state == self.WAIT_ACK_1:
            self.timer_ticks += 1
            if self.timer_ticks >= self.timeout:
                self._packet_unsent = True
                self.retransmit_count += 1
                self.timer_ticks = 0
        pass
        # --------------------

    # ========================================
    #  TODO ④：产生要发送的包
    # ========================================
    def outgoing_packet(self) -> Optional[Packet]:
        """
        同 rdt2.2：
          if current_pkt 存在 且 _packet_unsent == True:
              _packet_unsent = False
              return current_pkt
          return None
        """
        # ----- 你的代码 -----
        if self.current_pkt and self._packet_unsent:
          self._packet_unsent = False
          return self.current_pkt
        return None
        pass
        # --------------------

    @property
    def pending(self) -> int:
        waiting = 1 if self.state in (self.WAIT_ACK_0, self.WAIT_ACK_1) else 0
        return len(self.pending_queue) + waiting


# ============================================================
#  rdt 3.0 Receiver ---- 请你完成 TODO
# ============================================================

class Receiver3_0:
    """
    rdt3.0 接收方 —— 和 rdt2.2 逻辑基本相同

    唯一变化：收到坏包时直接忽略，不发任何东西。
    丢包统一由发送方的定时器兜底。
    """

    WAIT_0 = 0
    WAIT_1 = 1

    def __init__(self):
        self.state = self.WAIT_0
        self.delivered_messages = []
        self._ack_to_send = None

    # ========================================
    #  TODO ⑤：收到数据包
    # ========================================
    def incoming_packet(self, pkt: Packet):
        """
        收到数据包。

        三种情况：

        A. checksum_ok(pkt) == False（损坏）
           → 直接忽略！不发任何东西
           → 丢包 + 损坏都交给发送方定时器兜底

        B. 校验和正确 + seq 是我期望的
           → 交付 deliver(pkt.data)
           → 切状态
           → 发 ACK，ack_num = 新期望的序号

        C. 校验和正确 + seq 不是期望的（重复包）
           → 不交付数据
           → 重发 ACK（因为上次的 ACK 可能丢了导致发送方重传）
        """
        # ----- 你的代码 -----
        if not checksum_ok(pkt):
          pass
        elif self.state == self.WAIT_0 and pkt.seq_num == 0:
          self.deliver(pkt.data)
          self.state = self.WAIT_1
          ack = Packet(is_ack = True)
          ack.ack_num = 0
          ack.checksum = make_checksum(ack)
          self._ack_to_send = ack
        elif self.state == self.WAIT_1 and pkt.seq_num == 1:
          self.deliver(pkt.data)
          self.state = self.WAIT_0
          ack = Packet(is_ack = True)
          ack.ack_num = 1
          ack.checksum = make_checksum(ack)
          self._ack_to_send = ack
        else:
          ack = Packet(is_ack = True)
          
          if self.state == self.WAIT_0:
            ack.ack_num = 1
          else:
            ack.ack_num = 0
          ack.checksum = make_checksum(ack)
          self._ack_to_send = ack
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

def run_one_test(name, error_rate, loss_rate, seed, num_msgs, timeout, max_rounds):
    ch = UnreliableChannel(error_rate=error_rate, loss_rate=loss_rate, seed=seed, verbose=False)
    s, r = Sender3_0(timeout=timeout), Receiver3_0()
    ok, rounds = run_test(s, r, ch, num_messages=num_msgs, verbose=False, max_rounds=max_rounds)
    return {
        "name": name, "ok": ok, "rounds": rounds,
        "retrans": s.retransmit_count,
        "ch_sent": ch.total_sent, "ch_lost": ch.total_lost, "ch_corrupt": ch.total_corrupted,
    }


if __name__ == "__main__":
    results = []

    # 测试 1：无错误无丢包 — 基线
    results.append(run_one_test("无错误无丢包", 0.0, 0.0, 42, 8, 20, 200))

    # 测试 2：仅丢包 10%
    results.append(run_one_test("丢包 10%", 0.0, 0.10, 42, 8, 15, 300))

    # 测试 3：仅出错 20%
    results.append(run_one_test("出错 20%", 0.2, 0.0, 456, 8, 15, 300))

    # 测试 4：丢包 20% + 出错 10% — 地狱模式
    results.append(run_one_test("丢包 20% + 出错 10%", 0.1, 0.2, 99, 8, 15, 500))

    # 测试 5：极端丢包 40% — 验证定时器兜底
    results.append(run_one_test("极端丢包 40%", 0.0, 0.4, 555, 5, 12, 500))

    # 测试 6：短超时(3轮) — 应该能工作但重传多
    results.append(run_one_test("短超时(3轮) + 丢包 10%", 0.0, 0.1, 42, 5, 3, 300))

    # ---- 汇总报告 ----
    print("\n" + "=" * 70)
    print("  rdt 3.0 测试报告")
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
        print("  提示：")
        print("    - tick() 只在 WAIT_ACK 状态才会计数")
        print("    - 超时后要重置 timer_ticks = 0")
        print("    - 收到正确 ACK 后也要重置 timer_ticks = 0")
