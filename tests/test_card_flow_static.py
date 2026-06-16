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
        self.assertIn("flowScenarioGrid", js)
        self.assertIn("flowTaskGrid", js)

    def test_card_flow_has_dedicated_styles(self):
        css = read("frontend/style.css")

        for selector in [
            ".flow",
            ".flow-shell",
            ".flow-card",
            ".flow-choice-grid",
            ".flow-choice",
            ".flow-progress",
        ]:
            self.assertIn(selector, css)


if __name__ == "__main__":
    unittest.main()
