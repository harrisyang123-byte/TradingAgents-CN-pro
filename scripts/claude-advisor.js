export const meta = {
  name: 'claude-advisor',
  description: '组合顾问四层全链路分析 — Claude Code Agent 替代 LangGraph',
  phases: [
    { title: '数据收集', detail: '持仓/PE/Tier1/敞口/市场数据' },
    { title: 'L1-行业诊断', detail: '市场策略师 ↔ 反向者 → 裁判' },
    { title: 'L2-标的筛选', detail: 'Scout 6维评分 → 候选池' },
    { title: 'L3-组合辩论', detail: '分析师+策略师+侦察兵 红队辩论' },
    { title: 'L4-CIO处方', detail: 'CIO → 风控总监 → CIO终裁' },
    { title: '保存结果', detail: '写 MongoDB → 前端可见' },
  ],
}

const PORTFOLIO = {
  code: '6a094caea814b57d3357fa0b',
  path: '/Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn',
}

// ── Phase 1: 数据收集 ─────────────────────────────────

phase('数据收集')

const portfolioData = await agent({
  label: 'collect-data',
  prompt: `你是一个数据收集 agent。你的任务是为用户组合顾问分析收集全部基础数据。

工作目录: ${PORTFOLIO.path}
用户ID: ${PORTFOLIO.code}

请依次执行以下 Python 命令，收集所有数据并存为 JSON 文件:

1. 持仓数据:
PYTHONPATH=. .venv/bin/python -c "
import asyncio, json
from app.core.database import init_database, get_mongo_db
from app.services.portfolio_service import PortfolioService
async def run():
    await init_database()
    db = get_mongo_db()
    svc = PortfolioService()
    s = await svc.get_portfolio_summary('${PORTFOLIO.code}')
    # Save to file
    with open('/tmp/portfolio_data.json', 'w') as f:
        json.dump(s, f, ensure_ascii=False, default=str)
    print(f'OK: {len(s.get(\"positions\",[]))} positions, total_assets={s.get(\"total_assets\",0)}')
asyncio.run(run())
"

2. Tier1 报告:
PYTHONPATH=. .venv/bin/python -c "
import asyncio, json
from app.core.database import init_database, get_mongo_db
async def run():
    await init_database()
    db = get_mongo_db()
    reports = await db['analysis_reports'].find({'status':'completed','report_type':{'$ne':'portfolio'}}).sort('created_at',-1).to_list(50)
    result = []
    for r in reports:
        result.append({
            'code': r.get('stock_symbol') or r.get('stock_code',''),
            'name': r.get('stock_name',''),
            'instrument_type': r.get('instrument_type','stock'),
            'recommendation': str(r.get('recommendation',''))[:200],
            'summary': str(r.get('summary',''))[:500],
            'risk_level': r.get('risk_level',''),
            'confidence_score': r.get('confidence_score',0),
            'created_at': str(r.get('created_at',''))[:19],
        })
    with open('/tmp/tier1_reports.json','w') as f:
        json.dump(result, f, ensure_ascii=False)
    print(f'OK: {len(result)} reports')
asyncio.run(run())
"

3. PE 分位（对持仓中的股票标的逐个计算）:
PYTHONPATH=. .venv/bin/python -c "
import asyncio, json
from tradingagents.dataflows.pe_percentile import compute_pe_context, enrich_price_context
async def run():
    import json
    with open('/tmp/portfolio_data.json') as f: s = json.load(f)
    positions = s.get('positions',[])
    stock_positions = [p for p in positions if p.get('instrument_type') in ('stock',None)]
    results = {}
    for p in stock_positions:
        code = p['code']
        market = p.get('market','cn') or 'cn'
        if '.HK' in code: market = 'hk'
        elif not code.replace('.SH','').replace('.SZ','').isdigit(): market = 'us'
        try:
            ctx = compute_pe_context(code, market)
            results[code] = ctx
        except Exception as e:
            results[code] = {'error': str(e)}
    with open('/tmp/pe_context.json','w') as f:
        json.dump(results, f, ensure_ascii=False, default=str)
    print(f'OK: {len(results)} PE contexts')
asyncio.run(run())
"

4. 敞口矩阵:
PYTHONPATH=. .venv/bin/python -c "
import asyncio, json
from app.core.database import init_database
from app.services.portfolio_service import PortfolioService
from app.services.exposure_service import ExposureService
async def run():
    await init_database()
    svc = PortfolioService()
    s = await svc.get_portfolio_summary('${PORTFOLIO.code}')
    exp = ExposureService()
    m = await exp.compute(s)
    result = {
        'hhi': m.hhi if m else 0,
        'penetration_ratio': m.penetration_ratio if m else 0,
        'exposures': [{'code':e.code,'name':e.name,'direct':e.direct_weight,'fund':e.fund_derived_weight,'total':e.total_weight,'sector':e.sector} for e in (m.stock_exposures if m else [])],
        'overlaps': [{'code':e.code,'name':e.name,'total':e.total_weight,'sources':e.fund_sources} for e in (m.top_overlaps if m else [])],
    }
    with open('/tmp/exposure_matrix.json','w') as f:
        json.dump(result, f, ensure_ascii=False, default=str)
    print(f'OK: {len(result[\"exposures\"])} exposures')
asyncio.run(run())
"

所有命令执行完成后，读取全部 JSON 文件并汇总报告。报告包含：
- 持仓总数、总资产、现金占比
- Tier1 报告数量和匹配的持仓数量
- PE 可用率（多少持有股票有 PE 数据）
- 敞口穿透率

如果你的命令中有任何失败，请重试一次。如果仍然失败，记录失败原因。`,
  schema: {
    type: 'object',
    properties: {
      position_count: { type: 'number' },
      total_assets: { type: 'number' },
      cash_ratio: { type: 'number' },
      tier1_matched: { type: 'number' },
      tier1_total: { type: 'number' },
      pe_available: { type: 'number' },
      pe_total: { type: 'number' },
      exposure_count: { type: 'number' },
      fund_penetration_ratio: { type: 'number' },
      data_file_paths: { type: 'object', properties: {
        portfolio: { type: 'string' },
        tier1: { type: 'string' },
        pe: { type: 'string' },
        exposure: { type: 'string' },
      }},
      errors: { type: 'array', items: { type: 'string' } },
    },
    required: ['position_count', 'total_assets', 'cash_ratio'],
  },
})

log(`数据收集完成: ${portfolioData.position_count} 只持仓, PE可用 ${portfolioData.pe_available}/${portfolioData.pe_total}`)


// ── Phase 2: L1 行业诊断 ─────────────────────────────

phase('L1-行业诊断')

const l1Report = await agent({
  label: 'l1-industry-diagnosis',
  prompt: `你是组合顾问的**市场策略师**。你需要基于真实数据为用户 ${PORTFOLIO.code} 的持仓做行业方向诊断。

## 数据文件

持仓数据: ${portfolioData.data_file_paths.portfolio}
敞口数据: ${portfolioData.data_file_paths.exposure}

## 你的工作流

第一步：调用 `get_industry_rankings` 获取行业排名数据
命令: PYTHONPATH=${PORTFOLIO.path}/.venv/bin/python -c "import sys; sys.path.insert(0,'${PORTFOLIO.path}'); from tradingagents.agents.advisors.market_tools import get_industry_rankings; import json; r = get_industry_rankings.invoke({'market':'cn'}); print(json.dumps(r,ensure_ascii=False,default=str)[:3000])"

第二步：对每个用户持仓涉及行业的 Go/NoGo 判定

读取 /tmp/portfolio_data.json 中的 positions。对每个 position 的 industry 做判定：
- 如果你是 A 股散户持有 36 只标的共 60 万，现金 32 万，你有接近 53% 现金
- 现金这么高说明你保守/观望。哪些行业目前值得配？
- 对每个持仓行业需要给出：Go/NoGo/观察 + 该行业当前估值水位 + 驱动因素 + 仓位建议

第三步：输出行业诊断表

你不需要调用工具做复杂计算。基于你读到的数据文件和你的训练知识做判断。关键是要覆盖**用户全部 36 只持仓涉及的行业**，不能只挑几个行业说。`,
})

log(`L1 完成`)


// ── Phase 3: L2 标的筛选 ─────────────────────────────

phase('L2-标的筛选')

const l2Report = await agent({
  label: 'l2-stock-screening',
  prompt: `你是 L2 **侦察兵**，负责筛选优质个股。

## 上下文（来自 L1 行业诊断）

${l1Report.slice(0, 3000)}

## 数据文件

持仓: ${portfolioData.data_file_paths.portfolio}
Tier1 报告: ${portfolioData.data_file_paths.tier1}
PE: ${portfolioData.data_file_paths.pe}

## 你的工作

对 Go 和 观察 行业的持仓标的，逐个评估：

1. 读取 Tier1 报告中的 recommendation（买入/卖出/持有）
2. 读取 PE 分位数据
3. 综合判断该标的是否值得买入、增持、持有、减持或清仓

## 对非持仓的候选新标的

你还可以推荐 L2 候选池中的新标的（基于 Tier1 报告中对未持仓股票的买入评级）。

输出格式：对每个标的给出 action（buy/sell/hold/add/reduce）+ reasoning + 6 维评分（business_model 1-10, moat 1-10, management 1-5, financials 1-10, valuation 低估/合理/偏贵, top_risks）。`,
})

log(`L1→L2 完成`)


// ── Phase 4: L3 组合辩论 ─────────────────────────────

phase('L3-组合辩论')

const contrarianReview = await agent({
  label: 'l3-contrarian',
  prompt: `你是组合构建反向者（Contrarian）。你的职责是**挑战**前面分析的结论。

## 行业分析（L1）
${l1Report.slice(0, 2000)}

## 标的推荐（L2）
${l2Report.slice(0, 2000)}

## 数据
持仓: ${portfolioData.data_file_paths.portfolio}
敞口: ${portfolioData.data_file_paths.exposure}

## 你的任务

1. 挑战 L1 的行业判定：哪些 Go 的判断可能太乐观？哪些 NoGo 可能错杀了机会？
2. 挑战 L2 的标的推荐：Scout 推的标的是不是大路货？有没有错过冷门好公司？
3. 检查组合层面的问题：
   - 基金穿透后真实暴露在哪些底层股票上（读 exposure）
   - 直接把持股 + 基金底层持股重叠是否过度集中
   - 现金 32 万占比 53%——现在应该加仓还是保持？

输出你的挑战意见。要有具体批评，不是泛泛而谈。`,
})

log(`L3 辩论完成`)


// ── Phase 5: L4 CIO 处方 ─────────────────────────────

phase('L4-CIO处方')

const cioDraft = await agent({
  label: 'l4-cio-draft',
  prompt: `你是首席投资官（CIO）。综合所有层级的数据和辩论，输出最终处方。

## L1 行业方向
${l1Report.slice(0, 2000)}

## L2 标的推荐
${l2Report.slice(0, 2000)}

## L3 反向者批评
${contrarianReview.slice(0, 2000)}

## 持仓数据
${portfolioData.data_file_paths.portfolio}
${portfolioData.data_file_paths.exposure}
${portfolioData.data_file_paths.pe}
${portfolioData.data_file_paths.tier1}

## 数据约束
总资产: ¥${portfolioData.total_assets.toLocaleString()}
现金占比: ${portfolioData.cash_ratio}%

## 输出格式

第一部分：敞口诊断（基于穿透数据）
第二部分：行业配置方案（每个行业的目标权重）
第三部分：操作处方（JSON 格式，逐个标的）

每条处方必须含：
- code, name, action(buy/sell/hold/add/reduce/new_position), current_weight, target_weight
- timing(immediate/conditional/scheduled)
- suggested_price(基于 PE 分位的价格区间)
- reasoning, risk_note, priority(urgent/important/optional)

目标：覆盖全部持仓。现金也要处理。`,
})

const riskReview = await agent({
  label: 'l4-risk-review',
  prompt: `你是**风险总监**。审查 CIO 处方中的风险。

## CIO 草案
${cioDraft.slice(0, 4000)}

## 你的审查维度
1. 集中度风险：处方是否导致过度集中（单票 > 30%？单行业 > 50%？）
2. 流动性风险：建议卖出的标的是否有充分的流动性信号
3. Tier1 矛盾检测：Tier1 建议卖的标的是否 CIO 建议持有？标出来
4. PE vs 建议冲突检测：PE 99% 分位估值偏高但 CIO 建议买入？标出来

输出你的审查意见和修正建议。`,
})

const cioFinal = await agent({
  label: 'l4-cio-final',
  prompt: `你是 CIO，做终裁。

## CIO 初稿
${cioDraft.slice(0, 3000)}

## 风险总监审查
${riskReview.slice(0, 3000)}

综合两者意见，做最终裁决：
1. 哪些风险意见你采纳了？
2. 哪些你拒绝了（为什么）？
3. 输出最终处方 JSON

最终格式：
{
  "advice_id": "",
  "cio_verdict": "包含敞口诊断、行业配置方案、综合判断的完整文本",
  "prescription": [
    {"code":"...","name":"...","action":"hold/buy/sell/add/reduce/new_position","current_weight":0,"target_weight":0,"timing":"immediate/conditional/scheduled","suggested_price":"","reasoning":"","risk_note":"","priority":"urgent/important/optional"}
  ]
}

注意：处方必须覆盖全部持仓，每只存量的都要有 action。`,
})

log(`CIO 处方完成`)


// ── Phase 6: 保存结果 ───────────────────────────────

phase('保存结果')

const saveResult = await agent({
  label: 'save-to-mongodb',
  prompt: `将以下 CIO 处方保存到 MongoDB。

UTVIdGhpbmcgQ29uZmlnTWFuYWdlciAtPiBtb25nb2RifCBjeWJlcg==

处方内容（JSON）:
${cioFinal}

保存命令:
PYTHONPATH=${PORTFOLIO.path}/.venv/bin/python -c "
import asyncio, json, uuid
from datetime import datetime
from app.core.database import init_database, get_mongo_db
from app.core.response import ok

async def run():
    await init_database()
    db = get_mongo_db()
    advice_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # 从最终输出提取 prescription
    # CIO 应该在文本中输出 JSON 块
    import re
    match = re.search(r'\`\`\`(?:json)?\\s*(\[.*?\])\\s*\`\`\`', json_text, re.DOTALL)
    if match:
        presc = json.loads(match.group(1))
    else:
        presc = []

    doc = {
        'advice_id': advice_id,
        'user_id': '${PORTFOLIO.code}',
        'status': 'COMPLETED',
        'created_at': now,
        'completed_at': now,
        'cio_verdict': cio_verdict_text,
        'prescription': presc,
        'elapsed_seconds': 0,
        'source': 'claude-code',
    }
    await db['portfolio_advice'].insert_one(doc)
    print(f'Saved: advice_id={advice_id}')
asyncio.run(run())
"

注意：如果 CIO 终裁中的 JSON 没有被正确解析，你需要手动提取。确保保存前 prescription 不为空。

保存成功后，确认:
console.log('Prescription saved to MongoDB');
console.log('Frontend should now display the advice at /portfolio/overview');
`,
})

log(`结果已保存`)
