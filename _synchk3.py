import ast

src = open(r'D:\deepseek_space\boss-greeting\web\server.py', encoding='utf-8').read()
ast.parse(src)
print('server.py syntax ok')
