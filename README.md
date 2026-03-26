# 🦞 Lobster Communication Protocol (LCP)

**龙虾通信协议** — 面向自治 AI 智能体的点对点可信通信标准

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](spec/LCP-1.0-spec-zh.md)
[![Status](https://img.shields.io/badge/status-Proposed_Standard-green.svg)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## 简介

LCP（Lobster Communication Protocol）是一种专为 AI 智能体（"龙虾"）之间点对点通信设计的开放协议标准。它提供了极简、安全、可审计的消息传输框架，使运行在不同机器上的智能体能够跨网络边界进行可靠协调。

### 为什么需要 LCP？

| 现有协议 | 设计目标 | 信任模型 |
|---------|---------|---------|
| HTTP | 人↔机器 | 客户端-服务器 |
| XMPP | 人↔人 | 联邦式 |
| MQTT | 机器↔机器（IoT） | 代理中心 |
| **LCP** | **智能体↔智能体** | **点对点零信任** |

LCP 不依赖中心服务器、消息代理或云服务，所有通信直接在对等节点之间完成。

### 核心特性

- 🔒 **默认加密** — 基于 WireGuard 的端到端加密，完美前向保密
- 📝 **完全可审计** — 所有消息以人类可读的 JSON 存储，留有完整审计轨迹
- 🌐 **传输无关** — 协议层独立于底层传输（Taildrop、HTTP 等）
- ⚡ **极简实现** — 200 行 Python 即可完整实现
- 🔄 **离线容忍** — 异步存储转发，优雅处理对端不在线
- 🏗️ **零基础设施** — 无需中心服务器，无需云服务
- 👁️ **人类监督** — 人类委托人可随时审计所有消息

## 快速开始

### 1. 安装参考实现

```bash
git clone https://github.com/lobster-comm/lobster-protocol.git
cd lobster-protocol
pip install -r reference-impl/requirements.txt
```

### 2. 配置对端

```bash
cp reference-impl/config/peers.example.json reference-impl/config/peers.json
# 编辑 peers.json，填入你的对端信息
```

### 3. 发送第一条消息

```python
from lcp import LCPClient

client = LCPClient(name="MyAgent", config_path="config/peers.json")

# 握手建立信任
client.ping("RemoteAgent")

# 发送消息
client.send("RemoteAgent", "Hello from the ocean floor! 🦞")

# 委托任务
client.task("RemoteAgent", "请查询今天的天气预报")
```

### 4. 接收消息

```python
messages = client.receive()
for msg in messages:
    print(f"[{msg['type']}] {msg['from']}: {msg['message']}")
    client.ack(msg)  # 确认并归档
```

## 协议概览

### 三层架构

```
┌─────────────────────────────────────────────┐
│              应用层（智能体逻辑）              │
├─────────────────────────────────────────────┤
│            协议层（LCP/1.0 信封）             │
├─────────────────────────────────────────────┤
│     传输层（Taildrop / HTTP / 自定义）        │
├─────────────────────────────────────────────┤
│        网络层（WireGuard / Tailscale）        │
└─────────────────────────────────────────────┘
```

### 消息信封

每条 LCP 消息封装在一个标准化的 JSON 信封中：

```json
{
  "lcp": "1.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "from": "JeffreyBOT",
  "to": "CloudJeffreyBOT",
  "timestamp": "2026-03-26T13:56:00.518245+08:00",
  "type": "chat",
  "message": "来自海底的问候！🦞",
  "replyTo": null,
  "correlationId": null,
  "ttl": 86400,
  "priority": "normal",
  "extensions": {}
}
```

### 消息类型

| 类型 | 用途 | 信任要求 |
|------|------|---------|
| `ping` | 握手请求 | 等级 1（已识别） |
| `pong` | 握手响应 | 等级 1（已识别） |
| `chat` | 通用对话 | 等级 2（可信） |
| `task` | 任务委托 | 等级 2（可信） |
| `result` | 任务结果 | 等级 2（可信） |
| `ack` | 接收确认 | 等级 2（可信） |
| `error` | 错误报告 | 等级 2（可信） |
| `x-*` | 自定义扩展 | 等级 2（可信） |

### 三级信任模型

```
未知 (Level 0)  ──配置注册表──▶  已识别 (Level 1)  ──ping/pong──▶  可信 (Level 2)
  消息丢弃                        仅握手消息                       所有消息类型
```

## 典型应用场景

| 场景 | 说明 | 关键消息类型 |
|------|------|-------------|
| 🖥️ **跨设备协作** | Mac 智能体委托 Windows 智能体访问内网资源 | task → result |
| 🏠 **智能家居联动** | 主智能体检测到"快到家"，委托树莓派开空调开灯 | task → result + x-heartbeat |
| 📊 **分布式研究** | 多智能体并行采集中英文信息源，汇总生成报告 | task(并行) → result(异步) |
| 🔧 **DevOps 自动化** | 开发机分析bug，服务器跑测试部署，全链路自动化 | task → ack → result |
| 🔒 **安全巡检** | 中心智能体向多台设备并行发起扫描，汇总异常 | task → result/error |
| 📞 **AI 电话中转** | Mac决策 → 手机打电话 → Windows更新记录 | task 链式传递 |
| 🔍 **代码审查** | 安全/性能/风格智能体并行审查同一PR | task(并行) + correlationId |
| 💾 **灾备协调** | 协调多机备份，hash校验，失败自动报警 | task → result + lcp-result |
| 🧠 **知识共享** | 金融专家智能体 ↔ 技术专家智能体互相请教 | task ↔ result |
| 📧 **工作流串联** | 邮件→摘要→日历→提醒，跨设备自动化流水线 | task 链式 |

> 📖 [查看完整应用场景文档（含时序图）](docs/USE_CASES.md)

## 文档

| 文档 | 说明 |
|------|------|
| [📖 完整规范（中文）](spec/LCP-1.0-spec-zh.md) | LCP/1.0 完整技术规范 |
| [📖 Full Specification (EN)](spec/LCP-1.0-spec-en.md) | LCP/1.0 Full Technical Specification |
| [🎯 典型应用场景](docs/USE_CASES.md) | 10 大应用场景详解 |
| [📐 JSON Schema](schema/lcp-envelope-1.0.json) | 消息信封 JSON Schema |
| [🔧 参考实现](reference-impl/) | Python 参考实现 |
| [📋 示例消息](examples/) | 各类型消息示例 |
| [📄 PDF 版本（中文）](spec/LCP-1.0-spec-zh.pdf) | 规范 PDF 下载 |
| [📄 PDF Version (EN)](spec/LCP-1.0-spec-en.pdf) | Specification PDF Download |

## 项目结构

```
lobster-comm-protocol/
├── README.md                     # 本文件
├── LICENSE                       # CC BY 4.0
├── CONTRIBUTING.md               # 贡献指南
├── CHANGELOG.md                  # 变更日志
├── spec/
│   ├── LCP-1.0-spec-zh.md       # 完整规范（中文）
│   ├── LCP-1.0-spec-en.md       # 完整规范（英文）
│   ├── LCP-1.0-spec-zh.pdf      # PDF 版本（中文）
│   └── LCP-1.0-spec-en.pdf      # PDF 版本（英文）
├── schema/
│   └── lcp-envelope-1.0.json    # JSON Schema
├── reference-impl/
│   ├── lcp/
│   │   ├── __init__.py
│   │   ├── envelope.py           # 信封构造与验证
│   │   ├── transport.py          # 传输层（Taildrop）
│   │   ├── client.py             # LCP 客户端
│   │   └── errors.py             # 错误码定义
│   ├── config/
│   │   └── peers.example.json    # 对端配置示例
│   ├── tests/
│   │   ├── test_envelope.py
│   │   ├── test_transport.py
│   │   └── test_client.py
│   └── requirements.txt
├── examples/
│   ├── handshake.json            # 握手示例
│   ├── chat.json                 # 聊天示例
│   ├── task-delegation.json      # 任务委托示例
│   └── error-recovery.json       # 错误恢复示例
└── docs/
    └── images/
        └── architecture.png      # 架构图
```

## 设计哲学

LCP 的设计受到了以下启发：

- **Unix 哲学** — 做一件事，做好它。消息就是文件。
- **RFC 风格** — 精确的术语（MUST / SHOULD / MAY），机器可验证的 Schema。
- **零信任架构** — 不信任任何未经验证的对端，所有消息需加密传输。
- **龙虾精神** 🦞 — 龙虾拥有坚硬的外壳（安全边界），通过精确的信号通道通信，各自维护领地（宿主机器），在深海中建立可靠连接。

## 路线图

### LCP/1.0 ✅ 当前版本
- [x] 点对点消息传递
- [x] 三级信任模型
- [x] Taildrop 传输绑定
- [x] 7 种核心消息类型
- [x] 扩展框架
- [x] JSON Schema
- [x] Python 参考实现

### LCP/1.1 📋 计划中
- [ ] 消息签名（HMAC-SHA256）
- [ ] 应用层加密（`lcp-encrypted` 扩展）
- [ ] 消息压缩
- [ ] 批量消息传输

### LCP/2.0 🔮 远景
- [ ] 多方（群组）通信
- [ ] 动态对端发现（mDNS / Tailscale API）
- [ ] 二进制载荷编码
- [ ] 多跳路由
- [ ] 流式消息传输

## 贡献

我们欢迎所有形式的贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与。

### 参与方式

- 🐛 [报告问题](../../issues/new?template=bug_report.md)
- 💡 [提出建议](../../issues/new?template=feature_request.md)
- 📖 改进文档
- 🔧 提交参考实现
- 🌐 翻译规范文档

## 参考文献

- [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) — 需求级别关键词
- [RFC 8259](https://datatracker.ietf.org/doc/html/rfc8259) — JSON 数据交换格式
- [RFC 9562](https://datatracker.ietf.org/doc/html/rfc9562) — UUID
- [WireGuard](https://www.wireguard.com/papers/wireguard.pdf) — 下一代内核网络隧道
- [Tailscale](https://tailscale.com/blog/how-tailscale-works) — WireGuard 网状网络

## 许可证

本项目采用 [CC BY 4.0 国际许可协议](LICENSE) 发布。

参考实现代码采用 [MIT 许可证](reference-impl/LICENSE)。

---

<p align="center">
  <strong>🦞 龙虾通信，深海互联 🦞</strong><br>
  <em>Lobsters Communicate, Oceans Connect</em>
</p>
