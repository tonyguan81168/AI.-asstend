---
description: 生成每日A股热点投研报告：综合财联社/韭研公社/同花顺，给出热门主线 + 3只潜力股。用法：/stock-daily [YYYY-MM-DD]
---

参考 `.claude/skills/stock-daily-report/SKILL.md` 生成报告。

步骤：
1. 运行 `python3 stock-research/fetch_hotspots.py`（用户给了日期则加 `--date <日期>`）
2. 读取生成的 `stock-research/reports/<date>/raw.json`，检查 `errors`，缺失的源用 WebSearch 补充并注明
3. 按 skill 中的打分法识别主线，筛选 3 只潜力股
4. 按模板写入 `stock-research/reports/<date>/report.md`，并在对话中输出摘要
5. 若 `stock-research/holdings.json` 有持仓，按 skill 的「持仓次日竞价应对」为每只持仓给出明日竞价动作和条件单价格
6. 严禁编造数据；结尾附风险提示

用户输入的参数：$ARGUMENTS
