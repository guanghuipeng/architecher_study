#pragma once
/*
 * RDT 实验 —— C++ 版信道模拟器
 *
 * 和 Python 版功能完全一样：
 *   - Packet: 数据包结构
 *   - make_checksum / checksum_ok: 校验和
 *   - UnreliableChannel: 不可靠信道（出错/丢包/延迟）
 *   - run_test<T>: 测试框架模板
 */

#include <string>
#include <optional>
#include <random>
#include <iostream>
#include <sstream>
#include <vector>
#include <functional>

// ============================================================
//  Packet —— 通用数据包
// ============================================================
struct Packet {
    int seq_num = 0;
    std::string data;
    int checksum = 0;
    bool is_ack = false;
    bool is_nak = false;
    int ack_num = 0;

    std::string repr() const {
        if (is_ack) return "ACK(" + std::to_string(ack_num) + ")";
        if (is_nak) return "NAK(" + std::to_string(ack_num) + ")";
        if (!data.empty()) return "DATA(seq=" + std::to_string(seq_num) + ", len=" + std::to_string(data.size()) + ")";
        return "EMPTY";
    }
};

// ============================================================
//  校验和
// ============================================================
inline int make_checksum(const Packet& pkt) {
    std::string content = std::to_string(pkt.seq_num) + "|" + pkt.data + "|"
        + std::to_string(pkt.ack_num) + "|" + std::to_string(pkt.is_ack)
        + "|" + std::to_string(pkt.is_nak);
    int sum = 0;
    for (char c : content) sum += static_cast<unsigned char>(c);
    return sum % 65536;
}

inline bool checksum_ok(const Packet& pkt) {
    return pkt.checksum == make_checksum(pkt);
}

// ============================================================
//  UnreliableChannel —— 不可靠信道
// ============================================================
class UnreliableChannel {
public:
    double error_rate;
    double loss_rate;
    int total_sent = 0;
    int total_corrupted = 0;
    int total_lost = 0;

    explicit UnreliableChannel(double err = 0.0, double loss = 0.0, int seed = 42)
        : error_rate(err), loss_rate(loss), rng_(seed),
          err_dist_(0.0, 1.0), loss_dist_(0.0, 1.0) {}

    std::optional<Packet> transmit(const Packet& pkt, const std::string& direction = "->") {
        total_sent++;

        // 丢包
        if (loss_dist_(rng_) < loss_rate) {
            total_lost++;
            return std::nullopt;
        }

        Packet result = pkt;

        // 出错
        if (err_dist_(rng_) < error_rate) {
            if (!result.data.empty()) {
                std::uniform_int_distribution<int> char_dist(0, result.data.size() - 1);
                std::uniform_int_distribution<int> bit_dist(0, 6);
                int idx = char_dist(rng_);
                unsigned char& ch = reinterpret_cast<unsigned char&>(result.data[idx]);
                ch ^= (1 << bit_dist(rng_));
                if (ch == 0) ch = 1;
            }
            total_corrupted++;
        }

        return result;
    }

    void stats() const {
        std::cout << "[信道统计] 发送:" << total_sent
                  << " 出错:" << total_corrupted
                  << " 丢包:" << total_lost << std::endl;
    }

private:
    std::mt19937 rng_;
    std::uniform_real_distribution<double> err_dist_;
    std::uniform_real_distribution<double> loss_dist_;
};

// ============================================================
//  测试框架 (模板)
// ============================================================
struct TestResult {
    bool success;
    int rounds;
    int retrans;
    int ch_sent;
    int ch_lost;
    int ch_corrupt;
    std::vector<std::string> delivered;
};

template <typename Sender, typename Receiver>
TestResult run_test(Sender& sender, Receiver& receiver, UnreliableChannel& channel,
                    int num_messages, int max_rounds = 200) {
    // 注入消息
    for (int i = 0; i < num_messages; i++) {
        sender.rdt_send("MSG_" + std::to_string(i));
    }

    int round_count = 0;
    while (receiver.delivered_count() < num_messages && round_count < max_rounds) {
        round_count++;

        // Sender → Receiver (可能多个包)
        while (true) {
            auto opt_pkt = sender.outgoing_packet();
            if (!opt_pkt) break;
            auto delivered = channel.transmit(*opt_pkt, "S->R");
            if (delivered) {
                receiver.incoming_packet(*delivered);
            }
        }

        // Receiver → Sender (ACK/NAK)
        auto opt_ack = receiver.outgoing_ack();
        if (opt_ack) {
            auto delivered = channel.transmit(*opt_ack, "R->S");
            if (delivered) {
                sender.incoming_ack(*delivered);
            }
        }

        sender.tick();
    }

    TestResult result;
    result.success = (receiver.delivered_count() == num_messages);
    result.rounds = round_count;
    result.retrans = sender.retransmit_count;
    result.ch_sent = channel.total_sent;
    result.ch_lost = channel.total_lost;
    result.ch_corrupt = channel.total_corrupted;
    result.delivered = receiver.delivered_messages;
    return result;
}

// 打印测试报告
inline void print_report(const std::string& title,
                         const std::vector<std::pair<std::string, TestResult>>& results) {
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "  " << title << " 测试报告" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    int passed = 0;
    for (size_t i = 0; i < results.size(); i++) {
        const auto& [name, r] = results[i];
        const char* status = r.success ? "[OK]" : "[FAIL]";
        if (r.success) passed++;
        std::cout << "  " << (i + 1) << ". " << name << std::endl;
        std::cout << "     " << status << " | " << r.rounds
                  << "轮 | 重传" << r.retrans << "次 | "
                  << "交付 " << r.delivered.size() << "/" << r.delivered.size()
                  << " | 信道:发" << r.ch_sent
                  << "/丢" << r.ch_lost << "/错" << r.ch_corrupt << std::endl;
    }
    std::cout << "\n  总计: " << passed << "/" << results.size() << " 通过" << std::endl;
}
