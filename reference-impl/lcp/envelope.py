"""
LCP/1.0 消息信封构造与验证
Envelope construction and validation per Section 4 of the LCP specification.

仅依赖 Python 标准库。
"""

import json
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple, List

# ===== 常量 =====

PROTOCOL_VERSION = "1.0"
MAX_ENVELOPE_SIZE = 1_048_576  # 1 MiB
MAX_MESSAGE_LENGTH = 65_536    # 字符
MAX_LNAME_LENGTH = 64

LNAME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,63}$')
UUID_V4_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
)
CORE_TYPES = frozenset({"ping", "pong", "chat", "task", "result", "ack", "error"})
PRIORITY_LEVELS = frozenset({"low", "normal", "high", "urgent"})


def create_envelope(
    from_name: str,
    to_name: str,
    msg_type: str,
    message: str,
    reply_to: Optional[str] = None,
    correlation_id: Optional[str] = None,
    ttl: int = 86400,
    priority: str = "normal",
    extensions: Optional[Dict[str, Any]] = None,
    tz_offset_hours: int = 8,
) -> dict:
    """
    构造一个符合 LCP/1.0 规范的消息信封。

    Args:
        from_name: 发送方龙虾名称 (LName)
        to_name: 接收方龙虾名称 (LName)
        msg_type: 消息类型 (ping/pong/chat/task/result/ack/error/x-*)
        message: 消息正文
        reply_to: 被回复消息的 UUID（可选）
        correlation_id: 会话关联标识符（可选）
        ttl: 存活时间，秒（默认 86400 = 24小时）
        priority: 优先级（low/normal/high/urgent）
        extensions: 扩展数据（可选）
        tz_offset_hours: 时区偏移小时数（默认 +8 = 亚洲/上海）

    Returns:
        dict: LCP 消息信封

    Raises:
        ValueError: 参数不符合规范
    """
    # 参数验证
    if not LNAME_RE.match(from_name):
        raise ValueError(f"无效的发送方 LName: {from_name}")
    if not LNAME_RE.match(to_name):
        raise ValueError(f"无效的接收方 LName: {to_name}")
    if msg_type not in CORE_TYPES and not msg_type.startswith("x-"):
        raise ValueError(f"无效的消息类型: {msg_type}")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"消息正文超过 {MAX_MESSAGE_LENGTH} 字符限制")
    if priority not in PRIORITY_LEVELS:
        raise ValueError(f"无效的优先级: {priority}")
    if reply_to is not None and not UUID_V4_RE.match(reply_to):
        raise ValueError(f"无效的 replyTo UUID: {reply_to}")

    tz = timezone(timedelta(hours=tz_offset_hours))
    return {
        "lcp": PROTOCOL_VERSION,
        "id": str(uuid.uuid4()),
        "from": from_name,
        "to": to_name,
        "timestamp": datetime.now(tz).isoformat(),
        "type": msg_type,
        "message": message,
        "replyTo": reply_to,
        "correlationId": correlation_id,
        "ttl": ttl,
        "priority": priority,
        "extensions": extensions or {},
    }


def validate_envelope(raw: bytes) -> Tuple[Optional[dict], List[str]]:
    """
    验证 LCP 信封。

    Args:
        raw: 原始字节数据（UTF-8 编码的 JSON）

    Returns:
        (envelope, errors) 元组。
        如果验证通过，errors 为空列表。
        如果验证失败，envelope 可能为 None。
    """
    errors: List[str] = []

    # 大小检查
    if len(raw) > MAX_ENVELOPE_SIZE:
        return None, ["E007: 信封超过 1 MiB 限制"]

    # JSON 解析
    try:
        env = json.loads(raw.decode("utf-8-sig"))
    except UnicodeDecodeError as e:
        return None, [f"E001: 编码错误: {e}"]
    except json.JSONDecodeError as e:
        return None, [f"E001: JSON 解析错误: {e}"]

    if not isinstance(env, dict):
        return None, ["E001: 信封必须是 JSON 对象"]

    # 必选字段检查
    required_fields = ("lcp", "id", "from", "to", "timestamp", "type", "message", "replyTo")
    for field in required_fields:
        if field not in env:
            errors.append(f"E002: 缺少必选字段: {field}")
    if errors:
        return env, errors

    # 版本检查
    if env["lcp"] != PROTOCOL_VERSION:
        errors.append(f"E010: 不支持的协议版本: {env['lcp']}（支持: {PROTOCOL_VERSION}）")

    # UUID 格式
    msg_id = env.get("id", "")
    if not isinstance(msg_id, str) or not UUID_V4_RE.match(msg_id):
        errors.append(f"E002: 'id' 字段 UUID v4 格式无效: {msg_id}")

    # LName 格式
    from_name = env.get("from", "")
    if not isinstance(from_name, str) or not LNAME_RE.match(from_name):
        errors.append(f"E002: 'from' 字段 LName 无效: {from_name}")

    to_name = env.get("to", "")
    if not isinstance(to_name, str) or not LNAME_RE.match(to_name):
        errors.append(f"E002: 'to' 字段 LName 无效: {to_name}")

    # 消息类型
    msg_type = env.get("type", "")
    if not isinstance(msg_type, str):
        errors.append("E002: 'type' 字段必须为字符串")
    elif msg_type not in CORE_TYPES and not msg_type.startswith("x-"):
        errors.append(f"E002: 未知消息类型: {msg_type}")

    # 消息正文
    message = env.get("message", "")
    if not isinstance(message, str):
        errors.append("E002: 'message' 字段必须为字符串")
    elif len(message) > MAX_MESSAGE_LENGTH:
        errors.append(f"E007: 消息正文超过 {MAX_MESSAGE_LENGTH} 字符限制")

    # replyTo
    reply_to = env.get("replyTo")
    if reply_to is not None:
        if not isinstance(reply_to, str) or not UUID_V4_RE.match(reply_to):
            errors.append(f"E002: 'replyTo' 字段 UUID 格式无效: {reply_to}")

    # 可选字段验证
    priority = env.get("priority")
    if priority is not None and priority not in PRIORITY_LEVELS:
        errors.append(f"E002: 无效的优先级: {priority}")

    ttl = env.get("ttl")
    if ttl is not None:
        if not isinstance(ttl, int) or ttl < 0 or ttl > 604800:
            errors.append(f"E002: TTL 值无效（需为 0-604800 的整数）: {ttl}")

    return env, errors


def serialize_envelope(envelope: dict) -> bytes:
    """
    将信封序列化为 UTF-8 JSON 字节。

    Args:
        envelope: LCP 消息信封

    Returns:
        UTF-8 编码的 JSON 字节
    """
    return json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")


def get_filename(envelope: dict) -> str:
    """
    根据规范生成消息文件名。

    Args:
        envelope: LCP 消息信封

    Returns:
        文件名，格式为 msg_{uuid前8位}.json
    """
    return f"msg_{envelope['id'][:8]}.json"
