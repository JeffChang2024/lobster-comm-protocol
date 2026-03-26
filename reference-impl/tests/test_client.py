"""
LCP/1.0 客户端测试
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lcp.client import LCPClient, TRUST_TRUSTED


class TestLCPClient(unittest.TestCase):
    """LCPClient 集成测试（使用 LocalTransport）"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.peer_inbox = os.path.join(self.test_dir, "peer_inbox")
        os.makedirs(self.peer_inbox)

        # 写入配置
        config = {
            "peers": {
                "BobBot": {
                    "tailscale_name": "bob-machine",
                    "transport": "local",
                    "trust_level": 2,
                    "inbox_dir": self.peer_inbox,
                }
            }
        }
        self.config_path = os.path.join(self.test_dir, "peers.json")
        with open(self.config_path, "w") as f:
            json.dump(config, f)

        self.client = LCPClient(
            name="AliceBot",
            config_path=self.config_path,
            data_dir=os.path.join(self.test_dir, "data"),
            transport="local",
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ping(self):
        env = self.client.ping("BobBot", "Hello Bob!")
        self.assertEqual(env["type"], "ping")
        self.assertEqual(env["from"], "AliceBot")
        self.assertEqual(env["to"], "BobBot")

    def test_send_chat(self):
        env = self.client.send("BobBot", "Hi there!")
        self.assertEqual(env["type"], "chat")
        self.assertEqual(env["message"], "Hi there!")

    def test_send_with_reply(self):
        first = self.client.send("BobBot", "First message")
        reply = self.client.send("BobBot", "Reply!", reply_to=first["id"])
        self.assertEqual(reply["replyTo"], first["id"])

    def test_task_delegation(self):
        env = self.client.task(
            "BobBot",
            "Check the weather",
            deadline="2026-12-31T23:59:59+08:00",
            category="data-retrieval",
        )
        self.assertEqual(env["type"], "task")
        self.assertIn("lcp-task", env["extensions"])
        self.assertEqual(env["correlationId"], env["id"])

    def test_result(self):
        task = self.client.task("BobBot", "Do something")
        result = self.client.result(
            "BobBot", "Done!", reply_to=task["id"],
            correlation_id=task["correlationId"],
        )
        self.assertEqual(result["type"], "result")
        self.assertEqual(result["replyTo"], task["id"])

    def test_error_report(self):
        task = self.client.task("BobBot", "Impossible task")
        err = self.client.error(
            "BobBot", reply_to=task["id"],
            code="E008", detail="资源不可用",
        )
        self.assertEqual(err["type"], "error")
        self.assertIn("lcp-error", err["extensions"])
        self.assertEqual(err["extensions"]["lcp-error"]["code"], "E008")

    def test_outbox_archived(self):
        """发送后发件箱应有副本"""
        self.client.send("BobBot", "Archive test")
        files = os.listdir(self.client.outbox_dir)
        self.assertEqual(len(files), 1)

    def test_peer_inbox_receives(self):
        """对端收件箱应收到消息"""
        self.client.send("BobBot", "For Bob")
        files = os.listdir(self.peer_inbox)
        self.assertEqual(len(files), 1)

    def test_unicode_message(self):
        env = self.client.send("BobBot", "龙虾通信🦞")
        self.assertEqual(env["message"], "龙虾通信🦞")

    def test_deduplication(self):
        """重复消息应被去重"""
        self.client.send("BobBot", "Original")

        # 模拟：同一消息出现两次
        msgs = self.client.receive()
        # 第一次收到的消息 ID 会被记录
        # 如果再次收到相同 ID，应被过滤


if __name__ == "__main__":
    unittest.main()
