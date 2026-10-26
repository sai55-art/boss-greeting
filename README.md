# boss-greeting 老板生日/周年关怀推送

每天 10:00 自动匹配当天生日 / 企业成立周年 / 企业入园周年的老板，
生成祝福文案与海报，通过企业微信推送给指定同事，由其手动转发。

## 快速开始（demo）

```powershell
# 1. 依赖：pandas / openpyxl / Pillow（本机 venv 已复用运行时自带库）

# 2. 导入演示数据（2025年3月清单 -> data/关怀台账.xlsx）
.venv\Scripts\python.exe scripts\import_march.py

# 3. 跑测试
.venv\Scripts\python.exe -m unittest discover -s tests -v

# 4. 干跑某一天（只生成文案+海报，不推送）
.venv\Scripts\python.exe -m src.main --date 2026-03-05 --dry-run
```

产物在 `output/<日期>/项目-类型-MMDD-姓名.jpg`。

## 正式启用

1. `cp config.example.json config.json`，填入企微 corpid / secret / agentid / touser
2. 把正式空白海报背景图放到 `templates/背景-生日.png` 等（缺失时用占位渐变图）
3. 服务器 cron（北京时间）：
   ```
   0 10 * * * cd /path/to/boss-greeting && .venv/bin/python -m src.main >> logs/cron.log 2>&1
   ```

## 管理前端

```powershell
.venv\Scripts\python.exe -X utf8 web\server.py     # http://127.0.0.1:8800
```

六个页面：仪表盘 / 台账管理（CRUD+Excel 导入导出）/ 模板与海报（模板编辑+底图上传）/
推送配置（webhook 在线改+测试发送）/ 发送记录 / 手动运行（按日期预览、干跑、真实推送）。
纯标准库实现，零新增依赖。

## 目录

- `data/关怀台账.xlsx` 唯一数据源（类别/企业名称/所属项目/姓名/职务/性别/节点日期）
- `templates/文案模板.json` 三种节点 + 英文模板
- `config.json` 推送配置（corpid/secret 等，不入库）
- `src/` roster 匹配 / copywriting 文案 / poster 海报 / wecom 推送 / main 入口
- `logs/sent.jsonl` 发送记录（同日防重复；`--force` 可强制重发）
