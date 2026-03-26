# 变更日志 | Changelog

本文件记录 LCP 协议的所有重要变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-03-26

### 新增
- 初始版本发布
- 完整的 LCP/1.0 协议规范（中文/英文）
- 消息信封格式定义（12 个字段）
- 7 种核心消息类型：ping、pong、chat、task、result、ack、error
- 三级信任模型：未知 → 已识别 → 可信
- Taildrop 传输绑定（规范性）
- HTTP 同步传输绑定（参考性）
- 12 个标准错误码（E001-E099）
- 扩展框架（`lcp-*` 标准扩展 + `x-*` 自定义扩展）
- JSON Schema 验证模式
- Python 参考实现（仅标准库依赖）
- 完整的测试套件
- 4 个典型消息流示例

### 基于
- JeffreyBOT（macOS）与 CloudJeffreyBOT（Windows）之间实际运行的龙虾通信系统
- Tailscale Taildrop 点对点文件传输
- WireGuard 加密隧道

[1.0.0]: https://github.com/nicejeffrey/lobster-comm-protocol/releases/tag/v1.0.0
