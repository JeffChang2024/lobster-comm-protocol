"""
LCP/1.0 错误码定义
Error code definitions per Section 10 of the LCP specification.
"""

from typing import Dict, Any, Optional


# 标准错误码注册表
ERROR_CODES: Dict[str, Dict[str, Any]] = {
    "E001": {"name": "PARSE_ERROR",       "description": "JSON 解析失败",        "retryable": False},
    "E002": {"name": "INVALID_ENVELOPE",   "description": "必选字段缺失或格式错误", "retryable": False},
    "E003": {"name": "UNKNOWN_SENDER",     "description": "发送方不在对端注册表中", "retryable": False},
    "E004": {"name": "TRUST_VIOLATION",    "description": "消息类型不被发送方的信任等级允许", "retryable": False},
    "E005": {"name": "TTL_EXPIRED",        "description": "消息超过了存活时间",    "retryable": True},
    "E006": {"name": "DUPLICATE_ID",       "description": "消息 ID 已被处理",     "retryable": False},
    "E007": {"name": "SIZE_EXCEEDED",      "description": "信封超过最大尺寸",      "retryable": False},
    "E008": {"name": "TASK_FAILED",        "description": "任务无法完成",          "retryable": True},
    "E009": {"name": "TASK_TIMEOUT",       "description": "任务超过其截止时间",    "retryable": True},
    "E010": {"name": "VERSION_MISMATCH",   "description": "不支持的协议版本",      "retryable": False},
    "E011": {"name": "TRANSPORT_ERROR",    "description": "传输层级别的故障",      "retryable": True},
    "E099": {"name": "INTERNAL_ERROR",     "description": "未指定的内部错误",      "retryable": False},
}


class LCPError(Exception):
    """LCP 协议错误基类"""

    def __init__(self, code: str, detail: Optional[str] = None):
        self.code = code
        info = ERROR_CODES.get(code, {"name": "UNKNOWN", "description": "未知错误", "retryable": False})
        self.name = info["name"]
        self.description = info["description"]
        self.retryable = info["retryable"]
        self.detail = detail or self.description
        super().__init__(f"{code} {self.name}: {self.detail}")

    def to_extension(self) -> dict:
        """生成 lcp-error 扩展对象"""
        return {
            "lcp-error": {
                "code": self.code,
                "name": self.name,
                "detail": self.detail,
                "retryable": self.retryable,
            }
        }
