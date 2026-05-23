"""CIO 裁判 (L4 终裁)：芒格思维约束，综合四层数据，输出结构化处方"""

from __future__ import annotations
import json
import re
from tradingagents.utils.logging_init import get_logger

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

        position_lines = []
        for pos in positions:
            position_lines.append(
                f"- {pos.get('code', '?')} ({pos.get('instrument_type', 'stock')}): "
                f"仓位 {pos.get('weight', 0):.1f}%, "
                f"市值 ¥{pos.get('market_value_cny', 0):,.2f}"
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

### 当前持仓
{chr(10).join(position_lines) if position_lines else '无持仓'}

### 资金状况
- 可用现金：¥{available_cash:,.2f}
- 总资产（市值+现金）：¥{total_assets:,.2f}
- 新建仓/加仓金额约束：目标买入金额 ≤ 可用现金 × 目标仓位占比

### 价格与估值数据
{chr(10).join(price_lines) if price_lines else '无价格数据'}
提示：PE 分位越低越便宜（0% = 历史最低），越高越贵（100% = 历史最高）。若某标的无 PE 分位数据（新股/亏损/美股数据不足），请基于 MA20 和当前 PE 绝对值做定性判断。

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

{fund_decision_criteria}### 定量红线
- 单只 ≤ {max_single}%
- 单行业 ≤ {max_industry}%
- 突破红线必须显式说明理由

## 输出格式

### 第一部分：最终判断
综合四层数据的投资结论。说明如何权衡风险总监的审查意见。

### 第二部分：操作处方
```json
[
  {{"code": "...", "name": "...", "instrument_type": "stock/fund/etf", "action": "buy/sell/hold/reduce/add/new_position", "current_weight": 0.0, "target_weight": 0.0,
    "priority": "urgent/important/optional",
    "l1_context": "从宏观裁判报告提取的该标的所属行业判断（生命周期阶段、Go/NoGo、关键风险）",
    "l2_context": "从标的裁判报告提取的护城河评级和过滤结果",
    "suggested_price": "基于 PE 分位和 MA20 的安全边际判断（价格区间而非点价）",
    "max_loss_pct": "逆向验证：如果判断错了，最大亏损百分比及触发场景",
    "five_year_view": "5年后这个生意会更好吗？是/否 + 一句话理由",
    "bias_check": "认知偏差检测（禀赋效应/近因偏差/锚定效应/讲故事陷阱），无显著偏差则标注'无'",
    "reasoning": "...", "risk_note": "..."}}
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

## 输出格式

### 第一部分：总体判断
2-3段话总结投资判断、关键分歧、如何权衡各方意见。

### 第二部分：操作处方
```json
[
  {{"code": "...", "name": "...", "instrument_type": "stock/fund/etf", "action": "buy/sell/hold/reduce/add/new_position", "current_weight": 0.0, "target_weight": 0.0, "reasoning": "...", "risk_note": "..."}}
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
                    # 决策卡片新字段（可选，向后兼容）
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
