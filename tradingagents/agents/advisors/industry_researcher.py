"""行业研究员 (v3)：B+C 数据注入 → Strategist vs Contrarian 辩论 → 裁判

每个行业独立 spawn，数据源 = LLM 内生知识 + AKShare 硬数据 + 新闻研报。
输出定性景气判断，不直接输出数字权重。
"""

from __future__ import annotations
import json
import logging
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

INDUSTRY_RESEARCH_SYSTEM = """你是 {industry} 行业的专业研究员。你需要对该行业做出投资判断。

## 你的数据源

你会收到以下数据：
1. **行业景气数据**：资金流向、PE分位、北向资金等量化信号
2. **新闻/政策**：近7天相关新闻摘要 (近7天来自AKShare)
3. **宏观背景**：PMI/PPI 等宏观指标
4. **你的训练知识**：你对这个行业的理解（TAM、渗透率、供需格局）

## 行业生命周期模型（用于判断结构性位置）
- **新兴萌芽期**：技术/模式初现 → 高不确定性，小仓位试探
- **期望膨胀期**：市场热炒 → 警惕泡沫
- **泡沫破裂期**：预期落空 → 寻找错杀
- **稳步成长期**：商业模式验证 → 最佳窗口
- **成熟稳定期**：增长放缓 → 买龙头，要安全边际

## 你的任务

### 行业研究员（首发）
综合分析三层数据，输出对该行业的判断：
- **go_nogo**: "Go" / "NoGo" / "观察"
- **vitality_level**: "强烈看好" / "看好" / "中性" / "看空"
- **lifecycle**: 生命周期阶段
- **reasoning**: 详细分析（景气度、安全边际、竞争格局、政策方向）
- **TAM判断**: 市场总规模趋势
- **估值判断**: 当前估值在历史上的位置

### 行业反向者（挑战）
质疑研究员的分析：
- TAM是否被高估？
- 景气度是结构性还是周期性？
- 政策信号是实质利好还是空泛表态？
- 估值便宜有没有价值陷阱的可能？

### 辩论规则
1. 研究员先发言
2. 反向者挑战（1轮）
3. 研究员回应（1轮）
4. 行业裁判做最终判断

## 输出格式

```json
{
  "industry": "{industry}",
  "go_nogo": "Go/NoGo/观察",
  "vitality_level": "强烈看好/看好/中性/看空",
  "lifecycle": "稳步成长期",
  "reasoning": "综合分析",
  "tam_assessment": "TAM规模趋势判断",
  "valuation_assessment": "估值判断",
  "debate_summary": "辩论中双方的分歧点",
  "risk_note": "关键风险"
}
```
"""


async def research_single_industry(
    llm,
    industry: str,
    vitality_data: Optional[Dict[str, Any]] = None,
    news_texts: Optional[list[str]] = None,
    macro_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """对单行业执行完整研究：研究员→反向者→裁判，输出结构化结论。

    Args:
        llm: LLM 实例
        industry: 行业名（18-bucket 体系）
        vitality_data: 景气打分各维度数据
        news_texts: 近7天新闻标题列表
        macro_data: 宏观指标

    Returns:
        结构化结论字典
    """
    # 构建数据上下文
    vitality_context = ""
    if vitality_data:
        score = vitality_data.get("total_score", 0)
        signals = vitality_data.get("signal_breakdown", {})
        completeness = vitality_data.get("data_completeness", 0)
        vitality_context = f"景气总分: {score}，数据完整度: {completeness}\n"
        for key, val in signals.items():
            vitality_context += f"  {key}: {val}\n"

    news_context = ""
    if news_texts:
        news_context = "近7天新闻摘要:\n" + "\n".join(news_texts[:15]) + "\n"

    macro_context = ""
    if macro_data:
        pmi = macro_data.get("pmi", "N/A")
        macro_context = f"PMI: {pmi}\n"

    data_prompt = f"""
## 行业景气数据
{vitality_context or '（无可用的量化信号数据）'}

## 新闻/政策
{news_context or '（无相关新闻数据）'}

## 宏观背景
{macro_context or '（无宏观数据）'}
"""

    # 研究员发言
    researcher_prompt = f"""
你是该行业的首席研究员。请根据你的训练知识和以下数据，做出判断。

{data_prompt}

请输出你的分析（中文），然后输出 JSON 格式的结论。
"""
    researcher_msg = HumanMessage(content=researcher_prompt)
    r1 = await llm.ainvoke([researcher_msg])
    researcher_view = str(r1.content) if hasattr(r1, "content") else str(r1)

    # 反向者挑战
    contrarian_prompt = f"""
你是该行业的反向者（Contrarian）。首席研究员刚刚给出了如下分析，请你挑战它。

研究员观点:
{researcher_view[:3000]}

{data_prompt}

请质疑：他的TAM判断是否乐观了？景气是结构性还是周期性？有什么他忽略的风险？
输出你的挑战（中文），然后输出 JSON 格式的结论。
"""
    c_msg = HumanMessage(content=contrarian_prompt)
    r2 = await llm.ainvoke([c_msg])
    contrarian_view = str(r2.content) if hasattr(r2, "content") else str(r2)

    # 研究员回应
    response_prompt = f"""
反向者提出了以下挑战，请回应：

反向者观点:
{contrarian_view[:3000]}

你的原始分析:
{researcher_view[:2000]}

请回应挑战，维护或修正你的观点。然后输出最终结论 JSON。
"""
    resp_msg = HumanMessage(content=response_prompt)
    r3 = await llm.ainvoke([resp_msg])
    final_view = str(r3.content) if hasattr(r3, "content") else str(r3)

    # 解析最终结论
    conclusion = _parse_industry_conclusion(final_view, industry)

    # 补充辩论记录
    conclusion["debate_history"] = (
        f"[研究员首发]\n{researcher_view[:1500]}\n\n"
        f"[反向者挑战]\n{contrarian_view[:1500]}\n\n"
        f"[研究员回应]\n{final_view[:1500]}"
    )

    return conclusion


def _parse_industry_conclusion(text: str, industry: str) -> Dict[str, Any]:
    """解析行业裁判输出"""
    import re

    default = {
        "industry": industry,
        "go_nogo": "未知",
        "vitality_level": "中性",
        "lifecycle": "",
        "reasoning": "",
        "tam_assessment": "",
        "valuation_assessment": "",
        "debate_summary": "",
        "risk_note": "",
        "debate_history": "",
    }

    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            default.update(result)
        except (json.JSONDecodeError, ValueError):
            pass

    return default
