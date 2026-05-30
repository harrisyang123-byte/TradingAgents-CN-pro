"""CIO 裁判 (L4 终裁)：芒格思维约束，综合四层数据，输出结构化处方"""

from __future__ import annotations
import json
import re
from tradingagents.utils.logging_init import get_logger
from app.services.portfolio_audit_service import HEALTH_EMOJI_MAP

logger = get_logger("default")


def create_cio(llm):
    def cio_node(state: dict) -> dict:
        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])
        available_cash = portfolio.get("available_cash", 0.0)
        total_assets = portfolio.get("total_assets", 0.0)
        max_single = state.get("max_single_weight", 30.0)
        max_industry = state.get("max_industry_weight", 50.0)
        max_prescription = state.get("max_prescription_items", 8)

        analyst = state.get("analyst_assessment", "")
        strategist = state.get("strategist_assessment", "")
        scout = state.get("scout_assessment", "")
        advisor_debate = state.get("advisor_debate_state", {})

        market_intel = state.get("market_intel", {})
        macro_judge = state.get("macro_judge_verdict", "")
        stock_judge = state.get("stock_judge_verdict", "")
        risk_review = state.get("risk_director_review", "")
        price_context = state.get("price_context", {})

        is_final = bool(risk_review)
        feedback_context = state.get("feedback_context", "")

        audit_results = state.get("audit_results", {})
        audit_map = {}
        if isinstance(audit_results, list):
            for a in audit_results:
                audit_map[a.get("code", "")] = a

        position_lines = []
        for pos in positions:
            code = pos.get("code", "?")
            name = pos.get("name", "?")
            instr = pos.get("instrument_type", "stock")
            weight = pos.get("weight", 0)
            mv = pos.get("market_value_cny", 0)

            aud = audit_map.get(code, {})
            avg_cost = aud.get("avg_cost", pos.get("avg_cost", 0))
            last_price = aud.get("last_price", pos.get("last_price", 0))
            pnl_pct = aud.get("pnl_pct", pos.get("pnl_pct", 0))
            pnl_cny = aud.get("pnl_cny", pos.get("pnl_cny", 0))
            health = aud.get("health", "ok")
            buy_date = aud.get("buy_date", pos.get("buy_date", ""))

            health_emoji = HEALTH_EMOJI_MAP.get(health, "⚪")
            cost_part = f"成本 ¥{avg_cost}, 现价 ¥{last_price}" if avg_cost and last_price else ""
            pnl_sign = "+" if pnl_pct >= 0 else ""
            pnl_part = f"浮{'+' if pnl_pct >= 0 else ''}{pnl_pct:.1f}%"
            buy_part = f", 买入 {buy_date}" if buy_date else ""

            if cost_part:
                position_lines.append(
                    f"- {health_emoji} {code} {name} ({instr}): 仓位 {weight:.1f}%, 市值 ¥{mv:,.0f}\n"
                    f"  {cost_part}, {pnl_part} (¥{pnl_cny:+,.0f}){buy_part}, 健康分: {health}"
                )
            else:
                position_lines.append(
                    f"- {health_emoji} {code} {name} ({instr}): 仓位 {weight:.1f}%, 市值 ¥{mv:,.0f}"
                )

        has_funds = any(p.get("instrument_type") == "fund" for p in positions)
        fund_decision_criteria = ""
        if has_funds:
            fund_decision_criteria = """### 基金决策标准（额外约束）
- **HOLD 基金的条件**：经理任职 > 3年且业绩稳定、费率合理（股票型 < 1.5%/年）、策略无漂移、无更好的同策略替代品
- **REDEEM/SELL 基金的条件**：基金经理变更（尤其明星经理离职）、连续2年以上跑输基准且归因于选股而非市场风格、费率显著高于同类（>2%/年）、规模过大导致策略受限
- **REPLACE 基金的条件**：发现同策略但费率更低、业绩更稳定的替代基金；或基金策略漂移严重偏离你的配置意图
- **ADD 基金的条件**：某行业/风格暴露不足，且你无法/不愿直接选股，通过被动指数基金或优秀主动基金补足
- **费用比较**：评估基金时始终比较总费率（管理费+托管费+销售服务费），高费率必须有持续的alpha证明
"""

        price_lines = []
        for code, ctx in price_context.items():
            pe_info = ""
            if ctx.get("pe_ttm") and ctx.get("pe_percentile_5y") is not None:
                pe_info = f", PE(TTM) {ctx['pe_ttm']}, 近5年分位 {ctx['pe_percentile_5y']}%"
            elif ctx.get("pe_ttm"):
                pe_info = f", PE(TTM) {ctx['pe_ttm']}"
            ma_info = f", MA20 ¥{ctx['ma20']:,.2f}" if ctx.get("ma20") else ""
            price_lines.append(
                f"- {code}: 现价 ¥{ctx.get('current_price', 'N/A')}{pe_info}{ma_info}"
                f" | 判断: {ctx.get('judgment', '无')}"
            )

        if is_final:
            prompt = f"""你是组合顾问团队的首席投资官 (CIO)。这是你的最终裁决。

你需要综合所有四层数据，考虑风险总监的审查意见，做出最终的组合操作处方。

## 所有层级数据汇总

### L1 行业方向（宏观裁判裁决）
{macro_judge[:2000] if macro_judge else '无 L1 数据'}

### L2 标的筛选（标的裁判裁决）
{stock_judge[:2000] if stock_judge else '无 L2 数据'}

### L3 组合构建
#### 持仓分析师
{analyst[:1500] if analyst else '无评估'}
#### 策略师
{strategist[:1500] if strategist else '无评估'}
#### 侦察兵
{scout[:1500] if scout else '无评估'}
#### L3 辩论记录
{advisor_debate.get('history', '')[:1500]}

### L4 风险总监审查（重点参考）
{risk_review[:2500]}

### 历史处方反馈
{feedback_context[:1500] if feedback_context else '无历史处方数据（首次分析）'}

### 当前持仓
{chr(10).join(position_lines) if position_lines else '无持仓'}

### 资金状况
- 可用现金：¥{available_cash:,.2f}
- 总资产（市值+现金）：¥{total_assets:,.2f}
- 新建仓/加仓金额约束：目标买入金额 ≤ 可用现金 × 目标仓位占比

### 价格与估值数据
{chr(10).join(price_lines) if price_lines else '无价格数据'}
提示：PE 分位越低越便宜（0% = 历史最低），越高越贵（100% = 历史最高）。若某标的无 PE 分位数据（新股/亏损/美股数据不足），请基于 MA20 和当前 PE 绝对值做定性判断。

## 存量诊断 vs 增量探索

你的处方必须区分两类本质不同的决策：

### 存量体检（现有持仓）
基于成本/盈亏/持有时间/基本面，对每只持仓判定：
- **hold (持有不动)**：成本区间合理、权重正常、基本面无恶化
- **add (加仓)**：亏损但有基本面支撑、当前仓位低于目标
- **reduce (减仓)**：亏损 >5% 且基本面恶化、或盈利 >30% 有止盈需求
- **sell (清仓)**：亏损 >20% 且无基本面支撑、或行业逻辑已破
- 锚定效应警告：不要因为亏损不舍得卖（"等回本就卖"是最危险的认知偏差）

### 增量探索（新机会）
- 候选标的 + 入场条件（价格区间、PE分位）
- 必须明确：替代哪只现有持仓（如果新增，哪只减持）
- 如果"卖掉A换B"：在两条处方中配对标注
- 没有好机会就空着——20孔卡片不是让你凑数的

## 你的思维约束（必须遵守）

### 20孔卡片（硬限制）
一生只有20次投资机会。本次处方最多 {max_prescription} 条操作。

### 5年视角
每条 BUY/ADD 建议必须自问：5年后这个生意会更好吗？

### 行业生命周期校准
L1 裁判标注为"期望膨胀期"的行业 → 对应的 BUY/ADD 自动降级为 HOLD/观察

### 市场先生
每条 BUY 建议必须标注：这是在利用恐惧（逆向买入）还是顺从狂热（追涨）？

### 逆向验证
每条 BUY/ADD 必须回答：如果这个判断错了，最大亏损是多少？什么情况下会失败？

### 认知偏差检测
做决策前检查：禀赋效应（因持有而不愿卖）、近因偏差（过度重视近期涨跌）、锚定效应（被成本价锚定）

### 讲故事的警告
"AI龙头""新能源标杆""中国的XXX" —— 标签不是买入理由，回到四层过滤器

### 处方质量 > 数量
宁可给 3 条有深度分析的建议，不要给 8 条敷衍的建议。

### 反馈闭环
- 对照历史处方，说明哪些建议被延续、哪些已过时或需要纠正
- 如果历史处方中某操作未执行，分析原因并调整本次建议
- 从历史判断中学习：哪些判断对了、哪些错了？

{fund_decision_criteria}### 定量红线
- 单只 ≤ {max_single}%
- 单行业 ≤ {max_industry}%
- 突破红线必须显式说明理由

### 资金分配框架
你的处方必须在全局资金约束内完成分配：
- **总资产 ¥{total_assets:,.2f}**，可用现金 ¥{available_cash:,.2f}，现金占比 {available_cash / max(total_assets, 1) * 100:.1f}%
- **资金来源-去向必须配对**：
  - 每条 BUY/ADD 的资金来源必须标注（来自现金 / 来自卖出某标的）
  - 每条 REDUCE/SELL 释放的资金必须标注去向（回到现金 / 用于买入某标的）
- **资金平衡检查**：Σ 买入金额 ≤ 可用现金 + Σ 卖出释放金额
- **交易成本考虑**：单边交易成本约 0.1%（A股佣金+印花税），大规模调仓需考虑成本

### 现金管理
- **现金占比**：{available_cash / max(total_assets, 1) * 100:.1f}%，{ '偏高，建议提高资金利用率' if available_cash / max(total_assets, 1) > 0.3 else '合理' if available_cash / max(total_assets, 1) > 0.1 else '偏低，注意保持流动性缓冲' }
- **闲置资金建议**：超过 10% 的闲置现金可配置货币基金（如 511880 银华日利）或国债逆回购（GC001/R-001），年化约 1.5-3%
- **现金缓冲**：建议始终保持总资产 5-10% 的现金缓冲，以应对调仓机会和紧急赎回需求
- **处方中考虑**：不建议为了"把现金花完"而勉强买入——没有好机会就持有现金

### 再平衡机制
- **定期再平衡**：建议每季度或每半年检视一次组合，恢复目标权重
- **阈值触发**：当某标的权重偏离目标 ±5pp（如目标 10% 实际 16%）时触发再平衡
- **机会触发**：L1/L2 裁判发现高值博率机会时主动调仓
- **处方标注**：若操作为再平衡驱动（而非基本面变化），在 reasoning 中说明

### 时机条件
每条处方必须标注执行时机：
- **immediate（立即执行）**：当前价格合理，应立刻操作
- **conditional（条件触发）**：等待特定条件满足后再执行（如回调至某价位、PE 分位降低）
- **scheduled（定期执行）**：作为定期再平衡的一部分，不急于操作
- 若为 conditional，必须写明触发条件（价格阈值 / PE 分位 / 技术指标 / 事件）
- 处方中 timing 字段使用以上三个枚举值之一

## 输出格式

### 第一部分：最终判断
综合四层数据的投资结论。说明如何权衡风险总监的审查意见。

### 第二部分：操作处方
```json
[
  {{"code": "...", "name": "...", "instrument_type": "stock/fund/etf", "action": "buy/sell/hold/reduce/add/new_position", "current_weight": 0.0, "target_weight": 0.0,
    "split_type": "存量体检/增量探索", "avg_cost": 0.0, "pnl_pct": 0.0,
    "priority": "urgent/important/optional",
    "l1_context": "从宏观裁判报告提取的该标的所属行业判断（生命周期阶段、Go/NoGo、关键风险）",
    "l2_context": "从标的裁判报告提取的护城河评级和过滤结果",
    "suggested_price": "基于 PE 分位和 MA20 的安全边际判断（价格区间而非点价）",
    "max_loss_pct": "逆向验证：如果判断错了，最大亏损百分比及触发场景",
    "five_year_view": "5年后这个生意会更好吗？是/否 + 一句话理由",
    "bias_check": "认知偏差检测（禀赋效应/近因偏差/锚定效应/讲故事陷阱），无显著偏差则标注'无'",
    "timing": "immediate/conditional/scheduled（立即执行/条件触发/定期执行）",
    "capital_source": "资金来源描述（如'来自现金'、'来自减仓000063'、'无（仅持有不动）'）",
    "trigger_condition": "若timing=conditional，填写触发条件（如'回调至PE分位<20%或价格<¥35'）；否则填''",
    "cost_context": "持仓成本上下文（如：成本¥38.50, 浮亏6.3%, 持有180天）",
    "reasoning": "...", "risk_note": "..."}}**
]
```

### 决策卡片字段说明
- priority: urgent=需立即关注（减仓/清仓、重大风险）, important=应该执行（加仓机会、新增优质标的）, optional=可关注（观察列表、小仓位试探）
- l1_context: 在 macro_judge_verdict 中找到该标的所属行业的生命周期判断和 Go/NoGo 建议，提取为一句话
- l2_context: 在 stock_judge_verdict 中找到该标的的护城河评级和过滤结果，提取为一句话。若裁判报告未覆盖 → 标注"未覆盖"或"经由 L2 Scout 筛选"
- suggested_price: 参考 price_context 中的 PE 分位和 MA20，给出安全边际判断。有 PE 分位→引用分位和价格区间；无 PE 分位→基于 MA20 做定性描述
- max_loss_pct: 如果这个判断错了，最大亏损可能多大？什么场景下会发生？
- five_year_view: 用一句话回答"5年后这个生意会更好吗？"
- bias_check: 自检是否有认知偏差（禀赋效应、近因偏差、锚定效应、讲故事陷阱）

action 说明：
- buy: 新买入（之前无持仓）
- new_position: 建议建仓（新标的）
- add: 加仓（已有持仓）
- reduce: 减仓
- sell: 清仓
- hold: 持有不动

用中文回答。"""
        else:
            prompt = f"""你是组合顾问团队的首席投资官 (CIO)。你需要综合四层数据做出组合操作处方的初稿。

## 所有层级数据汇总

### L1 行业方向（宏观裁判裁决）
{macro_judge[:2000] if macro_judge else '无 L1 数据'}

### L2 标的筛选（标的裁判裁决）
{stock_judge[:2000] if stock_judge else '无 L2 数据'}

### L3 组合构建
#### 持仓分析师（关注个股安全边际）
{analyst[:1500] if analyst else '无评估'}

#### 策略师（关注组合构建 + 逆向思维）
{strategist[:1500] if strategist else '无评估'}

#### 侦察兵（关注组合缺口 + 新标的发现）
{scout[:1500] if scout else '无评估'}

#### L3 辩论记录
{advisor_debate.get('history', '')[:1500]}

### 当前持仓
{chr(10).join(position_lines) if position_lines else '无持仓'}

### 资金状况
- 可用现金：¥{available_cash:,.2f}
- 总资产（市值+现金）：¥{total_assets:,.2f}
- 新建仓/加仓金额约束：目标买入金额 ≤ 可用现金 × 目标仓位占比

### 价格与估值数据
{chr(10).join(price_lines) if price_lines else '无价格数据'}
提示：PE 分位越低越便宜（0% = 历史最低），越高越贵（100% = 历史最高）。若某标的无 PE 分位数据（新股/亏损/美股数据不足），请基于 MA20 和当前 PE 绝对值做定性判断。

## 存量诊断 vs 增量探索

你的处方必须区分两类本质不同的决策：

### 存量体检（现有持仓）
基于成本/盈亏/持有时间/基本面，对每只持仓判定：
- **hold (持有不动)**：成本区间合理、权重正常、基本面无恶化
- **add (加仓)**：亏损但有基本面支撑、当前仓位低于目标
- **reduce (减仓)**：亏损 >5% 且基本面恶化、或盈利 >30% 有止盈需求
- **sell (清仓)**：亏损 >20% 且无基本面支撑、或行业逻辑已破
- 锚定效应警告：不要因为亏损不舍得卖（"等回本就卖"是最危险的认知偏差）

### 增量探索（新机会）
- 候选标的 + 入场条件（价格区间、PE分位）
- 必须明确：替代哪只现有持仓（如果新增，哪只减持）
- 如果"卖掉A换B"：在两条处方中配对标注
- 没有好机会就空着——20孔卡片不是让你凑数的

## 你的思维约束（必须遵守）

### 20孔卡片（硬限制）
一生只有20次投资机会。本次处方最多 {max_prescription} 条操作。宁可 3 条好建议，不要 8 条敷衍。

### 5年视角
每条 BUY/ADD 必须自问：5年后这个生意会更好吗？

### 行业生命周期校准
L1 裁判标注为"期望膨胀期"的行业 → BUY/ADD 自动降级为 HOLD/观察

### 市场先生
每条 BUY 标注：在利用恐惧（逆向买入）还是顺从狂热（追涨）？

### 逆向验证
每条 BUY/ADD 必须回答：如果判断错了，最大亏损是多少？

### 认知偏差检测
检查：禀赋效应、近因偏差、锚定效应

### 讲故事的警告
标签不是买入理由，回到四层过滤器。

{fund_decision_criteria}### 定量红线
- 单只 ≤ {max_single}%
- 单行业 ≤ {max_industry}%

### 资金分配框架
你的处方必须在全局资金约束内完成分配：
- **总资产 ¥{total_assets:,.2f}**，可用现金 ¥{available_cash:,.2f}
- **资金来源-去向必须配对**：
  - 每条 BUY/ADD 标注资金来源（来自现金 / 来自卖出某标的）
  - 每条 REDUCE/SELL 标注资金去向（回到现金 / 用于买入某标的）
- **资金平衡**：Σ 买入金额 ≤ 可用现金 + Σ 卖出释放金额

### 现金管理
- 现金占比 {available_cash / max(total_assets, 1) * 100:.1f}%，{'偏高' if available_cash / max(total_assets, 1) > 0.3 else '正常' if available_cash / max(total_assets, 1) > 0.1 else '偏低'}
- 闲置资金建议配置货基（511880）或逆回购，不建议为"花完现金"而勉强买入

### 再平衡机制
- 建议每季度检视组合权重偏离，超过 ±5pp 触发再平衡
- 若操作为再平衡驱动（非基本面变化），在 reasoning 中说明

### 时机条件
每条处方标注执行时机：
- **immediate**（立即）| **conditional**（条件触发）| **scheduled**（定期）
- 若 conditional，写明触发条件（价格阈值 / PE 分位 / 技术指标）

## 输出格式

### 第一部分：总体判断
2-3段话总结投资判断、关键分歧、如何权衡各方意见。

### 第二部分：操作处方
```json
[
  {{"code": "...", "name": "...", "instrument_type": "stock/fund/etf", "action": "buy/sell/hold/reduce/add/new_position", "current_weight": 0.0, "target_weight": 0.0,
    "timing": "immediate/conditional/scheduled", "capital_source": "资金来源", "trigger_condition": "触发条件（非conditional则为空）",
    "reasoning": "...", "risk_note": "..."}}
]
```

用中文回答。"""

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        verdict = response.content if hasattr(response, "content") else str(response)

        prescription = _parse_prescription(verdict)

        result = {
            "prescription": prescription,
        }

        if is_final:
            result["cio_verdict"] = verdict
            logger.info(f"[CIO] 终裁完成，{len(prescription)} 条处方")
        else:
            result["cio_verdict"] = verdict
            logger.info(f"[CIO] 初稿完成，{len(prescription)} 条处方，待风险总监审查")

        return result

    return cio_node


def _parse_prescription(text: str) -> list:
    """从 CIO 输出中提取 JSON 处方"""
    match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if not match:
        match = re.search(r"\[[\s\S]*?\{[\s\S]*?\"code\"[\s\S]*?\}[\s\S]*?\]", text)
    if not match:
        return []
    try:
        items = json.loads(match.group(1) if match.lastindex else match.group(0))
        if not isinstance(items, list):
            return []
        valid = []
        for item in items:
            if isinstance(item, dict) and "code" in item:
                valid.append({
                    "code": str(item.get("code", "")),
                    "name": str(item.get("name", "")),
                    "instrument_type": str(item.get("instrument_type", "stock")),
                    "action": str(item.get("action", "hold")),
                    "current_weight": float(item.get("current_weight", 0)),
                    "target_weight": float(item.get("target_weight", 0)),
                    "reasoning": str(item.get("reasoning", "")),
                    "risk_note": str(item.get("risk_note", "")),
                    # 存量体检 vs 增量探索 字段
                    "split_type": str(item.get("split_type", "")),
                    "avg_cost": str(item.get("avg_cost", "")),
                    "pnl_pct": str(item.get("pnl_pct", "")),
                    "cost_context": str(item.get("cost_context", "")),
                    # 决策卡片新字段（可选，向后兼容）
                    "timing": str(item.get("timing", "immediate")),
                    "capital_source": str(item.get("capital_source", "")),
                    "trigger_condition": str(item.get("trigger_condition", "")),
                    "priority": str(item.get("priority", "optional")),
                    "l1_context": str(item.get("l1_context", "")),
                    "l2_context": str(item.get("l2_context", "")),
                    "suggested_price": str(item.get("suggested_price", "")),
                    "max_loss_pct": str(item.get("max_loss_pct", "")),
                    "five_year_view": str(item.get("five_year_view", "")),
                    "bias_check": str(item.get("bias_check", "")),
                })
        return valid
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[CIO] 处方解析失败: {e}")
        return []
