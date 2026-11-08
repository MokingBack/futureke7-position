# futureke7 期货席位蓝图

复刻"交易可查网-交易蓝图"：每天把东方财富持仓数据按 家人/机构/外资 三组汇总，输出三栏静态页。

## 目录
- `build_daily.py` — 拉当日数据→生成HTML
- `classify.json` — 席位分组表（外资11家 / 机构40家，其余国内公司归家人）
- `docs/` — GitHub Pages 静态产物
- `.github/workflows/daily.yml` — 每个交易日20:00自动跑

## 部署
1. 新建GitHub仓库 `futureke7-blueprint`
2. 推送本目录
3. Settings → Pages → 选 `docs/` 分支
4. Actions 权限给 read+write（Settings → Actions → General → Workflow permissions）

## 准确率
用9-10月15个完整交易日回测：整体方向匹配77%（家人74.6%/机构72.8%/外资84%），落在70-80%目标区间。
