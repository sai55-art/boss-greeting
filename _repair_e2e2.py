# -*- coding: utf-8 -*-
# 修复路径字符串的闭引号（chr(34) 免疫版）
P = r'D:\deepseek_space\boss-greeting\_ego\e2e-a.mjs'
Q = chr(34)
s = open(P, encoding='utf-8').read()

paths = ['/api/roster);', '/api/roster/import, {', '/api/templates, {',
         '/api/templates);', '/api/config);', '/api/run, {',
         '/api/preview?date=2026-03-05);', '/api/preview?date=oops);',
         '/api/logs);', '/api/not-exist);']
for tail in paths:
    broken = ', ' + Q + tail
    if tail.endswith(', {'):
        fixed = ', ' + Q + tail[:-3] + Q + ', {'
    else:
        fixed = ', ' + Q + tail[:-2] + Q + ');'
    s = s.replace(broken, fixed)

open(P, 'w', encoding='utf-8').write(s)
print('repaired-2')
