"""
LCP/1.0 传输层实现
Transport layer implementations per Section 7 of the LCP specification.

支持的传输绑定：
- Taildrop（规范性）
- 本地文件系统（测试用）
"""

import glob
import json
import os
import subprocess
import tempfile
from typing import List, Optional, Dict, Any

from .envelope import serialize_envelope, get_filename, validate_envelope


class TransportError(Exception):
    """传输层错误"""
    pass


class TaildropTransport:
    """
    Taildrop 传输层绑定（规范性）。

    通过 Tailscale Taildrop 在对等节点之间传输 LCP 消息文件。
    """

    # 各平台默认 socket 路径
    DEFAULT_SOCKETS = {
        "darwin_homebrew": "/opt/homebrew/var/run/tailscale/tailscaled.sock",
        "darwin_system": "/var/run/tailscale/tailscaled.sock",
        "linux": "/var/run/tailscale/tailscaled.sock",
    }

    def __init__(
        self,
        socket_path: Optional[str] = None,
        send_timeout: int = 30,
        receive_timeout: int = 10,
    ):
        self.socket_path = socket_path or self._detect_socket()
        self.send_timeout = send_timeout
        self.receive_timeout = receive_timeout

    def _detect_socket(self) -> str:
        """自动检测 Tailscale socket 路径"""
        for path in self.DEFAULT_SOCKETS.values():
            if os.path.exists(path):
                return path
        raise TransportError(
            "未找到 Tailscale socket。请确保 Tailscale 已安装并运行，"
            "或手动指定 socket_path。"
        )

    def send(
        self,
        envelope: dict,
        peer_tailscale_name: str,
        outbox_dir: str,
    ) -> bool:
        """
        通过 Taildrop 发送 LCP 消息。

        Args:
            envelope: LCP 消息信封
            peer_tailscale_name: 对端的 Tailscale 机器名
            outbox_dir: 本地发件箱目录

        Returns:
            True 表示发送成功

        Raises:
            TransportError: 发送失败
        """
        fname = get_filename(envelope)
        payload = serialize_envelope(envelope)

        # 本地归档
        os.makedirs(outbox_dir, exist_ok=True)
        outbox_path = os.path.join(outbox_dir, fname)
        with open(outbox_path, "wb") as f:
            f.write(payload)

        # 写入临时文件并通过 Taildrop 发送
        tmp_path = os.path.join(tempfile.gettempdir(), fname)
        try:
            with open(tmp_path, "wb") as f:
                f.write(payload)

            result = subprocess.run(
                [
                    "tailscale", "--socket", self.socket_path,
                    "file", "cp", tmp_path, f"{peer_tailscale_name}:",
                ],
                capture_output=True,
                text=True,
                timeout=self.send_timeout,
            )

            if result.returncode != 0:
                raise TransportError(
                    f"Taildrop 发送失败 (exit={result.returncode}): {result.stderr.strip()}"
                )

            return True

        except subprocess.TimeoutExpired:
            raise TransportError(f"Taildrop 发送超时（{self.send_timeout}s）")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def receive(self, inbox_dir: str) -> List[dict]:
        """
        从 Taildrop 接收消息（检查阶段，不归档）。

        Args:
            inbox_dir: 本地收件箱目录

        Returns:
            消息列表（包含 _filepath 元数据）
        """
        os.makedirs(inbox_dir, exist_ok=True)

        # 从 Taildrop 拉取待接收文件
        try:
            subprocess.run(
                [
                    "tailscale", "--socket", self.socket_path,
                    "file", "get", inbox_dir + "/",
                ],
                capture_output=True,
                text=True,
                timeout=self.receive_timeout,
            )
        except subprocess.TimeoutExpired:
            pass  # 超时不是错误，可能只是没有新文件

        # 解析消息
        messages = []
        for filepath in sorted(glob.glob(os.path.join(inbox_dir, "msg_*.json"))):
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    raw = f.read().encode("utf-8")
                env, errors = validate_envelope(raw)
                if errors:
                    print(f"WARN: 消息验证失败 {filepath}: {errors}")
                    continue
                env["_filepath"] = filepath
                messages.append(env)
            except Exception as e:
                print(f"WARN: 读取消息失败 {filepath}: {e}")

        return messages

    def archive(self, filepath: str, archive_dir: str) -> None:
        """
        将已处理的消息归档。

        Args:
            filepath: 消息文件路径
            archive_dir: 归档目录
        """
        os.makedirs(archive_dir, exist_ok=True)
        dest = os.path.join(archive_dir, os.path.basename(filepath))
        os.rename(filepath, dest)


class LocalTransport:
    """
    本地文件系统传输（测试用）。

    用于单机测试，直接在本地目录之间复制消息文件。
    """

    def send(
        self,
        envelope: dict,
        peer_inbox_dir: str,
        outbox_dir: str,
    ) -> bool:
        """直接写入对端的收件箱目录"""
        fname = get_filename(envelope)
        payload = serialize_envelope(envelope)

        os.makedirs(outbox_dir, exist_ok=True)
        os.makedirs(peer_inbox_dir, exist_ok=True)

        # 本地归档
        with open(os.path.join(outbox_dir, fname), "wb") as f:
            f.write(payload)

        # 写入对端收件箱
        with open(os.path.join(peer_inbox_dir, fname), "wb") as f:
            f.write(payload)

        return True

    def receive(self, inbox_dir: str) -> List[dict]:
        """读取收件箱中的消息"""
        os.makedirs(inbox_dir, exist_ok=True)
        messages = []
        for filepath in sorted(glob.glob(os.path.join(inbox_dir, "msg_*.json"))):
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    raw = f.read().encode("utf-8")
                env, errors = validate_envelope(raw)
                if errors:
                    continue
                env["_filepath"] = filepath
                messages.append(env)
            except Exception:
                continue
        return messages

    def archive(self, filepath: str, archive_dir: str) -> None:
        """归档消息"""
        os.makedirs(archive_dir, exist_ok=True)
        dest = os.path.join(archive_dir, os.path.basename(filepath))
        os.rename(filepath, dest)
