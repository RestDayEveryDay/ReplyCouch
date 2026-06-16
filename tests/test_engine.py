import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend import engine, personas


class AnthropicGatewayTest(unittest.TestCase):
    def test_anthropic_client_uses_configured_base_url(self):
        captured = {}
        payload = {
            "extracted_received": "明天下午来我办公室一趟",
            "analysis": {"risk": 20, "signals": []},
            "replies": [
                {
                    "tone": "safe",
                    "text": "好的老师。",
                    "emoji": "不加表情",
                    "rationale": "简洁确认",
                }
            ],
        }

        class FakeAnthropic:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                self.messages = SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        content=[
                            SimpleNamespace(type="text", text=json.dumps(payload))
                        ]
                    )
                )

        fake_module = SimpleNamespace(Anthropic=FakeAnthropic)
        scenario = personas.by_id(personas.SCENARIOS, "mentor")
        my_persona = personas.by_id(personas.MY_PERSONAS, "jinshen")
        their_persona = personas.by_id(personas.THEIR_PERSONAS, "yansu")

        with patch.dict(sys.modules, {"anthropic": fake_module}):
            with patch.object(
                engine,
                "ANTHROPIC_BASE_URL",
                "https://sub-lb.tap365.org",
                create=True,
            ):
                engine._anthropic_generate(
                    scenario,
                    my_persona,
                    their_persona,
                    "明天下午来我办公室一趟",
                    "礼貌确认",
                    None,
                )

        self.assertEqual(
            captured["base_url"],
            "https://sub-lb.tap365.org",
        )

    def test_anthropic_accepts_markdown_wrapped_json_from_gateway(self):
        payload = {
            "extracted_received": "明天下午来我办公室一趟",
            "analysis": {"risk": 20, "signals": []},
            "replies": [
                {
                    "tone": "safe",
                    "text": "好的老师，请问几点方便",
                    "emoji": "",
                    "rationale": "简洁确认",
                }
            ],
        }

        class FakeAnthropic:
            def __init__(self, **_kwargs):
                self.messages = SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        content=[
                            SimpleNamespace(
                                type="text",
                                text=f"```json\n{json.dumps(payload)}\n```",
                            )
                        ]
                    )
                )

        fake_module = SimpleNamespace(Anthropic=FakeAnthropic)
        scenario = personas.by_id(personas.SCENARIOS, "mentor")
        my_persona = personas.by_id(personas.MY_PERSONAS, "jinshen")
        their_persona = personas.by_id(personas.THEIR_PERSONAS, "yansu")

        with patch.dict(sys.modules, {"anthropic": fake_module}):
            result = engine._anthropic_generate(
                scenario,
                my_persona,
                their_persona,
                "明天下午来我办公室一趟",
                "礼貌确认",
                None,
            )

        self.assertEqual(result["replies"][0]["text"], "好的老师，请问几点方便")

    def test_anthropic_retries_malformed_json_from_gateway(self):
        valid_payload = {
            "extracted_received": "在吗？",
            "analysis": {"risk": 30, "signals": []},
            "replies": [
                {
                    "tone": "safe",
                    "text": "在，怎么了",
                    "emoji": "",
                    "rationale": "自然接话",
                }
            ],
        }
        responses = iter(
            [
                '```json\n{"analysis":{"risk":30,"signals":[{"icon":"","meaning":"这个"在吗"很主动"}]}}\n```',
                f"```json\n{json.dumps(valid_payload)}\n```",
            ]
        )
        calls = []

        class FakeAnthropic:
            def __init__(self, **_kwargs):
                def create(**kwargs):
                    calls.append(kwargs)
                    return SimpleNamespace(
                        content=[
                            SimpleNamespace(type="text", text=next(responses))
                        ]
                    )

                self.messages = SimpleNamespace(create=create)

        fake_module = SimpleNamespace(Anthropic=FakeAnthropic)
        scenario = personas.by_id(personas.SCENARIOS, "crush")
        my_persona = personas.by_id(personas.MY_PERSONAS, "zhiqiu")
        their_persona = personas.by_id(personas.THEIR_PERSONAS, "gaoleng")

        with patch.dict(sys.modules, {"anthropic": fake_module}):
            result = engine._anthropic_generate(
                scenario,
                my_persona,
                their_persona,
                "在吗？",
                "自然接话",
                None,
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(result["replies"][0]["text"], "在，怎么了")


if __name__ == "__main__":
    unittest.main()
