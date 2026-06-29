import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class CardFlowStaticTest(unittest.TestCase):
    def test_index_declares_card_flow_shell_and_steps(self):
        html = read("frontend/index.html")

        required_ids = [
            "flowView",
            "flowBackBtn",
            "flowStepTitle",
            "flowStepSub",
            "flowArchiveList",
            "flowArchivePager",
            "flowScenarioGrid",
            "flowTaskGrid",
            "flowSkipBackgroundBtn",
            "flowContinueBackgroundBtn",
        ]
        for element_id in required_ids:
            self.assertIn(f'id="{element_id}"', html)

        self.assertIn("从旧档案进入", html)
        self.assertIn("创建新档案", html)
        self.assertIn("补充背景", html)
        self.assertIn("选填，填了军师更懂情况", html)
        self.assertIn("最近对话", html)
        self.assertNotIn("你的关系", html)
        self.assertIn('class="flow-tools"', html)
        self.assertIn('class="flow-card-back"', html)
        self.assertNotIn('class="home-top flow-top"', html)

    def test_frontend_script_orchestrates_card_flow(self):
        js = read("frontend/app.js")

        required_functions = [
            "showFlowStep",
            "renderFlowArchives",
            "renderFlowScenarios",
            "renderFlowTasks",
            "startCardFlow",
            "continueAfterBackground",
        ]
        for fn in required_functions:
            self.assertRegex(js, rf"function\s+{fn}\s*\(", fn)

        self.assertIn('showView("flow")', js)
        self.assertIn("flowView", js)
        self.assertIn("flowStepTitle", js)
        self.assertIn("flowArchiveList", js)
        self.assertIn("FLOW_ARCHIVE_PAGE_SIZE", js)
        self.assertIn("flowArchivePage", js)
        self.assertIn("renderFlowArchivePager", js)
        self.assertIn("data.items", js)
        self.assertIn("page_size=${FLOW_ARCHIVE_PAGE_SIZE}", js)
        self.assertIn("flowScenarioGrid", js)
        self.assertIn("flowTaskGrid", js)
        self.assertIn("把聊天记录贴上来，军师给你三档能直接发的回复，还会标注一个翻车率。", js)
        self.assertIn("写好一句拿不准的回复，军师给你分析，再写一段仅供参考。", js)
        self.assertIn("军师会把整段聊天读一遍", js)
        self.assertIn("敲下心里的疑问", js)

    def test_card_flow_has_dedicated_styles(self):
        css = read("frontend/style.css")

        for selector in [
            ".flow",
            ".flow-shell",
            ".flow-card",
            ".flow-choice-grid",
            ".flow-choice",
            ".flow-progress",
            ".flow-tools",
            ".flow-card-back",
            ".continue-spotlight",
            ".dash-sec.featured",
        ]:
            self.assertIn(selector, css)


if __name__ == "__main__":
    unittest.main()
