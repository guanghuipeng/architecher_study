"""
RDT 实验 ---- rdt 1.0:完全可靠信道上的传输

这是最简单的情况:底层信道完美,不丢包、不出错、不乱序。

你的任务:
  阅读代码,理解 Sender 和 Receiver 各需要做什么。
  运行看效果,然后思考:这个协议在不可靠信道上会怎样？

运行:
  python rdt_1_0.py
"""

from typing import Optional
from rdt_channel import Packet, UnreliableChannel, run_test, checksum_ok, make_checksum


# ============================================================
#  rdt 1.0 Sender ---- 最简发送方
# ============================================================

class Sender1_0:
    """
    rdt1.0 发送方

    状态:只有一种状态 ---- 随时可以发下一个包
    逻辑:上层给数据 -> 打包 -> 发出去 -> 完事
    没有:ACK 处理、超时重传、序号管理
    """

    def __init__(self):
        self.pending_queue = []     # 等待发送的消息队列
        self.current_packet = None  # 当前正在发送的包(rdt1.0 里发完即清)

    # ---------- 上层接口:应用层调用 ----------
    def rdt_send(self, data: str):
        """上层有数据要发送"""
        self.pending_queue.append(data)

    # ---------- 下层接口:从信道收 ACK ----------
    def incoming_ack(self, pkt: Packet):
        """收到来自接收方的包(rdt1.0 里不会有,信道只传数据不传 ACK)"""
        pass  # rdt1.0 不需要处理任何反馈

    # ---------- 定时器 ----------
    def tick(self):
        """定时器滴答(rdt1.0 不需要定时器)"""
        pass

    # ---------- 产生要发送的包 ----------
    def outgoing_packet(self) -> Optional[Packet]:
        """
        框架会循环调用这个方法,取走要发的包。

        rdt1.0 的逻辑:
          有消息在排队 -> 取一条 -> 打包 -> 返回 -> 完事
          不需要等 ACK,下一个循环就能发下一条
        """
        if self.current_packet is not None:
            # 刚发完一个包,清掉它
            pkt = self.current_packet
            self.current_packet = None
            return pkt

        if self.pending_queue:
            data = self.pending_queue.pop(0)
            pkt = Packet(data=data)
            print(f"  [Sender] 打包并发送: '{data}'")
            self.current_packet = pkt
            return None  # 这个循环先返回 None,下个循环再发
        return None

    @property
    def pending(self) -> int:
        """未确认的包数量"""
        return len(self.pending_queue)

    @property
    def delivered(self):
        """兼容接口"""
        return self


# ============================================================
#  rdt 1.0 Receiver ---- 最简接收方
# ============================================================

class Receiver1_0:
    """
    rdt1.0 接收方

    状态:只有一种状态 ---- 随时接收
    逻辑:收到包 -> 拆包 -> 交上层 -> 完事
    没有:校验、ACK 发送、序号检查
    """

    def __init__(self):
        self.delivered_messages = []  # 已交付上层的消息

    # ---------- 下层接口:从信道收到包 ----------
    def incoming_packet(self, pkt: Packet):
        """收到一个数据包"""
        print(f"  [Receiver] 收到包, 数据: '{pkt.data}'")
        # rdt1.0: 无条件信任！直接交付上层
        self.deliver(pkt.data)

    def deliver(self, data: str):
        """把数据交给上层"""
        self.delivered_messages.append(data)
        print(f"  [Receiver] [OK] 交付上层: '{data}'")

    # ---------- 产生 ACK ----------
    def outgoing_ack(self) -> Optional[Packet]:
        """rdt1.0 不需要发 ACK"""
        return None

    # ---------- 统计 ----------
    @property
    def delivered_count(self) -> int:
        return len(self.delivered_messages)


# ============================================================
#  测试
# ============================================================

def test_rdt1_0():
    """rdt1.0 在完全可靠信道上的测试"""
    print("=" * 60)
    print("  rdt 1.0 ---- 完全可靠信道")
    print("  error_rate=0, loss_rate=0")
    print("=" * 60)

    # 完美信道
    channel = UnreliableChannel(
        error_rate=0.0,
        loss_rate=0.0,
        seed=42,
        verbose=True,
    )

    sender = Sender1_0()
    receiver = Receiver1_0()

    success, rounds = run_test(sender, receiver, channel, num_messages=3, verbose=True)

    print(f"\n[Result] 交付的消息: {receiver.delivered_messages}")

    return success


def test_rdt1_0_with_errors():
    """rdt1.0 在不可靠信道上的测试 ---- 演示为什么需要 rdt2.0"""
    print("\n" + "=" * 60)
    print("  rdt 1.0 在不可靠信道上(模拟)")
    print("  error_rate=0.3, loss_rate=0.2")
    print("  预期:部分消息损坏或丢失！")
    print("=" * 60)

    channel = UnreliableChannel(
        error_rate=0.3,
        loss_rate=0.2,
        seed=123,
        verbose=True,
    )

    sender = Sender1_0()
    receiver = Receiver1_0()

    # 手动模拟,显示接收方收到损坏数据
    print("\n  [注意] 损坏的包也被'交付'了!")
    print("  这就是为什么我们需要 rdt2.0 -- 校验和 + ACK/NAK\n")

    for i in range(3):
        msg = f"MSG_{i}"
        sender.rdt_send(msg)

    for round_num in range(50):
        pkt = sender.outgoing_packet()
        if pkt is not None:
            delivered = channel.transmit(pkt, "S->R")
            if delivered is not None:
                # 检查校验和但 rdt1.0 不检查！
                if delivered.checksum != 0:
                    ok = checksum_ok(delivered) if delivered.checksum else "无校验和"
                receiver.incoming_packet(delivered)

        if receiver.delivered_count >= 3:
            break

    print(f"\n[Result] 交付的消息: {receiver.delivered_messages}")
    print("[警告] 有些消息可能已损坏但依然被'交付'了!")


if __name__ == "__main__":
    test_rdt1_0()
    test_rdt1_0_with_errors()
