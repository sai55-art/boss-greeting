# -*- coding: utf-8 -*-
# 修复 e2e-a.mjs 中被吞掉的引号（引号一律用 chr(34) 构造）
import re

P = r'D:\deepseek_space\boss-greeting\_ego\e2e-a.mjs'
Q = chr(34)
s = open(P, encoding='utf-8').read()

pairs = [
    ('call(' + Q + 'GET, ' + Q + '/api/roster);',
     'call(' + Q + 'GET' + Q + ', ' + Q + '/api/roster' + Q + ');'),
    ('call(' + Q + 'POST, ' + Q + '/api/roster,',
     'call(' + Q + 'POST' + Q + ', ' + Q + '/api/roster' + Q + ','),
    ('call(' + Q + 'PUT, ',
     'call(' + Q + 'PUT' + Q + ', '),
    ('call(' + Q + 'GET, ',
     'call(' + Q + 'GET' + Q + ', '),
    ('(PASS))',
     '(PASS)' + Q + ')'),
    ('__TEST_USER2__);',
     '__TEST_USER2__' + Q + ');'),
    ('不存在,',
     '不存在' + Q + ','),
]
for a, b in pairs:
    s = s.replace(a, b)

open(P, 'w', encoding='utf-8').write(s)
print('repaired')
