# -*- coding: utf-8 -*-
# 修复 e2e-b.mjs 被吞引号（chr 免疫版）
P = r'D:\deepseek_space\boss-greeting\_ego\e2e-b.mjs'
s = open(P, encoding='utf-8).read()

S34 = 'String.fromCharCode(34)
pairs = [
    (const page = task.page('p1');,
     const page = task.page('p1'); + chr(10) + const S34 = ' + S34 + ';),
    (includes('成立周年), includes('成立周年')),
    (includes('入园周年), includes('入园周年')),
    (fill('#roster-q, 'E2E, fill('#roster-q', 'E2E),
    (includes('没有匹配), includes('没有匹配')),
    (fill('#roster-q, ');, fill('#roster-q', '');),
    (querySelector('#roster-pager), querySelector('#roster-pager')),
    (includes('共), includes('共')),
    (+ quote2());, + S34 + '2' + S34 + ');),
    (=== '16), === '16')),
    (+ quote1());, + S34 + '1' + S34 + ');),
    (td:nth-child(5))], td:nth-child(5)')],),
    (join('\n), join('\n')),
]
