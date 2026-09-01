"""
RDT 实验 ---- rdt 2.1：ACK/NAK 也会出错！加序号解决

rdt2.0 的致命漏洞：
  发送方收到一个损坏的反馈包 —— 分不清它是 ACK 还是 NAK！
  - 如果原本是 NAK（该重传）→ 没重传 → 数据丢失
  - 如果原本是 ACK（不该重传）→ 重传了 → 接收方收到重复包

rdt2.1 的解决方案：给数据包加序号（0 和 1 交替）
  接收方看到序号和上一个相同 → 知道是重传的 → 丢掉但重发 ACK
  接收方看到序号和上一个不同 → 知道是新包 → 交付

为什么 Stop-and-Wait 只需要 0/1 两个序号？
  同一时刻只有一个包在飞。接收方只需要区分"和上一个相同吗？"

发送方：4 个状态
  WAIT_CALL_0 → 空闲，下一个包用 seq=0
  WAIT_ACK_0  → 发了 seq=0，等 ACK
  WAIT_CALL_1 → 空闲，下一个包用 seq=1
  WAIT_ACK_1  → 发了 seq=1，等 ACK

接收方：2 个状态
  WAIT_0 → 期望收到 seq=0
  WAIT_1 → 期望收到 seq=1

运行：
  python rdt_2_1.py
"""

from typing import Optional
from rdt_channel import Packet, UnreliableChannel, checksum_ok, make_checksum, run_test


# ============================================================
#  rdt 2.1 Sender ---- 请你完成 TODO
# ============================================================

class Sender2_1:
    """
    rdt2.1 发送方 —— 4 个状态，序号 0/1 交替
    """

    WAIT_CALL_0 = 0   # 空闲，下一个包用 seq=0
    WAIT_ACK_0 = 1    # 发了 seq=0，等 ACK
    WAIT_CALL_1 = 2   # 空闲，下一个包用 seq=1
    WAIT_ACK_1 = 3    # 发了 seq=1，等 ACK

    def __init__(self):
        self.state = self.WAIT_CALL_0
        self.pending_queue = []       # 排队等待发送的消息
        self.current_pkt = None       # 当前等待 ACK 的包
        self._packet_unsent = False   # True = current_pkt 还没被 outgoing_packet 取走

    # ========================================
    #  TODO ①：上层有数据要发送 + 打包
    # ========================================
    def rdt_send(self, data: str):
        """
        上层给你原始数据（字符串）。

        你需要在这里完成"数据→包"的组装：
          1. 确定序号：
             WAIT_CALL_0 → seq=0, 状态切到 WAIT_ACK_0
             WAIT_CALL_1 → seq=1, 状态切到 WAIT_ACK_1
          2. Packet(seq_num=seq, data=data)  创建包（注意填 seq_num！）
          3. make_checksum(pkt)              计算校验和
          4. self.current_pkt = pkt          保存，方便后续重传
          5. self._packet_unsent = True      标记"还没被取走"

        如果当前状态是 WAIT_ACK_0 或 WAIT_ACK_1（忙）：
          → 把 data 放入 pending_queue 排队，不做其他事
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
    #  TODO ②：收到 ACK/NAK
    # ========================================
    def incoming_ack(self, pkt: Packet):
        """
        收到反馈包。

        rdt2.1 新增的难题：ACK/NAK 自己也可能在信道里损坏。

        你需要：
          1. checksum_ok(pkt) 检查校验和
             坏了 → "不知道是 ACK 还是 NAK" → 怎么办？
             rdt2.1 的处理：当作需要重传，把 _packet_unsent 设为 True
             （宁可重复发，也不要丢数据）

          2. 校验和正确，pkt.is_nak → 需要重传！
             重新计算 current_pkt 的校验和
             _packet_unsent = True

          3. 校验和正确，pkt.is_ack → 检查 ACK 的序号是否正确：
             期望什么 ACK 号？
               WAIT_ACK_0 → 期望 ACK(0)，表示"确认收到了包 0"
               WAIT_ACK_1 → 期望 ACK(1)，表示"确认收到了包 1"
             正确 → 切到对应的 WAIT_CALL 状态
                    如果队列有排队的消息 → 组装发送新包
             不正确 → 忽略（这是迟到的重复 ACK）
        """
        # ----- 你的代码 -----
        if not checksum_ok(pkt):
          self._packet_unsent = True
        elif pkt.is_nak:
          self._packet_unsent = True
        elif pkt.is_ack:
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
    #  TODO ③：产生要发送的包
    # ========================================
    def outgoing_packet(self) -> Optional[Packet]:
        """
        框架每轮调用取包。

        逻辑：
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
#  rdt 2.1 Receiver ---- 请你完成 TODO
# ============================================================

class Receiver2_1:
    """
    rdt2.1 接收方 —— 2 个状态，知道期望哪个序号

    WAIT_0 → 期望 seq=0
    WAIT_1 → 期望 seq=1

    核心规则：收到重复包（序号不是期望的）→ 数据不交付，但重发 ACK
    因为上次的 ACK 可能丢了，发送方在等。
    """

    WAIT_0 = 0
    WAIT_1 = 1

    def __init__(self):
        self.state = self.WAIT_0
        self.delivered_messages = []
        self._ack_to_send = None   # 待发的反馈包

    # ========================================
    #  TODO ④：收到数据包
    # ========================================
    def incoming_packet(self, pkt: Packet):
        """
        收到数据包。需要同时检查校验和 + 序号。

        三种情况：

        A. checksum_ok(pkt) == False（损坏）
           → 发 NAK
             构造：Packet(is_nak=True)
             别忘了 make_checksum(nak)！

        B. 校验和正确 + seq 是我期望的
           例如：state==WAIT_0 且 pkt.seq_num==0
           → 交付数据 deliver(pkt.data)
           → 切状态（WAIT_0→WAIT_1 或 WAIT_1→WAIT_0）
           → 发 ACK，ack_num = 新期望的序号
             构造：Packet(is_ack=True, ack_num=新序号)

        C. 校验和正确 + seq 不是期望的（重复包）
           → 不交付数据（已经交付过了）
           → 重发 ACK，ack_num = 当前期望的序号
             构造：Packet(is_ack=True, ack_num=期望序号)
        """
        # ----- 你的代码 -----
        if not checksum_ok(pkt):
          nak = Packet(is_nak = True)
          nak.checksum = make_checksum(nak)
          self._ack_to_send = nak
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

def run_one_test(name, error_rate, seed, num_msgs, max_rounds):
    ch = UnreliableChannel(error_rate=error_rate, loss_rate=0.0, seed=seed, verbose=False)
    s, r = Sender2_1(), Receiver2_1()
    ok, rounds = run_test(s, r, ch, num_messages=num_msgs, verbose=False, max_rounds=max_rounds)
    return {
        "name": name, "ok": ok, "rounds": rounds,
        "delivered": r.delivered_messages, "expected": num_msgs,
        "ch_sent": ch.total_sent, "ch_corrupt": ch.total_corrupted,
    }


if __name__ == "__main__":
    results = []

    results.append(run_one_test("无错误", 0.0, 42, 8, 200))
    results.append(run_one_test("出错 10%", 0.1, 456, 8, 300))
    results.append(run_one_test("出错 30% (验证坏ACK/NAK)", 0.3, 789, 8, 400))
    results.append(run_one_test("出错 50%", 0.5, 111, 8, 600))
    results.append(run_one_test("出错 60%", 0.6, 222, 5, 600))

    print("\n" + "=" * 70)
    print("  rdt 2.1 测试报告")
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
        print("    - 坏 ACK/NAK 的处理：当作需要重传")
        print("    - 收到 ACK 时检查 ack_num 是否匹配当前期望的")
        print("    - 接收方收到重复包时：不交付数据但要重发 ACK")
