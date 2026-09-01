/*
 * rdt 1.0 —— 完全可靠信道
 *
 * 这是最简单的情况：信道完美，不丢包、不出错、不乱序。
 * 阅读代码，理解 Sender 和 Receiver 各需要做什么。
 *
 * 编译: g++ -std=c++17 -o rdt_1_0 rdt_1_0.cpp
 * 运行: ./rdt_1_0
 */

#include "rdt_channel.hpp"
#include <queue>
#include <optional>

// ============================================================
//  Sender 1.0
// ============================================================
struct Sender1_0 {
    std::queue<std::string> pending_queue;
    std::optional<Packet> current_pkt;

    void rdt_send(const std::string& data) {
        pending_queue.push(data);
    }

    void incoming_ack(const Packet&) {
        // rdt1.0: 不需要处理反馈
    }

    void tick() {
        // rdt1.0: 不需要定时器
    }

    std::optional<Packet> outgoing_packet() {
        if (current_pkt) {
            auto pkt = *current_pkt;
            current_pkt.reset();
            return pkt;
        }
        if (!pending_queue.empty()) {
            std::string data = pending_queue.front();
            pending_queue.pop();
            Packet pkt;
            pkt.data = data;
            std::cout << "  [Sender] 发送: '" << data << "'" << std::endl;
            current_pkt = pkt;
            return std::nullopt;  // 下轮再发
        }
        return std::nullopt;
    }

    int retransmit_count = 0;
    int pending() const { return pending_queue.size() + (current_pkt ? 1 : 0); }
};

// ============================================================
//  Receiver 1.0
// ============================================================
struct Receiver1_0 {
    std::vector<std::string> delivered_messages;
    std::optional<Packet> ack_pkt;

    void incoming_packet(const Packet& pkt) {
        std::cout << "  [Receiver] 收到: '" << pkt.data << "'" << std::endl;
        deliver(pkt.data);
    }

    void deliver(const std::string& data) {
        delivered_messages.push_back(data);
        std::cout << "  [Receiver] [Deliver] 交付上层: '" << data << "'" << std::endl;
    }

    std::optional<Packet> outgoing_ack() {
        return std::nullopt;  // rdt1.0 不发 ACK
    }

    int delivered_count() const { return delivered_messages.size(); }
};

// ============================================================
int main() {
    std::cout << std::string(60, '=') << std::endl;
    std::cout << "  rdt 1.0 —— 完全可靠信道" << std::endl;
    std::cout << std::string(60, '=') << std::endl;

    UnreliableChannel channel(0.0, 0.0, 42);
    Sender1_0 sender;
    Receiver1_0 receiver;

    auto result = run_test(sender, receiver, channel, 5);
    std::cout << "\n[Result] success=" << (result.success ? "true" : "false")
              << " rounds=" << result.rounds << std::endl;
    std::cout << "交付的消息: ";
    for (auto& m : result.delivered) std::cout << m << " ";
    std::cout << std::endl;

    return 0;
}
