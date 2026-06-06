// Workflow: v3 增量编排器 — 宏观 / 行业 / PM / 合成 四段，按阶段缓存跳过
// 取代"每次全量重跑"。每段产物旁有 <out>.meta.json（TTL + 输入指纹）。
// 默认增量：缓存新鲜则跳过；任一段真跑了，其下游强制重跑。
//
// 用法: claude -p "Run workflow v3-advisor with args {dataDir:'...', user_id:'...'}"
// args:
//   dataDir       数据目录（必需）
//   user_id       用户 ID
//   from          从某段强制重跑到结尾   (macro|industry|scout|portfolio|pm|synth)
//   only          只跑某段（调试）       (macro|industry|scout|portfolio|pm|synth)
//   refresh       强制失效某段并重跑 + 下游；"industry:<行业名>" 只刷单个行业
//   full          忽略全部缓存，从头全跑
//   total_weight_limit / cash_floor / max_single_weight / max_industry_weight  约束覆盖

export const meta = {
  name: 'v3-advisor',
  description: 'v3 增量编排器 — 宏观/行业/Scout/组合诊断/PM/合成，按阶段缓存跳过',
  phases: [
    { title: '宏观裁判' },
    { title: '行业研究' },
    { title: 'Scout标的侦察' },
    { title: '组合层诊断' },
    { title: 'PM辩论' },
    { title: '风控合成' },
  ],
};

// ── 参数 ────────────────────────────────────────────────────
const dataDir = args.dataDir || args.data_dir;
const userId = args.user_id || args.userId || '6a094caea814b57d3357fa0b';
const fromStage = args.from || null;
const onlyStage = args.only || null;
const refresh = args.refresh || null;        // "macro"|"industry"|"scout"|"portfolio"|"pm"|"synth"|"industry:<名>"
const full = !!args.full;
const maxIndustryWeight = args.max_industry_weight || 30;
const maxSingle = args.max_single_weight || 30;

const STAGES = ['macro', 'industry', 'scout', 'portfolio', 'pm', 'synth'];

// 每段缓存配置：out 产物、ttl 天（<=0 表示永不缓存）、inputs 指纹输入
const CACHE = {
  macro:     { out: 'macro_verdict.json',        ttl: 1, inputs: ['data_macro.json', 'data_market_temp.json'] },
  industry:  { out: 'industry_allocations.json', ttl: 7, inputs: ['macro_verdict.json', 'industry_list.json'] },
  scout:     { out: 'step4_scout.json',          ttl: 7, inputs: ['industry_allocations.json', 'data_portfolio.json'] },
  portfolio: { out: 'portfolio_diagnosis.json',  ttl: 0, inputs: ['data_portfolio.json', 'industry_allocations.json'] },
  pm:        { out: 'pm_results.json',            ttl: 0, inputs: ['industry_allocations.json', 'step4_scout.json', 'data_portfolio.json'] },
  synth:     { out: 'final_prescription.json',    ttl: 0, inputs: ['pm_results.json', 'portfolio_diagnosis.json', 'data_portfolio.json'] },
};

// ── 缓存门辅助（调用 scripts/stage_cache.py）───────────────────
function p(name) { return `${dataDir}/${name}`; }

function safeName(ind) {
  // 行业名可能含 / 空格 括号，做成安全文件名（保留中文）
  return String(ind).replace(/[\/\\:\*\?"<>\|（）()\s]+/g, '_');
}

async function gateFresh(stage, outName, inputs, ttl) {
  if (full) return false;
  const inputsArg = inputs.map(p).join(',');
  const res = await Bash(
    `python3 scripts/stage_cache.py check --stage ${stage} --out ${p(outName)} --inputs "${inputsArg}" --ttl-days ${ttl}`
  );
  return String(res).trim().endsWith('FRESH');
}

async function gateStamp(stage, outName, inputs, ttl) {
  const inputsArg = inputs.map(p).join(',');
  await Bash(
    `python3 scripts/stage_cache.py stamp --stage ${stage} --out ${p(outName)} --inputs "${inputsArg}" --ttl-days ${ttl}`
  );
}

async function gateInvalidate(outName, dropOutput) {
  await Bash(
    `python3 scripts/stage_cache.py invalidate --out ${p(outName)} ${dropOutput ? '--drop-output' : ''}`
  );
}

// 读 JSON 文件里的某个数字字段（缺失返回默认）
async function readNum(file, key, dflt) {
  try {
    const raw = await Bash(
      `python3 -c "import json,sys;d=json.load(open('${p(file)}'));print(d.get('${key}', ${dflt}))" 2>/dev/null || echo ${dflt}`
    );
    const v = parseFloat(String(raw).trim());
    return Number.isFinite(v) ? v : dflt;
  } catch (e) {
    return dflt;
  }
}

function refreshMatches(stage) {
  if (!refresh) return false;
  return String(refresh).split(':')[0] === stage;
}

// ── 阶段实现 ────────────────────────────────────────────────

// Step 0: 宏观裁判
async function runMacro() {
  phase('宏观裁判');
  log('运行宏观裁判...');
  const macroResult = await agent(
    `Read ${p('data_macro.json')} and ${p('data_market_temp.json')}. \
Perform as Macro Judge. Determine current risk environment and total_weight_limit. \
Output JSON with keys: risk_environment, total_weight_limit (number %), cash_floor (number %), reasoning.`,
    { label: '宏观裁判', phase: '宏观裁判' }
  );
  await Bash(`cat > ${p('macro_verdict.json')} << 'ENDJSON'
${JSON.stringify(macroResult, null, 2)}
ENDJSON`);
  log(`宏观裁判完成: total_weight_limit=${macroResult.total_weight_limit || 70}%`);
}

// Step 1-2: 并行行业研究员 + 反向者（按行业增量）+ 跨行业裁判
async function runIndustry() {
  phase('行业研究');

  // 行业列表
  let industries;
  try {
    const raw = await Bash(
      `cat ${p('industry_list.json')} 2>/dev/null || echo '["消费（必选）","科技","医药健康","金融/保险","新能源（发电）"]'`
    );
    industries = JSON.parse(raw);
  } catch (e) {
    log(`[WARNING] 无法读取行业列表: ${e}`);
    industries = [];
  }
  log(`行业总数 ${industries.length}`);

  // 按行业判断是否需要重研究（per-industry 7天缓存 + 指纹=macro_verdict）
  const toResearch = [];
  for (const ind of industries) {
    const fn = `researcher_${safeName(ind)}.json`;
    const forced = full || refresh === 'industry' || refresh === `industry:${ind}`;
    if (!forced && (await gateFresh('industry-item', fn, ['macro_verdict.json'], 7))) {
      log(`[skip] 行业 ${ind} 研究缓存命中`);
      continue;
    }
    toResearch.push(ind);
  }
  log(`需重研究 ${toResearch.length}/${industries.length} 个行业`);

  // 研究员 → 反向者（仅对需重研究的行业跑）
  if (toResearch.length > 0) {
    await pipeline(
      toResearch,
      async (ind) => {
        const sn = safeName(ind);
        const result = await agent(
          `Read ${p('macro_verdict.json')} first. \
You are the chief industry researcher for ${ind}. \
Read and analyze available data, then output your judgment as JSON.`,
          { label: `研究员:${ind}`, phase: '行业研究' }
        );
        await Bash(`cat > ${p(`researcher_${sn}.json`)} << 'ENDJSON'
${JSON.stringify(result)}
ENDJSON`);
        await gateStamp('industry-item', `researcher_${sn}.json`, ['macro_verdict.json'], 7);
        log(`${ind} 研究员完成`);
        return { industry: ind, sn };
      },
      async (prev) => {
        const { industry: ind, sn } = prev;
        const result = await agent(
          `Read ${p(`researcher_${sn}.json`)}. \
You are the contrarian. Challenge the researcher's conclusions for ${ind}. Output JSON.`,
          { label: `反向者:${ind}`, phase: '行业研究' }
        );
        await Bash(`cat > ${p(`contrarian_${sn}.json`)} << 'ENDJSON'
${JSON.stringify(result)}
ENDJSON`);
        log(`${ind} 反向者完成`);
        return { industry: ind, sn };
      }
    );
  }

  // 汇总全部行业（含缓存命中的）从文件读取
  const allResults = [];
  for (const ind of industries) {
    const sn = safeName(ind);
    let researcher = null, contrarian = null;
    try { researcher = JSON.parse(await Bash(`cat ${p(`researcher_${sn}.json`)} 2>/dev/null || echo 'null'`)); } catch (e) {}
    try { contrarian = JSON.parse(await Bash(`cat ${p(`contrarian_${sn}.json`)} 2>/dev/null || echo 'null'`)); } catch (e) {}
    allResults.push({ industry: ind, researcher, contrarian });
  }
  await Bash(`cat > ${p('all_researchers.json')} << 'ENDJSON'
${JSON.stringify(allResults, null, 2)}
ENDJSON`);
  log(`行业研究汇总完成: ${allResults.length} 个行业`);

  // 跨行业配置裁判（每次都跑——相对便宜）
  phase('行业研究');
  const totalLimit = await readNum('macro_verdict.json', 'total_weight_limit', args.total_weight_limit || 70);
  log('运行跨行业配置裁判...');
  const crossResult = await agent(
    `Read ${p('all_researchers.json')} and ${p('macro_verdict.json')}. \
You are the Cross-Industry Judge. Allocate ${totalLimit}% of capital across industries. \
Max single industry ${maxIndustryWeight}%.

关键要求（必须遵守）：
1. 输出必须覆盖 all_researchers.json 里的**每一个行业**，禁止只输出 Go 行业。
2. 每个行业必须给出明确立场 stance ∈ "超配" | "标配" | "低配"：
   - 超配 = go_nogo "Go" 且配额高于其现持仓权重（加仓）
   - 低配 = 景气差/高估，目标权重低于现持仓（减仓或清仓）
   - 标配 = 维持，但**必须写明为什么维持**（不可空白）
3. 每个行业必须给出 final_weight（目标权重%）。低配行业可以低于现持仓甚至为 0。
4. 禁止「目标=现持仓 且无理由」的空透传行——每行 reasoning 不得为空。
5. 所有行业 final_weight 之和应 ≤ ${totalLimit}%。

Output a JSON array; each item: \
{industry, go_nogo, stance, vitality_level, market, final_weight, reasoning}.`,
    { label: '跨行业配置裁判', phase: '行业研究' }
  );
  await Bash(`cat > ${p('industry_allocations.json')} << 'ENDJSON'
${JSON.stringify(crossResult, null, 2)}
ENDJSON`);
  const n = Array.isArray(crossResult) ? crossResult.length : (crossResult.allocations?.length || 0);
  log(`跨行业配置完成: ${n} 个行业获配额`);
}

// Step 2: Scout 标的侦察（在 Go 行业里挖候选标的，产 step4_scout.json 供 PM 消费）
async function runScout() {
  phase('Scout标的侦察');

  let allocations;
  try {
    allocations = JSON.parse(await Bash(`cat ${p('industry_allocations.json')}`));
  } catch (e) {
    log(`[ERROR] 无法读取行业分配表: ${e}`);
    await Bash(`echo '{"candidates": []}' > ${p('step4_scout.json')}`);
    return { status: 'failed', error: 'no_industry_allocations' };
  }
  const list = Array.isArray(allocations) ? allocations : (allocations.allocations || []);
  const goIndustries = list.filter(
    (a) => a.go_nogo === 'Go' && ['超配', '标配'].includes(a.stance) && (a.final_weight || 0) > 0
  );
  log(`待侦察 Go 行业: ${goIndustries.length} 个`);

  if (goIndustries.length === 0) {
    log('无 Go 行业，跳过 Scout');
    await Bash(`echo '{"candidates": []}' > ${p('step4_scout.json')}`);
    return { status: 'done', candidates: 0 };
  }

  const scoutResult = await agent(
    `Read ${p('industry_allocations.json')} first, then ${p('data_portfolio.json')}, \
${p('data_pe.json')} (if exists), ${p('data_tier1.json')} (if exists).

You are the v3 Scout (标的侦察兵). Search for concrete buyable stocks ONLY in industries where \
go_nogo=="Go" AND stance in {超配,标配}. For each such industry find >=2 candidates. \
Use Bash to call market_tools.get_industry_constituents / get_company_profile / get_financial_summary \
for real constituent & financial data; if tools fail, fall back to your knowledge and mark data_source="llm_knowledge".

关键要求（必须遵守，否则 PM 拿不到候选）：
1. 每个 candidate 的 industry 字段必须与 industry_allocations.json 里的行业名**完全一致**（PM 按名字前缀匹配）。
2. market 用 "cn"/"hk"/"us"；price_range 用 {low,high} 对象；target_position 用数字（百分比）。
3. 每个 Go 行业 >=2 只候选，全部候选 >=5 只，中小盘(<500亿)占比 >=30%。
4. 每只带 6 维 scores（含 total）、financial_data、catalyst、top_risks、recommendation_level。
5. 不推荐用户已重仓(>10%)的标的；现持仓标的可标 is_holding=true 供 PM 决定加减。

Output JSON: {search_scope, candidates:[...], market_cap_distribution}.`,
    { label: 'Scout标的侦察', phase: 'Scout标的侦察' }
  );
  await Bash(`cat > ${p('step4_scout.json')} << 'ENDJSON'
${JSON.stringify(scoutResult, null, 2)}
ENDJSON`);
  const nc = Array.isArray(scoutResult?.candidates) ? scoutResult.candidates.length
    : (Array.isArray(scoutResult) ? scoutResult.length : 0);
  log(`Scout 完成: ${nc} 只候选标的`);
  return { status: 'done', candidates: nc };
}

// Step 3: 组合层诊断（持仓诊断师 → 组合反向者，产 portfolio_diagnosis.json 供 Synthesizer 做减仓决策）
async function runPortfolio() {
  phase('组合层诊断');

  // 持仓诊断师：逐只安全边际 + 全局集中度/一致性/隐形敞口
  const diag = await agent(
    `Read ${p('data_portfolio.json')} first, then ${p('industry_allocations.json')}, \
${p('step4_scout.json')} (if exists), ${p('data_exposure.json')} (if exists), \
${p('data_tier1.json')} (if exists), ${p('data_pe.json')} (if exists).

You are the v3 组合层持仓诊断师. Produce a TWO-level diagnosis and output ONLY JSON (no prose):
1. holdings_assessment: 逐只评估 data_portfolio.json 每只持仓的 safety_margin + assessment \
(继续持有/持有但警惕/建议减仓/建议清仓)，结合该标的行业 stance + PE + Tier1。
2. 全局: concentration(HHI/top5/单标的) + consistency_risks + hidden_exposures。
3. reduce_candidates: 列出所有 assessment∈{建议减仓,建议清仓} 的标的（Synthesizer 减仓的直接依据）。

覆盖 data_portfolio.json 中每只持仓；每只引用至少一个数据源；集中度优先用 data_exposure.json，\
缺失则从持仓权重自算并标 estimated。

JSON shape: {holdings_assessment:[{code,name,current_weight,industry,industry_stance,pe_percentile_5y,valuation_status,safety_margin,assessment,contradictions:[],reasoning}], \
concentration:{hhi,hhi_risk,top5_weight,max_single_weight,max_single_code,findings:[]}, \
consistency_risks:[{type,severity,description,affected_codes:[],potential_impact}], \
hidden_exposures:[], reduce_candidates:[{code,name,current_weight,reason,suggested_action}], diagnosis_summary}`,
    { label: '持仓诊断师', phase: '组合层诊断' }
  );
  await Bash(`cat > ${p('portfolio_diagnosis.json')} << 'ENDJSON'
${JSON.stringify(diag, null, 2)}
ENDJSON`);
  log('持仓诊断完成');

  // 组合反向者：挑战诊断（该减没减 / 该留没留）
  const contrarian = await agent(
    `Read ${p('portfolio_diagnosis.json')} first, then ${p('data_portfolio.json')}, \
${p('industry_allocations.json')}, ${p('step4_scout.json')} (if exists).

You are the v3 组合反向者. Challenge the diagnosis: find 该减没减 (analyst said 继续持有 but should reduce) \
and 该留没留 (analyst said 清仓 but it's a wrongly-killed good stock). At least 2 challenges; not full agreement. \
Each challenge needs argument + suggested_adjustment.

Output JSON: {challenges:[{code,name,analyst_assessment,my_view,argument,suggested_adjustment}], \
missed_reductions:[{code,name,reason}], concentration_challenge, contrarian_summary}.`,
    { label: '组合反向者', phase: '组合层诊断' }
  );
  await Bash(`cat > ${p('portfolio_contrarian.json')} << 'ENDJSON'
${JSON.stringify(contrarian, null, 2)}
ENDJSON`);
  log('组合反向者完成');
  return { status: 'done' };
}

// Step 4: 并行行业 PM 辩论
async function runPm() {
  phase('PM辩论');

  let allocations;
  try {
    allocations = JSON.parse(await Bash(`cat ${p('industry_allocations.json')}`));
  } catch (e) {
    log(`[ERROR] 无法读取行业分配表: ${e}`);
    return { status: 'failed', error: 'no_industry_allocations' };
  }
  const list = Array.isArray(allocations) ? allocations : (allocations.allocations || []);
  const goIndustries = list.filter((a) => a.go_nogo === 'Go' && (a.final_weight || 0) > 0);
  log(`Go行业: ${goIndustries.length} 个（待配仓）`);

  if (goIndustries.length === 0) {
    log('无Go行业需要配仓，跳过PM辩论');
    await Bash(`echo '[]' > ${p('pm_results.json')}`);
    return { status: 'done', pm_results: [] };
  }

  // 为每个 Go 行业准备候选标的（从 Step2 产出 step4_scout.json，缺失则空）
  for (const ind of goIndustries) {
    const indName = ind.industry;
    const sn = safeName(indName);
    try {
      await Bash(`python3 -c "
import json, os
path='${p('step4_scout.json')}'
cands=[]
if os.path.exists(path):
    with open(path) as f: data=json.load(f)
    items = data if isinstance(data, list) else data.get('candidates', [])
    key='${indName.slice(0, 2)}'
    cands=[c for c in items if str(c.get('industry','')).startswith(key) or str(c.get('industry_bucket','')).startswith(key)]
with open('${p(`candidates_${sn}.json`)}','w') as f: json.dump(cands, f, ensure_ascii=False, indent=2)
print('行业 ${indName}: %d 个候选' % len(cands))
" 2>&1`);
    } catch (e) {
      await Bash(`echo '[]' > ${p(`candidates_${sn}.json`)}`);
    }
  }

  const pmResults = [];
  await pipeline(
    goIndustries,
    async (ind) => {
      const indName = ind.industry, sn = safeName(indName), fw = ind.final_weight;
      const result = await agent(
        `Read ${p(`candidates_${sn}.json`)} first, then ${p('industry_allocations.json')}. \
Perform as Aggressive PM for ${indName} industry with ${fw}% quota, max single ${maxSingle}%. Output JSON.`,
        { label: `激进:${indName}`, phase: 'PM辩论' }
      );
      await Bash(`cat > ${p(`aggressive_pm_${sn}.json`)} << 'ENDJSON'
${JSON.stringify(result)}
ENDJSON`);
      log(`${indName} 激进PM完成`);
      return { industry: indName, sn, final_weight: fw };
    },
    async (prev) => {
      const { industry: indName, sn, final_weight: fw } = prev;
      const result = await agent(
        `Read ${p(`candidates_${sn}.json`)} and ${p(`aggressive_pm_${sn}.json`)}. \
Challenge the aggressive PM's plan. Output your conservative plan for ${indName} with ${fw}% quota as JSON.`,
        { label: `保守:${indName}`, phase: 'PM辩论' }
      );
      await Bash(`cat > ${p(`conservative_pm_${sn}.json`)} << 'ENDJSON'
${JSON.stringify(result)}
ENDJSON`);
      log(`${indName} 保守PM完成`);
      return { industry: indName, sn, final_weight: fw };
    },
    async (prev) => {
      const { industry: indName, sn, final_weight: fw } = prev;
      const result = await agent(
        `Read ${p(`candidates_${sn}.json`)}, ${p(`aggressive_pm_${sn}.json`)}, ${p(`conservative_pm_${sn}.json`)}. \
You are the PM Judge. Synthesize both PMs' opinions. Final allocation for ${indName}, ${fw}% quota. Output JSON.`,
        { label: `裁判:${indName}`, phase: 'PM辩论' }
      );
      pmResults.push({ industry: indName, result });
      log(`${indName} PM裁判完成`);
      return { industry: indName, result };
    }
  );

  await Bash(`cat > ${p('pm_results.json')} << 'ENDJSON'
${JSON.stringify(pmResults, null, 2)}
ENDJSON`);
  log(`PM辩论完成，共 ${pmResults.length} 个行业`);
  return { status: 'done', pm_results: pmResults };
}

// Step 5-7: 风控规则 + Risk Director + Portfolio Synthesizer
async function runSynth() {
  phase('风控合成');

  const totalLimit = await readNum('macro_verdict.json', 'total_weight_limit', args.total_weight_limit || 100);
  const cashFloor = await readNum('macro_verdict.json', 'cash_floor', args.cash_floor || 0);

  // 风控规则引擎（纯 Python）
  log('运行风控规则引擎...');
  let violations = [];
  try {
    const result = await Bash(`python3 -c "
import json, os
from tradingagents.agents.advisors.risk_rules import check_pm_positions
with open('${p('pm_results.json')}') as f: pm_results = json.load(f)
all_results = []
for pr in pm_results:
    if isinstance(pr, dict):
        all_results.append(pr.get('result', pr))
# 注入「现金」项：PM 阶段只产 Go 行业，风控规则4(cash_floor)需要现金项，
# 否则 cash_floor>0 时必报违规导致 synth 永远被中止。
# 现金权重 = 100 - 全部非现金行业目标权重之和（取自跨行业裁判分配表）。
cash_weight = None
alloc_path = '${p('industry_allocations.json')}'
if os.path.exists(alloc_path):
    with open(alloc_path) as f: alloc = json.load(f)
    rows = alloc if isinstance(alloc, list) else alloc.get('allocations', [])
    invested = sum(float(r.get('final_weight', 0) or 0) for r in rows if str(r.get('industry','')) != '现金')
    cash_row = next((r for r in rows if str(r.get('industry','')) == '现金'), None)
    cash_weight = float(cash_row.get('final_weight')) if cash_row and cash_row.get('final_weight') is not None else round(100.0 - invested, 1)
if cash_weight is None:
    cash_weight = ${cashFloor}
if not any(str(r.get('industry','')) == '现金' for r in all_results):
    all_results.append({'industry': '现金', 'final_weight': cash_weight,
                        'positions': [{'code': 'CASH', 'target_weight': cash_weight}]})
violations = check_pm_positions(all_results, ${totalLimit}, ${cashFloor}, ${maxSingle})
print(json.dumps(violations, ensure_ascii=False, indent=2))
" 2>&1`);
    violations = JSON.parse(result);
    log(`风控检查: ${violations.length} 条违规`);
  } catch (e) {
    // fail-closed：风控是事前硬拦截，引擎异常时绝不放行（旧实现 violations=[] 会静默通过违规方案）。
    // 注入一条阻断性违规，让下游 abort，而不是让未经风控的处方进入合成。
    log(`[ERROR] 风控引擎执行异常，fail-closed 视为违规并中止合成: ${e}`);
    violations = [{
      industry: '*', rule: 'risk_engine_error', code: '',
      current: 0, limit: 0,
      message: `风控引擎执行异常，已 fail-closed 中止合成（未放行任何方案）：${e}`,
    }];
  }
  await Bash(`cat > ${p('risk_violations.json')} << 'ENDJSON'
${JSON.stringify(violations, null, 2)}
ENDJSON`);

  if (violations.length > 0) {
    log(`发现 ${violations.length} 条违规，需打回PM重做`);
    return { status: 'violations_found', violations };
  }
  log('风控检查通过');

  // Risk Director 双角色辩论
  phase('风控合成');
  const pessimist = await agent(
    `Read ${p('pm_results.json')} and ${p('data_exposure.json')} (if exists). \
Perform as Pessimist Risk Director. Find worst-case scenarios. Output JSON.`,
    { label: '悲观风险总监', phase: '风控合成' }
  );
  await Bash(`cat > ${p('pessimist_risk.json')} << 'ENDJSON'
${JSON.stringify(pessimist)}
ENDJSON`);

  const optimist = await agent(
    `Read ${p('pm_results.json')} and ${p('pessimist_risk.json')}. \
Challenge the pessimist's assumptions. Output JSON.`,
    { label: '乐观风险分析师', phase: '风控合成' }
  );
  await Bash(`cat > ${p('optimist_risk.json')} << 'ENDJSON'
${JSON.stringify(optimist)}
ENDJSON`);

  const riskVerdict = await agent(
    `Read ${p('pm_results.json')}, ${p('pessimist_risk.json')}, ${p('optimist_risk.json')}. \
You are the Risk Judge. Synthesize both views into a final RiskAssessment. Output JSON.`,
    { label: '风控裁判', phase: '风控合成' }
  );
  await Bash(`cat > ${p('risk_assessment.json')} << 'ENDJSON'
${JSON.stringify(riskVerdict)}
ENDJSON`);
  log('风险辩论完成');

  // Portfolio Synthesizer（固定输出 schema，供 ingest_advice.py 直接消费）
  await agent(
    `Read ${p('pm_results.json')}, ${p('industry_allocations.json')}, ${p('risk_assessment.json')}, \
${p('all_researchers.json')}, ${p('portfolio_diagnosis.json')} (if exists), \
${p('portfolio_contrarian.json')} (if exists), ${p('data_portfolio.json')} (if exists).

You are the Portfolio Synthesizer. Do NOT make new investment decisions. Do:
1. Validate the constraint chain (allocations vs PM actuals)
2. Identify gaps (allocated quota not filled by PM)
3. Summarize the industry matrix and final prescription
4. Compute portfolio-level capital allocation (金额)
5. 把组合层诊断落到处方：portfolio_diagnosis.json 的 reduce_candidates（经 portfolio_contrarian.json \
   挑战修正后）必须在 final_prescription 里体现为 action=reduce/sell/clear 的明确卖出条目，\
   每条 risk_note 引用诊断依据（集中度/估值/行业低配）。没有诊断支持的现持仓维持时也要写明维持理由。

关键要求（直接决定前端是否显示「无指导/全持有」，必须遵守）：
- industry_matrix 必须覆盖 industry_allocations.json / all_researchers.json 里的**每一个行业**。
- 每个行业必须带 go_nogo（"Go"/"NoGo"/"观察"）、stance（超配/标配/低配）、vitality_level、market。
- 禁止「target_weight = actual_weight 且 reasoning 为空」的空透传行——标配行业也要写明维持理由。
- final_weight 来自 industry_allocations.json 的目标权重；actual_weight 来自 data_portfolio.json 现持仓权重之和。

写三个文件（严格 JSON，键名照抄）:

A) ${p('industry_matrix.json')}:
   {"constraint_chain_valid": bool, "violations": [...], "matrix": [
     {"industry","source","go_nogo","stance","vitality_level","market","lifecycle",
      "actual_weight","final_weight","gap","scout_triggered","positions":[codes],"reasoning"}
   ]}
   （go_nogo 用 "Go"/"NoGo"/"观察"，下游统一转大写；positions 为该行业涉及标的代码数组）

B) ${p('final_prescription.json')}:
   {"prescription": [
     {"code","name","industry","action","current_weight","target_weight",
      "entry_price_range":{"low","high"},"build_strategy","batch_plan":[...],"reasoning","risk_note","pe_percentile"}
   ], "summary": {"gaps_found","constraint_chain_valid","total_allocated_weight","available_cash"}}
   （action ∈ buy/sell/hold/add/reduce/new_position；industry 必须与 matrix 的 industry 完全一致；覆盖全部现持仓 + 拟买入）

C) ${p('capital_plan.json')} — 组合级资金分配（前端「资金总览卡」直接用）:
   {"total_assets","invested_weight","invested_amount","cash_weight","cash_amount","cash_floor",
    "allocations": [
      {"industry","go_nogo","current_weight","target_weight","current_amount","target_amount","delta_amount","action"}
    ]}
   金额 = round(total_assets × weight / 100)；total_assets 取自 data_portfolio.json，缺失则金额置 0 由下游补算。`,
    { label: 'Portfolio Synthesizer', phase: '风控合成' }
  );
  log('Portfolio Synthesizer 完成');
  return { status: 'done', violations: 0 };
}

const RUNNERS = { macro: runMacro, industry: runIndustry, scout: runScout, portfolio: runPortfolio, pm: runPm, synth: runSynth };

// ── 编排：决定每段跑/跳 ──────────────────────────────────────
const fromIdx = fromStage ? STAGES.indexOf(fromStage) : 0;
let forceDownstream = false;
const summary = [];
let lastResult = null;

for (const stage of STAGES) {
  const idx = STAGES.indexOf(stage);

  // 作用域过滤
  if (onlyStage && stage !== onlyStage) continue;
  if (!onlyStage && fromStage && idx < fromIdx) continue;

  let run = false, reason = '';
  if (full) { run = true; reason = 'full'; }
  else if (onlyStage === stage) { run = true; reason = 'only'; }
  else if (fromStage && idx >= fromIdx) { run = true; reason = 'from'; }
  else if (refreshMatches(stage)) { run = true; reason = 'refresh'; }
  else if (forceDownstream) { run = true; reason = 'upstream-changed'; }
  else {
    const cfg = CACHE[stage];
    const fresh = await gateFresh(stage, cfg.out, cfg.inputs, cfg.ttl);
    if (fresh) { log(`[skip] ${stage} 缓存命中`); summary.push(`${stage}:skip`); continue; }
    run = true; reason = 'stale';
  }

  if (!run) continue;
  log(`[run] ${stage} (${reason})`);

  // refresh 单行业：删掉该行业的研究产物，迫使重研究
  if (stage === 'industry' && refresh && String(refresh).startsWith('industry:')) {
    const target = String(refresh).slice('industry:'.length);
    const sn = safeName(target);
    await gateInvalidate(`researcher_${sn}.json`, true);
    await Bash(`rm -f ${p(`contrarian_${sn}.json`)}`);
    log(`已失效行业 ${target} 的研究产物`);
  }

  lastResult = await RUNNERS[stage]();

  // 违规打回：synth 报违规则中止，不盖戳
  if (lastResult && lastResult.status === 'violations_found') {
    log(`[abort] ${stage} 报告违规，中止编排`);
    return { status: 'violations_found', stage, violations: lastResult.violations, data_dir: dataDir };
  }

  // 盖戳（pm/synth ttl=0 也盖，便于审计）
  const cfg = CACHE[stage];
  await gateStamp(stage, cfg.out, cfg.inputs, cfg.ttl);
  summary.push(`${stage}:run(${reason})`);
  forceDownstream = true;

  if (onlyStage) break;
}

log(`编排完成: ${summary.join(' ')}`);
return { status: 'done', stages: summary, data_dir: dataDir, user_id: userId };
