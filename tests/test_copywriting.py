# -*- coding: utf-8 -*-
import datetime as dt
import unittest

from src.copywriting import render, render_notice, templates_for

TEMPLATES = {
    "default": {
        "生日": "尊敬的 {姓名} {称谓}：\n\n祝您生日快乐!\n\n{项目落款} 敬上",
        "成立周年": "尊敬的 {姓名} {称谓}：\n值贵司成立{周年数}周年之际",
        "入园周年": "祝贵司入园{周年数}周年快乐",
        "英文": "Dear {称谓_en}.{姓名},",
    },
    "联科国际信息产业园": {
        "生日": "尊敬的 {姓名} 总：\n生日快乐！",
        "成立周年": "尊敬的 {姓名} 总：\n值贵司成立{周年数}周年之际",
        "入园周年": "携手走过 {周年数} 载时光",
        "核实": {
            "生日": "联科项目“{企业名称}”企业家{姓名}，{生日日期}生日，与身份证时间一致。【管家核实】",
            "成立周年": "联科项目“{企业名称}”{月}月{日}日（{周}）成立{周年数}周年，企业家为{姓名}，该企业成立时间为{成立日期}，与企知道、企查查时间一致。【管家核实】",
            "入园周年": "联科项目“{企业名称}”{月}月{日}日（{周}）入园{周年数}周年【管家核实】",
        },
    },
}


class TestRender(unittest.TestCase):
    def test_render_birthday_default(self):
        ev = {"category": "生日", "name": "王小明", "gender": "男", "years": 0}
        text = render(ev, TEMPLATES["default"], "联科·滨海智造港")
        self.assertIn("尊敬的 王小明 先生：", text)
        self.assertIn("联科·滨海智造港 敬上", text)
        self.assertNotIn("{", text)

    def test_render_lianke_birthday(self):
        ev = {"category": "生日", "name": "王小明", "gender": "男"}
        tpl = templates_for(TEMPLATES, "联科国际信息产业园")
        text = render(ev, tpl, "x")
        self.assertIn("尊敬的 王小明 总：", text)

    def test_templates_for_fallback(self):
        ev = {"category": "生日", "name": "张三", "gender": "男"}
        tpl = templates_for(TEMPLATES, "不存在的园区")
        self.assertIn("张三", render(ev, tpl, "x"))

    def test_render_female_anniversary(self):
        ev = {"category": "成立周年", "name": "李四", "gender": "女", "years": 12}
        text = render(ev, TEMPLATES["default"], "x")
        self.assertIn("成立12周年", text)
        self.assertIn("女士", text)

    def test_render_foreign_name_english(self):
        ev = {"category": "生日", "name": "JOHN MICHAEL SMITH", "gender": "女"}
        self.assertIn("Dear Ms.JOHN MICHAEL SMITH,",
                      render(ev, TEMPLATES["default"], "x"))


class TestNotice(unittest.TestCase):
    def test_birthday_notice(self):
        ev = {"category": "生日", "company": "某某公司", "name": "王小明", "gender": "男",
              "date": dt.date(1988, 11, 8)}
        notice = render_notice(ev, TEMPLATES["联科国际信息产业园"]["核实"], dt.date(2026, 11, 8))
        self.assertIn("联科项目“某某公司”", notice)
        self.assertIn("1988年11月8日生日", notice)
        self.assertIn("【管家核实】", notice)

    def test_founding_notice(self):
        ev = {"category": "成立周年", "company": "某某公司", "name": "李四", "gender": "男",
              "years": 7, "date": dt.date(2019, 11, 30)}
        notice = render_notice(ev, TEMPLATES["联科国际信息产业园"]["核实"], dt.date(2026, 11, 30))
        self.assertIn("11月30日（周一）成立7周年", notice)
        self.assertIn("企业家为李四", notice)
        self.assertIn("该企业成立时间为2019-11-30", notice)

    def test_no_notice_for_default(self):
        ev = {"category": "生日", "company": "c", "name": "n", "gender": "男",
              "date": dt.date(1988, 11, 8)}
        self.assertEqual(render_notice(ev, TEMPLATES["default"].get("核实"), dt.date(2026, 11, 8)), "")


if __name__ == "__main__":
    unittest.main()
