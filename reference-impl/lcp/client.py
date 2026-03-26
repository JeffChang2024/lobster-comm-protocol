"""
LCP/1.0 客户端
High-level client API for the Lobster Communication Protocol.
"""

import json
import os
import time
from collections import deque
from typing import Optional, Dict, List, Any

from .envelope import create_envelope, CORE_TYPES
from .transport import TaildropTransport, LocalTransport
from .errors import LCPError


# 信任等级
TRUST_UNKNOWN = 0
TRUST_RECOGNIZED = 1
TRUST_TRUSTED = 2

# 各信任等级允许的消息类型
TRUST_ALLOWED_TYPES = {
    TRUST_UNKNOWN: frozenset(),
    TRUST_RECOGNIZED: frozenset({"ping", "pong"}),
    TRUST_TRUSTED: CORE_TYPES | frozenset(),  # 所有核心类型 + x- 扩展
}


class LCPClient:
    """
    LCP/1.0 客户端。

    提供高级 API 用于发送、接收和管理 LCP 消息。

    用法：
        client = LCPClient(
            name="JeffreyBOT",
            config_path="config/peers.json"
        )
        client.ping("CloudJeffreyBOT")
        client.send("CloudJeffreyBOT", "Hello! 🦞")
        messages = client.receive()
    """

    def __init__(
        self,
        name: str,
        config_path: Optional[str] = None,
        data_dir: Optional[str] = None,
        transport: str = "taildrop",
        socket_path: Optional[str] = None,
        tz_offset_hours: int = 8,
    ):
        """
        初始化 LCP 客户端。

        Args:
            name: 本地龙虾名称 (LName)
            config_path: 对端配置文件路径
            data_dir: 数据目录（inbox/outbox/archive）
            transport: 传输类型 ("taildrop" 或 "local")
            socket_path: Tailscale socket 路径（可选，自动检测）
            tz_offset_hours: 时区偏移
        """
        self.name = name
        self.tz_offset_hours = tz_offset_hours

        # 数据目录
        self.data_dir = data_dir or os.path.join(os.getcwd(), "data")
        self.inbox_dir = os.path.join(self.data_dir, "inbox")
        self.archive_dir = os.path.join(self.data_dir, "inbox_archive")
        self.outbox_dir = os.path.join(self.data_dir, "outbox")
        for d in (self.inbox_dir, self.archive_dir, self.outbox_dir):
            os.makedirs(d, exist_ok=True)

        # 对端注册表
        self.peers: Dict[str, Dict[str, Any]] = {}
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.peers = config.get("peers", {})

        # 传输层
        if transport == "taildrop":
            self.transport = TaildropTransport(socket_path=socket_path)
        elif transport == "local":
            self.transport = LocalTransport()
        else:
            raise ValueError(f"不支持的传输类型: {transport}")

        # 去重集合（最近 1000 个消息 ID）
        self._seen_ids: deque = deque(maxlen=1000)

    def _get_peer(self, name: str) -> dict:
        """获取对端信息"""
        if name not in self.peers:
            raise LCPError("E003", f"对端 '{name}' 不在注册表中")
        return self.peers[name]

    def _get_trust_level(self, name: str) -> int:
        """获取对端信任等级"""
        if name not in self.peers:
            return TRUST_UNKNOWN
        return self.peers[name].get("trust_level", TRUST_RECOGNIZED)

    def _check_trust(self, name: str, msg_type: str) -> None:
        """检查对端信任等级是否允许该消息类型"""
        level = self._get_trust_level(name)
        if msg_type in TRUST_ALLOWED_TYPES.get(level, frozenset()):
            return
        if level == TRUST_TRUSTED and msg_type.startswith("x-"):
            return  # 可信对端允许扩展类型
        raise LCPError("E004", f"对端 '{name}' 的信任等级 {level} 不允许 '{msg_type}' 消息")

    def _send_envelope(self, envelope: dict) -> bool:
        """发送信封"""
        peer = self._get_peer(envelope["to"])
        if isinstance(self.transport, TaildropTransport):
            return self.transport.send(
                envelope,
                peer["tailscale_name"],
                self.outbox_dir,
            )
        elif isinstance(self.transport, LocalTransport):
            peer_inbox = peer.get("inbox_dir", os.path.join(self.data_dir, "peer_inbox"))
            return self.transport.send(envelope, peer_inbox, self.outbox_dir)
        return False

    # ===== 高级 API =====

    def ping(self, to: str, message: str = "LCP ping 🦞") -> dict:
        """发送 ping 握手请求"""
        env = create_envelope(
            self.name, to, "ping", message,
            tz_offset_hours=self.tz_offset_hours,
        )
        self._send_envelope(env)
        return env

    def pong(self, to: str, reply_to: str, message: str = "LCP pong 🦞") -> dict:
        """发送 pong 握手响应"""
        env = create_envelope(
            self.name, to, "pong", message,
            reply_to=reply_to,
            tz_offset_hours=self.tz_offset_hours,
        )
        self._send_envelope(env)
        # 握手成功，升级对端信任等级
        if to in self.peers:
            self.peers[to]["trust_level"] = TRUST_TRUSTED
        return env

    def send(
        self,
        to: str,
        message: str,
        reply_to: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: str = "normal",
    ) -> dict:
        """发送聊天消息"""
        env = create_envelope(
            self.name, to, "chat", message,
            reply_to=reply_to,
            correlation_id=correlation_id,
            priority=priority,
            tz_offset_hours=self.tz_offset_hours,
        )
        self._send_envelope(env)
        return env

    def task(
        self,
        to: str,
        message: str,
        deadline: Optional[str] = None,
        category: Optional[str] = None,
        priority: str = "normal",
    ) -> dict:
        """发送任务委托"""
        extensions = {}
        if deadline or category:
            task_ext: Dict[str, Any] = {}
            if deadline:
                task_ext["deadline"] = deadline
            if category:
                task_ext["category"] = category
            extensions["lcp-task"] = task_ext

        env = create_envelope(
            self.name, to, "task", message,
            priority=priority,
            extensions=extensions or None,
            tz_offset_hours=self.tz_offset_hours,
        )
        # correlationId 默认为任务自身的 id
        env["correlationId"] = env["id"]
        self._send_envelope(env)
        return env

    def result(
        self,
        to: str,
        message: str,
        reply_to: str,
        correlation_id: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> dict:
        """发送任务结果"""
        extensions = {}
        if data:
            extensions["lcp-result"] = data
        env = create_envelope(
            self.name, to, "result", message,
            reply_to=reply_to,
            correlation_id=correlation_id,
            extensions=extensions or None,
            tz_offset_hours=self.tz_offset_hours,
        )
        self._send_envelope(env)
        return env

    def error(
        self,
        to: str,
        reply_to: str,
        code: str,
        detail: str,
    ) -> dict:
        """发送错误报告"""
        lcp_error = LCPError(code, detail)
        env = create_envelope(
            self.name, to, "error", detail,
            reply_to=reply_to,
            extensions=lcp_error.to_extension(),
            tz_offset_hours=self.tz_offset_hours,
        )
        self._send_envelope(env)
        return env

    def receive(self) -> List[dict]:
        """
        接收消息（检查阶段，不归档）。

        Returns:
            新消息列表
        """
        messages = self.transport.receive(self.inbox_dir)

        # 去重 + 信任检查
        valid = []
        for msg in messages:
            msg_id = msg.get("id")

            # 去重
            if msg_id in self._seen_ids:
                continue
            self._seen_ids.append(msg_id)

            valid.append(msg)

        return valid

    def ack(self, message: dict) -> None:
        """
        确认并归档消息（确认阶段）。

        Args:
            message: 要归档的消息（须含 _filepath）
        """
        filepath = message.get("_filepath")
        if filepath and os.path.exists(filepath):
            self.transport.archive(filepath, self.archive_dir)
