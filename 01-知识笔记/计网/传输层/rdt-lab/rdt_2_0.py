"""
RDT 实验 ---- rdt 2.0：有 bit 错误的信道

信道可能翻转 bit（出错），但不会丢包。

上一版 rdt1.0 的问题：
  信道出错 → 接收方收到坏数据 → 直接交付上层 → 灾难！

rdt2.0 新加两个机制：
  ① 校验和 (checksum) — 检测 bit 错误
  ② ACK / NAK    — 接收方告诉发送方"收到好的还是坏的"

思考题（写代码前先想清楚）：
  1. 发送方发完包后该干什么？还能继续发下一个吗？
  2. 接收方收到坏包怎么办？收到好包怎么办？
  3. 发送方收到 ACK 做什么？收到 NAK 做什么？
  4. 如果 ACK 或 NAK 自己在信道里出错了，怎么办？
     （这是 rdt2.0 的致命漏洞，rdt2.1 会解决）

运行：
  python rdt_2_0.py
"""

from typing import Optional
from rdt_channel import Packet, UnreliableChannel, checksum_ok, make_checksum, run_test


# ============================================================
#  rdt 2.0 Sender ---- 请你完成 TODO
# ============================================================

class Sender2_0:
    """
    rdt2.0 发送方

    状态：两种
      WAITING_FOR_CALL — 空闲，等上层给数据
      WAITING_FOR_ACK  — 发完包了，等接收方回复

    关键：发完包后必须停下来等！不能像 rdt1.0 那样连续发。
    """

    WAITING_FOR_CALL = 0
    WAITING_FOR_ACK = 1

    def __init__(self):
        self.state = self.WAITING_FOR_CALL
        self.pending_queue = []       # 排队等待发送的消息
        self.current_pkt = None       # 当前等待 ACK 的包
        self._packet_unsent = False   # True = current_pkt 还没被 outgoing_packet 取走

    # ========================================
    #  TODO ①：上层有数据要发送 + 打包
    # ========================================
    def rdt_send(self, data: str):
        """
        上层调用，给你一条要发送的原始数据（就是个字符串）。

        你需要在这里完成"数据→包"的组装：
          1. pkt = Packet(data=data)              创建包
          2. pkt.checksum = make_checksum(pkt)    计算校验和并填入包
          3. self.current_pkt = pkt               保存（方便后续重传）
          4. self._packet_unsent = True           标记"还没被取走"

        然后根据当前状态：
          - WAITING_FOR_CALL（空闲）→ 直接组装 + 切到 WAITING_FOR_ACK
          - WAITING_FOR_ACK（忙）    → 放入 pending_queue 排队
        """
        # ----- 你的代码 -----
      
        if self.state == self.WAITING_FOR_CALL:
          pkt = Packet(data=data)
          pkt.checksum = make_checksum(pkt)
          self.current_pkt = pkt
          self._packet_unsent = True
          self.state = self.WAITING_FOR_ACK
        elif self.state == self.WAITING_FOR_ACK:
          self.pending_queue.append(data)
        pass
        # --------------------

    # ========================================
    #  TODO ②：收到接收方的反馈
    # ========================================
    def incoming_ack(self, pkt: Packet):
        """
        收到来自接收方的包（可能是 ACK，也可能是 NAK）。

        你需要：
          1. 先检查校验和：checksum_ok(pkt)
             坏了 → 忽略，什么也不做

          2. 校验和正确，看是 ACK 还是 NAK：
             - ACK → 发送成功！
               切回 WAITING_FOR_CALL
               如果队列有排队的消息 → 取出来组装发送（和 TODO① 一样）
             - NAK → 重传！
               把 current_pkt 的校验和重新算一遍
               _packet_unsent = True  （允许 outgoing_packet 再次取走）
        """
        # ----- 你的代码 -----
        if not checksum_ok(pkt):
          return
        if pkt.is_ack:
          self.state = self.WAITING_FOR_CALL
          if self.pending_queue:
            data = self.pending_queue.pop(0)
            self.rdt_send(data)
        elif pkt.is_nak:
          self._packet_unsent = True
        
        
        # --------------------

    # ========================================
    #  TODO ③：产生要发送的包（框架每轮都调用）
    # ========================================
    def outgoing_packet(self) -> Optional[Packet]:
        """
        框架循环调用这个方法取包。

        逻辑非常简单：
          if current_pkt 存在 且 _packet_unsent == True:
              把 _packet_unsent 设为 False
              返回 current_pkt
          否则:
              返回 None

        为什么这样设计？
          框架每轮都调用这个方法。如果直接返回 current_pkt，
          那同一个包会被反复发送无数次。用 _packet_unsent
          保证一个包只被取走一次，直到收到 NAK 重新标记为 unsent。
        """
        # ----- 你的代码 -----
        if self.current_pkt and self._packet_unsent:
          self._packet_unsent = False
          return self.current_pkt
        else:
          return None
        pass
        # --------------------

    # ---------- 定时器（rdt2.0 不用） ----------
    def tick(self):
        pass

    @property
    def pending(self) -> int:
        return len(self.pending_queue) + (1 if self.state == self.WAITING_FOR_ACK else 0)


# ============================================================
#  rdt 2.0 Receiver ---- 请你完成 TODO
# ============================================================

class Receiver2_0:
    """
    rdt2.0 接收方

    状态：一种 —— 始终等待接收

    逻辑：
      - 收到包 → 检查校验和
      - 正确 → 交付上层 + 发 ACK
      - 出错 → 发 NAK（不要交付错误数据！）
    """

    def __init__(self):
        self.delivered_messages = []
        self._ack_to_send = None   # 待发的 ACK 或 NAK

    # ========================================
    #  TODO ④：收到数据包
    # ========================================
    def incoming_packet(self, pkt: Packet):
        """
        收到一个数据包。

        你需要：
          1. 检查校验和（用 checksum_ok(pkt)）
          2. 如果正确 → 调用 self.deliver(data) 交付上层
                       然后构造一个 ACK 包，放入 self._ack_to_send
          3. 如果出错 → 构造一个 NAK 包，放入 self._ack_to_send
                       不要交付错误数据！

        构造 ACK：Packet(is_ack=True)
        构造 NAK：Packet(is_nak=True)
        别忘了给 ACK/NAK 也计算校验和！(make_checksum)
        """
        # ----- 你的代码 -----
        if checksum_ok(pkt):
          self.deliver(pkt.data)
          ack = Packet(is_ack=True)
          ack.checksum = make_checksum(ack)
          self._ack_to_send = ack
        else:
          nak = Packet(is_nak = True)
          nak.checksum = make_checksum(nak)
          self._ack_to_send = nak
        pass
        # --------------------

    def deliver(self, data: str):
        self.delivered_messages.append(data)
        print(f"  [Receiver] [Deliver] 交付上层: '{data}'")

    def outgoing_ack(self) -> Optional[Packet]:
        """框架调用：返回要发的 ACK/NAK"""
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
    """运行一次测试，返回结果字典"""
    ch = UnreliableChannel(error_rate=error_rate, loss_rate=0.0, seed=seed, verbose=False)
    s, r = Sender2_0(), Receiver2_0()
    ok, rounds = run_test(s, r, ch, num_messages=num_msgs, verbose=False, max_rounds=max_rounds)
    return {
        "name": name,
        "ok": ok,
        "rounds": rounds,
        "delivered": r.delivered_messages,
        "expected": num_msgs,
        "ch_sent": ch.total_sent,
        "ch_corrupt": ch.total_corrupted,
    }


if __name__ == "__main__":
    results = []

    # 测试 1：无错误 — 确认基本功能正常
    results.append(run_one_test("无错误", 0.0, 42, 5, 200))

    # 测试 2：10% 出错 — 轻量验证
    results.append(run_one_test("出错 10%", 0.1, 456, 5, 300))

    # 测试 3：30% 出错 — 验证 ACK/NAK 重传
    results.append(run_one_test("出错 30%", 0.3, 789, 5, 400))

    # 测试 4：50% 出错 — 压力测试
    results.append(run_one_test("出错 50%", 0.5, 111, 5, 500))

    # ---- 汇总报告 ----
    print("\n" + "=" * 70)
    print("  rdt 2.0 测试报告")
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
        print("  提示：检查 ACK/NAK 处理逻辑和 outgoing_packet 的重传机制")
