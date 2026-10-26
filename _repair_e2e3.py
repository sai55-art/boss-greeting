# -*- coding: utf-8 -*-
# 修复最后三处（chr(34) 免疫版）
P = r'D:\deepseek_space\boss-greeting\_ego\e2e-a.mjs'
Q = chr(34)
s = open(P, encoding='utf-8').read()

pairs = [
    (', ' + Q + '/api/roster, {', ', ' + Q + '/api/roster' + Q + ', {'),
    (', ' + Q + '/api/templates, tpl.j.templates);',
     ', ' + Q + '/api/templates' + Q + ', tpl.j.templates);'),
]
for a, b in pairs:
    s = s.replace(a, b)

open(P, 'w', encoding='utf-8').write(s)
print('repaired-3')
