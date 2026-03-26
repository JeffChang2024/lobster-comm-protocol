"""
LCP/1.0 信封构造与验证测试
"""

import json
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lcp.envelope import (
    create_envelope,
    validate_envelope,
    serialize_envelope,
    get_filename,
    PROTOCOL_VERSION,
    MAX_ENVELOPE_SIZE,
    MAX_MESSAGE_LENGTH,
)


class TestCreateEnvelope(unittest.TestCase):
    """信封构造测试"""

    def test_basic_chat(self):
        env = create_envelope("AliceBot", "BobBot", "chat", "Hello!")
        self.assertEqual(env["lcp"], "1.0")
        self.assertEqual(env["from"], "AliceBot")
        self.assertEqual(env["to"], "BobBot")
        self.assertEqual(env["type"], "chat")
        self.assertEqual(env["message"], "Hello!")
        self.assertIsNone(env["replyTo"])
        self.assertEqual(env["priority"], "normal")
        self.assertEqual(env["ttl"], 86400)
        self.assertIsInstance(env["extensions"], dict)

    def test_ping(self):
        env = create_envelope("A", "B", "ping", "Are you there?")
        self.assertEqual(env["type"], "ping")

    def test_with_reply_to(self):
        reply_id = "550e8400-e29b-41d4-a716-446655440000"
        env = create_envelope("A", "B", "chat", "Reply!", reply_to=reply_id)
        self.assertEqual(env["replyTo"], reply_id)

    def test_with_correlation_id(self):
        env = create_envelope("A", "B", "task", "Do something",
                              correlation_id="550e8400-e29b-41d4-a716-446655440000")
        self.assertEqual(env["correlationId"], "550e8400-e29b-41d4-a716-446655440000")

    def test_with_extensions(self):
        ext = {"lcp-task": {"deadline": "2026-12-31T23:59:59+08:00"}}
        env = create_envelope("A", "B", "task", "Task!", extensions=ext)
        self.assertIn("lcp-task", env["extensions"])

    def test_extension_type(self):
        env = create_envelope("A", "B", "x-heartbeat", "alive")
        self.assertEqual(env["type"], "x-heartbeat")

    def test_uuid_format(self):
        env = create_envelope("A", "B", "chat", "Hi")
        import re
        uuid_re = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        )
        self.assertRegex(env["id"], uuid_re)

    def test_timestamp_has_timezone(self):
        env = create_envelope("A", "B", "chat", "Hi")
        self.assertIn("+", env["timestamp"])

    def test_invalid_lname_rejected(self):
        with self.assertRaises(ValueError):
            create_envelope("123invalid", "B", "chat", "Hi")

    def test_invalid_type_rejected(self):
        with self.assertRaises(ValueError):
            create_envelope("A", "B", "invalid_type", "Hi")

    def test_message_too_long(self):
        with self.assertRaises(ValueError):
            create_envelope("A", "B", "chat", "x" * (MAX_MESSAGE_LENGTH + 1))

    def test_invalid_priority(self):
        with self.assertRaises(ValueError):
            create_envelope("A", "B", "chat", "Hi", priority="critical")

    def test_all_priorities(self):
        for p in ("low", "normal", "high", "urgent"):
            env = create_envelope("A", "B", "chat", "Hi", priority=p)
            self.assertEqual(env["priority"], p)

    def test_all_core_types(self):
        for t in ("ping", "pong", "chat", "task", "result", "ack", "error"):
            env = create_envelope("A", "B", t, "msg")
            self.assertEqual(env["type"], t)

    def test_unicode_message(self):
        env = create_envelope("A", "B", "chat", "你好世界！🦞🌊")
        self.assertEqual(env["message"], "你好世界！🦞🌊")


class TestValidateEnvelope(unittest.TestCase):
    """信封验证测试"""

    def _make_valid_raw(self, **overrides) -> bytes:
        env = create_envelope("AliceBot", "BobBot", "chat", "Hello!")
        env.update(overrides)
        return json.dumps(env, ensure_ascii=False).encode("utf-8")

    def test_valid_envelope(self):
        raw = self._make_valid_raw()
        env, errors = validate_envelope(raw)
        self.assertEqual(len(errors), 0)
        self.assertIsNotNone(env)

    def test_missing_field(self):
        env = create_envelope("A", "B", "chat", "Hi")
        del env["type"]
        raw = json.dumps(env).encode("utf-8")
        _, errors = validate_envelope(raw)
        self.assertTrue(any("E002" in e for e in errors))

    def test_invalid_json(self):
        _, errors = validate_envelope(b"not json at all")
        self.assertTrue(any("E001" in e for e in errors))

    def test_wrong_version(self):
        raw = self._make_valid_raw(lcp="2.0")
        _, errors = validate_envelope(raw)
        self.assertTrue(any("E010" in e for e in errors))

    def test_invalid_uuid(self):
        raw = self._make_valid_raw(id="not-a-uuid")
        _, errors = validate_envelope(raw)
        self.assertTrue(any("E002" in e for e in errors))

    def test_invalid_from_lname(self):
        env = create_envelope("A", "B", "chat", "Hi")
        env["from"] = "123bad"
        raw = json.dumps(env).encode("utf-8")
        _, errors = validate_envelope(raw)
        self.assertTrue(any("E002" in e for e in errors))

    def test_size_exceeded(self):
        huge = b"x" * (MAX_ENVELOPE_SIZE + 1)
        _, errors = validate_envelope(huge)
        self.assertTrue(any("E007" in e for e in errors))

    def test_utf8_bom(self):
        """Windows BOM 兼容性测试"""
        raw = self._make_valid_raw()
        bom_raw = b"\xef\xbb\xbf" + raw
        env, errors = validate_envelope(bom_raw)
        self.assertEqual(len(errors), 0)

    def test_unknown_type_accepted(self):
        """x- 扩展类型应被接受"""
        raw = self._make_valid_raw(type="x-custom")
        _, errors = validate_envelope(raw)
        type_errors = [e for e in errors if "消息类型" in e or "type" in e.lower()]
        self.assertEqual(len(type_errors), 0)


class TestSerialize(unittest.TestCase):
    """序列化测试"""

    def test_serialize_utf8(self):
        env = create_envelope("A", "B", "chat", "你好🦞")
        raw = serialize_envelope(env)
        self.assertIsInstance(raw, bytes)
        decoded = raw.decode("utf-8")
        self.assertIn("你好🦞", decoded)
        # 不应有 ASCII 转义
        self.assertNotIn("\\u", decoded.replace('\\"', ""))

    def test_serialize_roundtrip(self):
        env = create_envelope("A", "B", "chat", "Roundtrip test")
        raw = serialize_envelope(env)
        restored = json.loads(raw)
        self.assertEqual(env, restored)


class TestGetFilename(unittest.TestCase):
    """文件名生成测试"""

    def test_format(self):
        env = {"id": "550e8400-e29b-41d4-a716-446655440000"}
        self.assertEqual(get_filename(env), "msg_550e8400.json")

    def test_prefix_length(self):
        env = create_envelope("A", "B", "chat", "Hi")
        fname = get_filename(env)
        self.assertTrue(fname.startswith("msg_"))
        self.assertTrue(fname.endswith(".json"))
        prefix = fname[4:-5]
        self.assertEqual(len(prefix), 8)


if __name__ == "__main__":
    unittest.main()
