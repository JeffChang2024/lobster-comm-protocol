"""
LCP/1.0 — 龙虾通信协议参考实现
Lobster Communication Protocol Reference Implementation

仅依赖 Python 标准库，零外部依赖。
"""

__version__ = "1.0.0"
__protocol_version__ = "1.0"

from .envelope import create_envelope, validate_envelope
from .client import LCPClient
from .errors import LCPError, ERROR_CODES

__all__ = [
    "create_envelope",
    "validate_envelope", 
    "LCPClient",
    "LCPError",
    "ERROR_CODES",
]
