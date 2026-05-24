from __future__ import annotations

import unittest

from travelmate.tools.llm_content import content_to_text, message_to_text


class DummyMessage:
    def __init__(self, content):
        self.content = content


class LlmContentTests(unittest.TestCase):
    def test_content_to_text_trims_string(self) -> None:
        self.assertEqual(content_to_text("  hello  "), "hello")

    def test_content_to_text_handles_list_of_text_blocks(self) -> None:
        content = [
            {"type": "text", "text": "Line 1"},
            {"type": "text", "text": "Line 2"},
        ]
        self.assertEqual(content_to_text(content), "Line 1\nLine 2")

    def test_content_to_text_handles_nested_text_value(self) -> None:
        content = [{"text": {"value": "Nested text"}}]
        self.assertEqual(content_to_text(content), "Nested text")

    def test_content_to_text_handles_dict_content_field(self) -> None:
        content = [{"content": "From content field"}]
        self.assertEqual(content_to_text(content), "From content field")

    def test_content_to_text_handles_none(self) -> None:
        self.assertEqual(content_to_text(None), "")

    def test_message_to_text_reads_message_content(self) -> None:
        message = DummyMessage([{"type": "text", "text": "OK"}])
        self.assertEqual(message_to_text(message), "OK")

    def test_message_to_text_accepts_raw_content(self) -> None:
        self.assertEqual(message_to_text("  raw  "), "raw")


if __name__ == "__main__":
    unittest.main()
