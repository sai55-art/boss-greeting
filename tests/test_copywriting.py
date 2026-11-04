# -*- coding: utf-8 -*-
import datetime as dt
import unittest

from src.copywriting import render, render_notice, templates_for

TEMPLATES = {
    "default": {
        "海报": {
            "生日": "尊敬的 {姓名} {称谓}：\n海报生日\n{项目落款} 敬上",
            "成立周年": "海报成立{周年数}周年",
            "入园周年": "海报入园",
            "英文": "Dear poster",
        },
        "祝福": {
            "生日": "祝福生日 {姓名} {称谓}",
            "成立周年": "祝福成立{周年数}周年",
            "入园周年": "祝福入园{周年数}周年",
            "英文": "Dear bless",
        },
        "核实": {},
    },
    "联科国际信息产业园": {
        "海报": {
            "生日": "海报生日",
            "成立周年": "海报成立",
            "入园周年": "海报入园",
            "英文": "Dear poster",
        },
        "祝福": {
            "生日": "尊敬的 {姓名} 总：祝福生日",
            "成立周年": "祝福成立{周年数}周年",
            "入园周年": "祝福入园{周年数}周年",
            "英文": "Dear bless",
        },
        "核实": {
            "生日": "联科项目“{企业名称}”企业家{姓名}，{生日日期}生日，与身份证时间一致。【管家核实】",
            "成立周年": "联科项目“{企业名称}”{月}月{日}日（{周}）成立{周年数}周年，企业家为{姓名}，该企业成立时间为{成立日期}，与企知道、企查查时间一致。【管家核实】",
            "入园周年": "联科项目“{企业名称}”{月}月{日}日（{周}）入园{周年数}周年【管家核实】",
        },
    },
}


class TestRender(unittest.TestCase):
    def test_default_bless_falls_back_same_as_poster(self):
        ev = {"category": "生日", "name": "王小明", "gender": "男", "years": 0}
        group = templates_for(TEMPLATES, "未知园区")
        poster = render(ev, group["海报"], "落款X")
        bless = render(ev, group["祝福"], "落款X")
        self.assertIn("海报生日", poster)
        self.assertIn("祝福生日 王小明 先生", bless)

    def test_lianke_poster_vs_bless_split(self):
        ev = {"category": "生日", "name": "王小明", "gender": "男"}
        group = templates_for(TEMPLATES, "联科国际信息产业园")
        poster = render(ev, group["海报"], "联科·国际信息产业园")
        bless = render(ev, group["祝福"], "x")
        self.assertIn("海报生日", poster)
        self.assertIn("尊敬的 王小明 总：", bless)
        self.assertNotIn("海报", bless)

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
