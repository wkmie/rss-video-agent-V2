from __future__ import annotations

import json
import unittest

from streamlit.testing.v1 import AppTest


def render_trading_cognition_for_test() -> None:
    import json

    import ui.modules.content_production as content_production

    def fake_api_request(*args, **kwargs):
        return {
            "script_text": json.dumps(
                {
                    "video_titles": ["为什么止损不是看空"],
                    "cover_titles": ["给错误划边界"],
                    "video_tags": ["#交易认知", "#风险管理"],
                    "script": "止损不是预测市场，而是控制错误的代价。",
                },
                ensure_ascii=False,
            ),
            "matched_knowledge": [
                {
                    "title": "止损不是看空",
                    "belief": "止损是给错误划定边界。",
                    "action_rule": "进场前先写明失效条件。",
                }
            ],
            "source_name": "尼克｜交易性格（公开内容蒸馏）",
            "source_notice": "基于公开内容归纳，不构成投资建议。",
        }

    content_production.api_request = fake_api_request
    content_production._trading()


class ContentProductionTradingUITests(unittest.TestCase):
    def test_trading_section_generates_complete_distilled_content(self) -> None:
        app = AppTest.from_function(render_trading_cognition_for_test, default_timeout=10).run()

        self.assertFalse(app.exception)
        self.assertEqual(app.button[0].label, "生成交易认知文案")
        self.assertFalse(app.button[0].disabled)
        self.assertEqual(
            app.selectbox[0].options,
            ["抖音", "视频号", "小红书", "TikTok", "YouTube Shorts"],
        )
        self.assertEqual(
            app.selectbox[1].options,
            ["30秒", "1分钟", "3分钟", "5分钟", "10分钟"],
        )

        app.text_area[0].input("交易为什么要设置止损？").run()
        app.toggle[0].set_value(False).run()
        app.button[0].click().run()

        self.assertFalse(app.exception)
        rendered_text = "\n".join(
            [item.value for item in app.markdown]
            + [item.value for item in app.caption]
            + [item.value for item in app.text]
        )
        self.assertIn("为什么止损不是看空", rendered_text)
        self.assertIn("给错误划边界", rendered_text)
        self.assertIn("#交易认知", rendered_text)
        self.assertIn("尼克｜交易性格（公开内容蒸馏）", rendered_text)
        self.assertIn("基于公开内容归纳，不构成投资建议。", rendered_text)
        self.assertEqual(app.text_area[1].value, "止损不是预测市场，而是控制错误的代价。")
        self.assertEqual(app.expander[0].label, "本次采用的认知依据")


if __name__ == "__main__":
    unittest.main()
