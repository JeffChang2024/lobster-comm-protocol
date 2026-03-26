"""
LCP/1.0 传输层测试（使用 LocalTransport）
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lcp.envelope import create_envelope
from lcp.transport import LocalTransport


class TestLocalTransport(unittest.TestCase):
    """LocalTransport 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.outbox = os.path.join(self.test_dir, "outbox")
        self.inbox = os.path.join(self.test_dir, "inbox")
        self.archive = os.path.join(self.test_dir, "archive")
        self.transport = LocalTransport()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_send_creates_files(self):
        env = create_envelope("A", "B", "chat", "Test message")
        self.transport.send(env, self.inbox, self.outbox)

        # 检查发件箱
        outbox_files = os.listdir(self.outbox)
        self.assertEqual(len(outbox_files), 1)
        self.assertTrue(outbox_files[0].startswith("msg_"))

        # 检查收件箱
        inbox_files = os.listdir(self.inbox)
        self.assertEqual(len(inbox_files), 1)

    def test_receive_reads_messages(self):
        env = create_envelope("A", "B", "chat", "Test receive")
        self.transport.send(env, self.inbox, self.outbox)

        messages = self.transport.receive(self.inbox)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["message"], "Test receive")
        self.assertEqual(messages[0]["from"], "A")

    def test_receive_preserves_filepath(self):
        env = create_envelope("A", "B", "chat", "Hi")
        self.transport.send(env, self.inbox, self.outbox)

        messages = self.transport.receive(self.inbox)
        self.assertIn("_filepath", messages[0])
        self.assertTrue(os.path.exists(messages[0]["_filepath"]))

    def test_archive_moves_file(self):
        env = create_envelope("A", "B", "chat", "Archive me")
        self.transport.send(env, self.inbox, self.outbox)

        messages = self.transport.receive(self.inbox)
        filepath = messages[0]["_filepath"]

        self.transport.archive(filepath, self.archive)

        # 收件箱应为空
        self.assertEqual(len(os.listdir(self.inbox)), 0)
        # 归档目录应有文件
        self.assertEqual(len(os.listdir(self.archive)), 1)

    def test_multiple_messages_ordered(self):
        """消息应按文件名字典序返回"""
        for i in range(5):
            env = create_envelope("A", "B", "chat", f"Message {i}")
            self.transport.send(env, self.inbox, self.outbox)

        messages = self.transport.receive(self.inbox)
        self.assertEqual(len(messages), 5)

    def test_unicode_roundtrip(self):
        env = create_envelope("A", "B", "chat", "你好世界🦞")
        self.transport.send(env, self.inbox, self.outbox)

        messages = self.transport.receive(self.inbox)
        self.assertEqual(messages[0]["message"], "你好世界🦞")

    def test_empty_inbox(self):
        messages = self.transport.receive(self.inbox)
        self.assertEqual(len(messages), 0)


if __name__ == "__main__":
    unittest.main()
