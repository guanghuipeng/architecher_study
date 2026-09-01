"""
RDT 实验 ---- 不可靠信道模拟器

这是整个实验的"舞台"。它模拟一个不可靠的底层信道,
你的 Sender 和 Receiver 将在这个信道上通信。

信道的不可靠行为:
  - 出错 (corrupt): 随机翻转数据中的某些 bit
  - 丢包 (drop):    随机丢弃数据包
  - 延迟 (delay):   随机延迟数据包的到达

用法:
  from rdt_channel import UnreliableChannel, Packet, checksum_ok, make_checksum
"""

import random
import time
from dataclasses import dataclass, field
from typing import Optional, Callable


# ============================================================
#  Packet ---- 所有版本的通用数据包结构
# ============================================================

@dataclass
class Packet:
    """在信道上传输的数据包"""
    seq_num: int = 0        # 序号 (rdt2.1+)
    data: str = ""          # 数据载荷
    checksum: int = 0       # 校验和 (rdt2.0+)
    is_ack: bool = False    # 是 ACK 包吗？
    is_nak: bool = False    # 是 NAK 包吗？(rdt2.0/2.1)
    ack_num: int = 0        # 确认的序号 (用于 ACK)

    def __repr__(self):
        if self.is_ack:
            return f"ACK({self.ack_num})"
        if self.is_nak:
            return f"NAK({self.ack_num})"
        if self.data:
            return f"DATA(seq={self.seq_num}, len={len(self.data)})"
        return "EMPTY"


# ============================================================
#  校验和工具
# ============================================================

def make_checksum(pkt: Packet) -> int:
    """计算校验和 ---- 对数据内容求简单和(模拟反码和)"""
    content = f"{pkt.seq_num}|{pkt.data}|{pkt.ack_num}|{int(pkt.is_ack)}|{int(pkt.is_nak)}"
    return sum(ord(c) for c in content) % 65536


def compute_checksum(pkt: Packet) -> int:
    """重新计算一个包的校验和(用于验证)"""
    return make_checksum(pkt)


def checksum_ok(pkt: Packet) -> bool:
    """验证校验和是否正确"""
    return pkt.checksum == compute_checksum(pkt)


# ============================================================
#  UnreliableChannel ---- 不可靠信道
# ============================================================

class UnreliableChannel:
    """
    模拟不可靠的网络信道。

    配置参数:
      - error_rate:  数据包出错的概率 (0.0 ~ 1.0)
      - loss_rate:   数据包丢失的概率 (0.0 ~ 1.0)
      - delay_range: 延迟范围,单位秒 (min, max),None 表示不延迟
      - seed:        随机种子(固定后每次运行结果一致,方便调试)
      - verbose:     是否打印信道内部事件
    """

    def __init__(self,
                 error_rate: float = 0.0,
                 loss_rate: float = 0.0,
                 delay_range: Optional[tuple] = None,
                 seed: int = 42,
                 verbose: bool = True):
        self.error_rate = error_rate
        self.loss_rate = loss_rate
        self.delay_range = delay_range
        self.verbose = verbose
        random.seed(seed)

        # 统计
        self.total_sent = 0
        self.total_corrupted = 0
        self.total_lost = 0
        self.total_delayed = 0

    def _corrupt(self, pkt: Packet) -> Packet:
        """随机翻转数据中的一个 bit"""
        if not pkt.data:
            return pkt
        # 翻转数据中某个字符的一个 bit
        chars = list(pkt.data)
        idx = random.randint(0, len(chars) - 1)
        ch = ord(chars[idx])
        bit = 1 << random.randint(0, 6)  # 翻转低 7 位中的一位
        ch ^= bit
        chars[idx] = chr(ch if ch > 0 else 1)
        pkt.data = "".join(chars)
        # 不更新 checksum ---- 模拟信道出错后校验和失效
        return pkt

    def transmit(self, pkt: Packet, direction: str = "->") -> Optional[Packet]:
        """
        通过信道传输一个包。
        返回 None 表示包丢失了。
        方向只是用于显示。
        """
        self.total_sent += 1

        # 1. 检查是否丢包
        if random.random() < self.loss_rate:
            self.total_lost += 1
            if self.verbose:
                print(f"   [信道] {direction} [LOST] 包丢失! {pkt}")
            return None

        result = Packet(
            seq_num=pkt.seq_num,
            data=pkt.data,
            checksum=pkt.checksum,
            is_ack=pkt.is_ack,
            is_nak=pkt.is_nak,
            ack_num=pkt.ack_num,
        )

        # 2. 检查是否出错
        if random.random() < self.error_rate:
            result = self._corrupt(result)
            self.total_corrupted += 1
            if self.verbose:
                print(f"   [信道] {direction} [ERR] 包出错! {pkt} -> {result}")

        # 3. 检查是否需要延迟
        if self.delay_range:
            delay = random.uniform(*self.delay_range)
            self.total_delayed += 1
            if self.verbose:
                print(f"   [信道] {direction} [DELAY] 延迟 {delay:.2f}s: {pkt}")
            time.sleep(delay)

        return result

    def stats(self):
        """打印信道统计"""
        print(f"[信道统计] 发送:{self.total_sent} "
              f"出错:{self.total_corrupted} "
              f"丢包:{self.total_lost} "
              f"延迟:{self.total_delayed}")


# ============================================================
#  测试辅助函数
# ============================================================

def run_test(sender, receiver, channel, num_messages: int = 5,
             max_rounds: int = 200, verbose: bool = True):
    """
    运行一次 RDT 协议测试。

    流程:
      1. 从上层注入 num_messages 条消息到 sender
      2. 循环执行:sender 产生包 -> 信道传输 -> receiver 处理 -> 信道返回 ACK
      3. receiver 收到全部消息时结束

    参数:
      - sender:   发送方对象(有 rdt_send(), tick(), delivered 属性)
      - receiver: 接收方对象(有 delivered 属性)
      - channel:  UnreliableChannel 实例
      - num_messages: 要传输的消息数量
      - max_rounds:   最大循环次数(防止死循环)
      - verbose:      是否打印每步细节

    返回:
      (success, rounds) ---- 是否成功、用了多少轮
    """

    # 注入消息
    for i in range(num_messages):
        msg = f"MSG_{i}"
        sender.rdt_send(msg)
        if verbose:
            print(f"\n{'='*50}")
            print(f"[上层] 注入消息: '{msg}'")
            print(f"{'='*50}")

    round_count = 0
    while receiver.delivered_count < num_messages and round_count < max_rounds:
        round_count += 1

        # ====== 发送方 -> 接收方 (数据包) ======
        pkt = sender.outgoing_packet()
        if pkt is not None:
            delivered = channel.transmit(pkt, "S->R")
            if delivered is not None:
                receiver.incoming_packet(delivered)

        # ====== 接收方 -> 发送方 (ACK/NAK) ======
        ack_pkt = receiver.outgoing_ack()
        if ack_pkt is not None:
            delivered = channel.transmit(ack_pkt, "R->S")
            if delivered is not None:
                sender.incoming_ack(delivered)

        # ====== 定时器 tick ======
        sender.tick()

        if verbose and round_count <= 30:
            print(f"  [第{round_count}轮] sender未确认:{sender.pending} "
                  f"receiver已交付:{receiver.delivered_count}/{num_messages}")

    if verbose:
        if receiver.delivered_count == num_messages:
            print(f"\n[OK] 所有 {num_messages} 条消息成功交付! 用了 {round_count} 轮")
        else:
            print(f"\n[FAIL] 超时! 只交付了 {receiver.delivered_count}/{num_messages}")
        channel.stats()

    return receiver.delivered_count == num_messages, round_count
