"""
RDT 实验 ---- Go-Back-N (GBN)

在 rdt3.0 之后,我们不再 stop-and-wait,而是让多个包同时在飞(流水线)。

GBN 的核心规则:
  - 发送方维护一个大小为 N 的滑动窗口
  - 接收方只接受按序到达的包,乱序的直接丢弃
  - 累积确认:ACK(n) 表示 "n 及之前的所有包都收到了"
  - 只有一个定时器,为窗口中最老的那个未确认包计时
  - 超时后:从最老的未确认包开始,全部重传

你的任务:
  完成 Sender 和 Receiver 中标记 TODO 的方法。

运行:
  python rdt_gbn.py

实验建议:
  1. 先用 window_size=4, 无丢包无出错, 确认流水线跑得通
  2. 加 10% 丢包, 观察 "回退 N 步" 的行为
  3. 对比 rdt3.0(Stop-and-Wait)的轮数,感受流水线加速
"""

from typing import Optional, List
from rdt_channel import Packet, UnreliableChannel, checksum_ok, make_checksum


# ============================================================
#  流水线测试框架 (和 stop-and-wait 不同,每轮可以发多个包)
# ============================================================

def run_test_pipelined(sender, receiver, channel, num_messages: int = 10,
                       max_rounds: int = 500, verbose: bool = True):
    """
    流水线版测试框架。
    和 run_test 的区别:每轮会循环调用 sender.outgoing_packet()
    直到它返回 None,允许一次发多个包。
    """
    for i in range(num_messages):
        msg = f"MSG_{i}"
        sender.rdt_send(msg)

    round_count = 0
    while receiver.delivered_count < num_messages and round_count < max_rounds:
        round_count += 1

        # ====== 发送方 -> 接收方 (可能发多个包) ======
        while True:
            pkt = sender.outgoing_packet()
            if pkt is None:
                break
            delivered = channel.transmit(pkt, "S->R")
            if delivered is not None:
                receiver.incoming_packet(delivered)

        # ====== 接收方 -> 发送方 (ACK) ======
        ack_pkt = receiver.outgoing_ack()
        if ack_pkt is not None:
            delivered = channel.transmit(ack_pkt, "R->S")
            if delivered is not None:
                sender.incoming_ack(delivered)

        # ====== 定时器 tick ======
        sender.tick()

        if verbose and round_count <= 50:
            print(f"  [第{round_count}轮] sender窗口:[{sender.base},{sender.nextseq}) "
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
#  GBN Sender ---- 请你完成 TODO
# ============================================================

class SenderGBN:
    """
    GBN 发送方

    滑动窗口:
      [base, nextseq) 范围内的包 "已发送但未确认"
      窗口大小 = N = window_size
      约束: nextseq < base + N

    定时器: 只为 base 那个包计时(最老未确认的包)

    收到 ACK(n):
      累积确认 —— base 跳到 n+1
      如果 base == nextseq: 窗口空了,停止定时器
      否则: 重启定时器(为新的 base 计时)

    超时:
      从 base 到 nextseq-1 全部重传!
    """

    SEQ_SPACE = 256  # 序号空间 (远远大于窗口,避免 SR 那种序号冲突)

    def __init__(self, window_size: int = 4, timeout: int = 20):
        self.window_size = window_size
        self.timeout = timeout

        # 滑动窗口
        self.base = 0       # 窗口左边界(最老未确认的序号)
        self.nextseq = 0    # 下一个可用的序号(窗口右边界)

        # 缓冲区
        self.pending_queue: List[str] = []           # 上层注入但还没分配序号的消息
        self.in_flight: dict = {}                    # 已发送但未确认的包 {seq: Packet}

        # 定时器
        self.timer_ticks = 0
        self.timer_running = False

        # 统计
        self.retransmit_count = 0

    # ========================================
    #  TODO ①: 上层注入数据
    # ========================================
    def rdt_send(self, data: str):
        """
        上层有数据要发送。

        你需要:
          把 data 放入 pending_queue
          然后调用 self._try_send() 尝试发送
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    # ========================================
    #  TODO ②: 尝试发送 (流水线的关键!)
    # ========================================
    def _try_send(self):
        """
        只要窗口没满且有数据在队列,就不断打包发送。

        窗口是否已满？ nextseq >= base + window_size

        你需要:
          1. 从 pending_queue 取数据
          2. 用 nextseq 作为序号创建 Packet
          3. 计算校验和
          4. 放入 in_flight 字典
          5. nextseq++
          6. 如果是窗口中的第一个包(base == nextseq 之前),启动定时器
          7. 循环直到窗口满或队列空
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    # ========================================
    #  TODO ③: 收到 ACK
    # ========================================
    def incoming_ack(self, pkt: Packet):
        """
        收到来自接收方的包。

        GBN 是累积确认: ACK(n) 表示 n 之前(含 n)的包全收到了。

        你需要:
          1. 检查校验和,坏了就忽略
          2. 取出 ack_num
          3. 把 base 更新为 ack_num + 1
             (但如果 ack_num < base,说明是迟到的重复 ACK,忽略)
          4. 清理 in_flight 中已经确认的包 (seq < 新 base 的)
          5. 如果 base == nextseq: 窗口空了,停止定时器
             否则: 重启定时器(为新的 base 计时)
          6. 调用 _try_send() —— 窗口有空位了,发新包!
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    # ========================================
    #  TODO ④: 定时器
    # ========================================
    def tick(self):
        """
        每轮调用一次。

        你需要:
          如果定时器正在运行:
            timer_ticks++
            如果 >= timeout: 超时！
              - 重传窗口中的所有包(base 到 nextseq-1)
              - retransmit_count += (nextseq - base)
              - 重置计时器,重启定时器(为 base 计时)
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    # ========================================
    #  TODO ⑤: 产生要发送的包 (框架接口)
    # ========================================
    def outgoing_packet(self) -> Optional[Packet]:
        """
        框架循环调用,每次返回一个待发送的包。
        返回 None 表示当前没有要发的包。

        你需要:
          in_flight 中可能有多个未发送的包
          如何标记一个包"已经通过 outgoing_packet 发出去了"?

          提示:
            在 in_flight 字典中追踪 {seq: (pkt, sent)}
            或者用两个字典: in_flight 和 unsent
            或者从 base 开始顺序返回未发送的包

        简化方案:
          用一个 _sent_up_to 指针,记录已经通过本方法返回的包的最大序号
          每次调用时,返回下一个未发送的包
        """
        # ----- 你的代码 -----
        pass
        # --------------------

    @property
    def pending(self) -> int:
        return len(self.pending_queue) + len(self.in_flight)


# ============================================================
#  GBN Receiver ---- 请你完成 TODO
# ============================================================

class ReceiverGBN:
    """
    GBN 接收方

    比发送方简单得多 —— 只记一个 expectedseq。
    收到正确的、期望序号的包 → 交付 + 发 ACK
    收到任何其他包 → 丢弃,重发上一次的 ACK
    """

    def __init__(self):
        self.expectedseq = 0
        self.delivered_messages: List[str] = []
        self._ack_to_send: Optional[Packet] = None
        self.last_ack_sent = -1  # 上一次发的 ACK 号

    # ========================================
    #  TODO ⑥: 收包逻辑
    # ========================================
    def incoming_packet(self, pkt: Packet):
        """
        收到一个数据包。

        你需要:
          1. 检查校验和,坏了 → 忽略(什么都不做)
          2. 序号 == expectedseq？
             是 → 交付上层, expectedseq++, 发 ACK(expectedseq)
             否 → 丢弃, 重发上一次的 ACK (last_ack_sent)
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
    """运行一次 GBN 测试"""
    ch = UnreliableChannel(error_rate=error_rate, loss_rate=loss_rate, seed=seed, verbose=False)
    s, r = SenderGBN(window_size=window_size, timeout=timeout), ReceiverGBN()
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

    # 测试 1：无错误无丢包 —— 验证流水线基本功能
    results.append(run_one_test("无错误无丢包 (窗口=4)", 4, 0.0, 0.0, 42, 10, 20, 200))

    # 测试 2：轻丢包 —— 验证累积 ACK 和定时器
    results.append(run_one_test("丢包 3% (窗口=4)", 4, 0.0, 0.03, 42, 10, 15, 300))

    # 测试 3：中丢包 —— 观察 "回退 N 步" 行为
    results.append(run_one_test("丢包 10% (窗口=4)", 4, 0.0, 0.10, 123, 10, 15, 400))

    # 测试 4：大窗口 —— 流水线加速效果
    results.append(run_one_test("丢包 10% (窗口=8,大窗口)", 8, 0.0, 0.10, 42, 15, 15, 500))

    # 测试 5：丢包 + 出错 —— 综合压力
    results.append(run_one_test("丢包 10% + 出错 5% (窗口=4)", 4, 0.05, 0.10, 99, 10, 15, 500))

    # 测试 6：高丢包 —— 压力测试
    results.append(run_one_test("丢包 20% (窗口=4)", 4, 0.0, 0.20, 777, 8, 12, 500))

    # ---- 汇总报告 ----
    print("\n" + "=" * 70)
    print("  GBN (Go-Back-N) 测试报告")
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
        print("    - GBN 超时后要重传整个窗口 [base, nextseq)")
        print("    - 定时器只为 base 那个包计时")
        print("    - 接收方收到乱序包直接丢弃，重发 last_ack_sent")
