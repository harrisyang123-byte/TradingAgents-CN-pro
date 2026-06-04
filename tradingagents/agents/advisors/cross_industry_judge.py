"""跨行业权重辩论裁判 (v3)

在 total_weight_limit 约束下，基于各行业的定性景气判断做资源分配，
输出每个行业的 final_weight（加总 = total_weight_limit）。
"""

from __future__ import annotations
import json
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


CROSS_INDUSTRY_JUDGE_SYSTEM = """你是跨行业配置裁判。你负责在总股票仓位限额内分配各行业权重。

## 你的输入
1. **total_weight_limit**：总仓位上限（如60%），来自宏观裁判
2. **各行业研究结论**：go_nogo + vitality_level + reasoning

## 你的任务

这不是简单的归一化——这是一个资源分配决策。

### 分配原则
1. Go 的行业获得配额，NoGo 的行业配额为 0
2. vitality_level 高（强烈看好/看好）的行业多配
3. vitality_level 低（中性/看空）的行业少配或不配
4. 考虑各行业的 reasoning（估值贵/便宜、景气结构性/周期性）
5. 所有行业 final_weight 加总 = total_weight_limit
6. 单行业不超过 max_industry_weight（默认 30%）

### 分配方法
把 total_weight_limit 视为限量的资源，你有判断权决定怎么分。
不按比例缩放，而是基于你对各行业的相对判断分配给各个行业。

## 输出格式

```json
{
  "allocations": [
    {"industry": "科技", "final_weight": 25.0, "reasoning": "强烈看好，景气上行期，估值合理"},
    {"industry": "消费", "final_weight": 15.0, "reasoning": "看好，但估值偏高，谨慎配"},
    {"industry": "医药", "final_weight": 0.0, "reasoning": "NoGo，政策风险大"}
  ],
  "total_allocated": 60.0,
  "remaining": 0.0,
  "overall_reasoning": "科技是当前最具配置价值的行业..."
}
```
"""


async def cross_industry_allocate(
    llm,
    industry_results: List[Dict[str, Any]],
    total_weight_limit: float,
    max_industry_weight: float = 30.0,
) -> Dict[str, Any]:
    """跨行业权重分配。

    Args:
        llm: LLM 实例
        industry_results: 各行业研究结论列表
        total_weight_limit: 总股票仓位上限
        max_industry_weight: 单行业上限

    Returns:
        {"allocations": [...], "total_allocated": float, "remaining": float, "overall_reasoning": str}
    """
    # 构建行业输入
    industry_lines = []
    for r in industry_results:
        gng = r.get("go_nogo", "未知")
        vl = r.get("vitality_level", "中性")
        reason = r.get("reasoning", "")[:200]
        industry_lines.append(
            f"- {r.get('industry')}: go_nogo={gng}, vitality_level={vl}, reasoning={reason}"
        )

    prompt = f"""
## 约束
- total_weight_limit: {total_weight_limit}%
- max_industry_weight: {max_industry_weight}%
- 所有行业 final_weight 加总必须 = {total_weight_limit}%

## 各行业研究结论
{chr(10).join(industry_lines)}

## 请输出
在 {total_weight_limit}% 的总仓位上限内，把资源分配给 Go 的行业。
NoGo 的行业配额为 0。

注意：这不是比例缩放。你有判断权。如果你认为某个行业特别值得配，给它更多。
"""

    msg = [{"role": "system", "content": CROSS_INDUSTRY_JUDGE_SYSTEM},
           {"role": "user", "content": prompt}]

    from langchain_core.messages import HumanMessage, SystemMessage
    response = await llm.ainvoke([SystemMessage(content=CROSS_INDUSTRY_JUDGE_SYSTEM),
                                  HumanMessage(content=prompt)])
    text = str(response.content) if hasattr(response, "content") else str(response)

    result = _parse_allocations(text)
    return result


def _parse_allocations(text: str) -> Dict[str, Any]:
    """解析跨行业裁判输出"""
    default = {
        "allocations": [],
        "total_allocated": 0.0,
        "remaining": 0.0,
        "overall_reasoning": "",
    }

    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            default.update(result)
            # 验证加总
            allocs = default.get("allocations", [])
            total = sum(a.get("final_weight", 0) for a in allocs)
            default["total_allocated"] = round(total, 1)
            default["remaining"] = round(default.get("total_allocated", total) - total, 1)
        except (json.JSONDecodeError, ValueError):
            pass

    return default
