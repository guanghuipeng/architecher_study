"""
RDT 实验 ---- rdt 2.2：NAK-free 协议（TCP 的思想来源）

rdt2.1 用了 ACK + NAK 两种反馈。
rdt2.2 的思想：能不能只用一种？只用 ACK，NAK 用"重复 ACK"来替代。

为什么这样做？
  少一种消息类型 = 协议更简单。TCP 用的就是这种思路。

rdt2.2 的核心规则：
  接收方：收到坏包 → 不发 NAK，而是重发上一个正确的 ACK（"重复 ACK"）
  发送方：两次收到同样的 ACK → 知道出问题了 → 重传

关键：发送方怎么区分"新 ACK"和"重复 ACK"？
  self.last_acked 记录上次收到的 ACK 号
  新 ACK：ack_num != last_acked  → 确认了新包 → 前进
  重复 ACK：ack_num == last_acked → 隐含 NAK → 重传

运行：
  python rdt_2_2.py
"""

from typing import Optional
from rdt_channel import Packet, UnreliableChannel, checksum_ok, make_checksum, run_test


# ============================================================
#  rdt 2.2 Sender ---- 请你完成 TODO
# ============================================================

class Sender2_2:
    """
    rdt2.2 发送方 —— 和 rdt2.1 结构一样，但处理 ACK 的逻辑变了

    新增：self.last_acked —— 记录上次成功收到的 ACK 号
      收到 ACK(n) 时：
        n != last_acked → 新 ACK！确认了当前包
        n == last_acked → 重复 ACK！等同于 rdt2.1 收到 NAK
    """

    WAIT_CALL_0 = 0
    WAIT_ACK_0 = 1
    WAIT_CALL_1 = 2
    WAIT_ACK_1 = 3

    def __init__(self):
        self.state = self.WAIT_CALL_0
        self.pending_queue = []
        self.current_pkt = None
        self._packet_unsent = False
        self.last_acked = -1   # 上次收到的 ACK 号，-1 表示还没收到过

    # ========================================
    #  TODO ①：上层有数据要发送 + 打包（同 rdt2.1）
    # ========================================
    def rdt_send(self, data: str):
        """
        和 rdt2.1 一样：
          空闲 → 确定序号 → Packet(seq_num=seq, data=data) → 算校验和
               → current_pkt = pkt, _packet_unsent = True
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
        elif self.state == self.WAIT_CALL_1:
          seq = 1
          pkt = Packet(seq_num=seq, data=data)
          pkt.checksum = make_checksum(pkt)
          self.current_pkt = pkt
          self._packet_unsent = True
          self.state = self.WAIT_ACK_1
        else:
          self.pending_queue.append(data)
        pass
        # --------------------

    # ========================================
    #  TODO ②：收到 ACK —— rdt2.2 的新逻辑！
    # ========================================
    def incoming_ack(self, pkt: Packet):
        """
        收到 ACK 包。注意：rdt2.2 不再有 NAK！

        你需要：
          1. checksum_ok(pkt) 检查校验和
             坏了 → 忽略

          2. 校验和正确，比较 pkt.ack_num 和 self.last_acked：

             不同 → 新 ACK！
               更新 self.last_acked = pkt.ack_num
               切到对应的 WAIT_CALL 状态
               如果队列有排队的消息 → 组装发送新包

             相同 → 重复 ACK！（这就是 rdt2.1 里 NAK 的替代品）
               重新计算 current_pkt 的校验和
               _packet_unsent = True  （触发重传）
        """
        # ----- 你的代码 -----
        if not checksum_ok(pkt):
          self._packet_unsent = True
        elif pkt.ack_num == self.last_acked:
          self._packet_unsent = True
        elif pkt.ack_num != self.last_acked:
          self.last_acked = pkt.ack_num
          if self.state == self.WAIT_ACK_0 and pkt.ack_num == 0:
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
    #  TODO ③：产生要发送的包（同 rdt2.1）
    # ========================================
    def outgoing_packet(self) -> Optional[Packet]:
        """
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

    def tick(self):
        pass

    @property
    def pending(self) -> int:
        waiting = 1 if self.state in (self.WAIT_ACK_0, self.WAIT_ACK_1) else 0
        return len(self.pending_queue) + waiting


# ============================================================
#  rdt 2.2 Receiver ---- 请你完成 TODO
# ============================================================

class Receiver2_2:
    """
    rdt2.2 接收方 —— 不再发 NAK！只用 ACK。

    关键变化：
      rdt2.1: 坏包 → NAK
      rdt2.2: 坏包 → 重复上一���的 ACK

    self.last_correct_ack 记录上一次正确交付后发的 ACK 号
    """

    WAIT_0 = 0
    WAIT_1 = 1

    def __init__(self):
        self.state = self.WAIT_0
        self.delivered_messages = []
        self._ack_to_send = None
        self.last_correct_ack = -1   # 上一次正确交付后发的 ACK 号

    # ========================================
    #  TODO ④：收到数据包 —— NAK-free 的核心
    # ========================================
    def incoming_packet(self, pkt: Packet):
        """
        收到数据包。不再发 NAK！

        三种情况：

        A. checksum_ok(pkt) == False（损坏）
           → 不发 NAK！
           → 发一个 ACK，ack_num = self.last_correct_ack（重复 ACK）
           → 这就是 NAK 的替代品！

        B. 校验和正确 + seq 是我期望的
           → 交付 deliver(pkt.data)
           → 切状态
           → 更新 self.last_correct_ack = 新 ACK 号
           → 发新 ACK，ack_num = 新期望的序号

        C. 校验和正确 + seq 不是期望的（重复包）
           → 不交付数据
           → 发 ACK，ack_num = self.last_correct_ack（重复 ACK）
           → 因为上次的 ACK 可能丢了
        """
        # ----- 你的代码 -----
        if not checksum_ok(pkt):
          ack = Packet(is_ack = True)
          ack.ack_num = self.last_correct_ack
          ack.checksum = make_checksum(ack)
          self._ack_to_send = ack
        elif self.state == self.WAIT_0 and pkt.seq_num == 0:
          self.deliver(pkt.data)
          self.state = self.WAIT_1
          ack = Packet(is_ack = True)
          ack.ack_num = 0
          ack.checksum = make_checksum(ack)
          self._ack_to_send = ack
          self.last_correct_ack = pkt.seq_num 
        elif self.state == self.WAIT_1 and pkt.seq_num == 1:
          self.deliver(pkt.data)
          self.state = self.WAIT_0
          ack = Packet(is_ack = True)
          ack.ack_num = 1
          ack.checksum = make_checksum(ack)
          self._ack_to_send = ack
          self.last_correct_ack = pkt.seq_num
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

def run_one_test(name, error_rate, seed, num_msgs, max_rounds):
    ch = UnreliableChannel(error_rate=error_rate, loss_rate=0.0, seed=seed, verbose=False)
    s, r = Sender2_2(), Receiver2_2()
    ok, rounds = run_test(s, r, ch, num_messages=num_msgs, verbose=False, max_rounds=max_rounds)
    return {
        "name": name, "ok": ok, "rounds": rounds,
        "delivered": r.delivered_messages, "expected": num_msgs,
        "ch_sent": ch.total_sent, "ch_corrupt": ch.total_corrupted,
    }


if __name__ == "__main__":
    results = []

    results.append(run_one_test("无错误", 0.0, 42, 8, 200))
    results.append(run_one_test("出错 15%", 0.15, 456, 8, 400))
    results.append(run_one_test("出错 30% (重复 ACK = NAK)", 0.3, 789, 8, 500))
    results.append(run_one_test("出错 50%", 0.5, 111, 8, 600))
    results.append(run_one_test("出错 60%", 0.6, 999, 6, 800))
    results.append(run_one_test("出错 40% (ACK 大量损坏)", 0.4, 777, 6, 500))

    print("\n" + "=" * 70)
    print("  rdt 2.2 (NAK-free) 测试报告")
    print("=" * 70)
    passed = 0
    for i, r in enumerate(results, 1):
        status = "[OK]" if r["ok"] else "[FAIL]"
        if r["ok"]:
            passed += 1
        print(f"  {i}. {r['name']}")
        print(f"     {status} | {r['rounds']}轮 | "
              f"交付 {len(r['delivered'])}/{r['expected']} | "
              f"信道:发{r['ch_sent']}/错{r['ch_corrupt']}")
    print(f"\n  总计: {passed}/{len(results)} 通过")
    if passed < len(results):
        print("  提示：")
        print("    - last_correct_ack 只在正确收到期望的包并交付后才更新")
        print("    - 收到坏包时发重复 ACK（ack_num = last_correct_ack）")
        print("    - 发送方通过比较 ack_num 和 last_acked 来识别重复 ACK")
