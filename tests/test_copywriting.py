# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from pathlib import Path

from src.copywriting import render

TEMPLATES = {
    "生日": "尊敬的 {姓名} {称谓}：\n\n祝您生日快乐!\n\n{项目落款} 敬上",
    "成立周年": "尊敬的 {姓名} {称谓}：\n值贵司成立{周年数}周年之际",
    "入园周年": "祝贵司入园{周年数}周年快乐",
    "英文": "Dear {称谓_en}.{姓名},",
}


class TestRender(unittest.TestCase):
    def test_render_birthday(self):
        ev = {"category": "生日", "name": "王小明", "gender": "男", "years": 0}
        text = render(ev, TEMPLATES, "联科·滨海智造港")
        self.assertIn("尊敬的 王小明 先生：", text)
        self.assertIn("联科·滨海智造港 敬上", text)
        self.assertNotIn("{", text)

    def test_render_female_anniversary(self):
        ev = {"category": "成立周年", "name": "李四", "gender": "女", "years": 12}
        self.assertIn("成立12周年", render(ev, TEMPLATES, "x"))
        self.assertIn("女士", render(ev, TEMPLATES, "x"))

    def test_render_foreign_name_english(self):
        ev = {"category": "生日", "name": "JOHN MICHAEL SMITH", "gender": "女"}
        self.assertIn("Dear Ms.JOHN MICHAEL SMITH,",
                      render(ev, TEMPLATES, "x"))


if __name__ == "__main__":
    unittest.main()
