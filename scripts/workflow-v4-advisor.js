// Workflow: v4 分层独立深度投研编排器 — 单元化调度 + 部门子流程
// 取代 v3「线性 7 stage」：按 unit-selector 只跑命中单元（AC4.4），各单元独立落盘/状态/缓存。
//
// 用法: claude -p "运行 v4 编排器，Workflow 脚本 scripts/workflow-v4-advisor.js，
//                  args 传 {verb:'analyze', selector:'asset:equity', user_id:'...'}"
// args:
//   verb       analyze | refresh
//   selector   单元选择器：asset:<class> | plan:<class> | alloc:portfolio |
//              industry:<name> | alloc:equity_industries | stock:<code> | alloc:industry:<name>
//   user_id    用户 ID
//   portfolio_file  AI 代跑文件输入（可选）
//   full       忽略缓存（可选）
//
// 铁律：所有 LLM 决策走子 Agent（agent()），Python 不直接调 LLM；
//       存储/锁/指纹/写信封统一走 scripts/v4_unit_cli.py（保持本编排器轻薄）。

export const meta = {
  name: 'v4-advisor',
  description: 'v4 单元化分层投研编排器 — 大类研究/配置委员会/行业深辩/个股，按单元独立调度',
  phases: [
    { title: '大类研究部门' },
    { title: '资产配置委员会' },
    { title: '权益深链' },
  ],
};

// ── 参数 ────────────────────────────────────────────────────
const verb = args.verb || 'analyze';
const selector = args.selector;
const userId = args.user_id || args.userId || '6a094caea814b57d3357fa0b';
const portfolioFile = args.portfolio_file || args.portfolioFile || '';
const dataDir = args.data_dir || 'data/v4';
const DEBATE_ROUNDS = 3; // AC2.2 固定 3 轮

if (!selector) {
  throw new Error('缺少 selector（如 asset:equity）');
}

// ── 统一数据接地契约（注入每个 agent 提示） ──────────────────
const GROUNDING = `

数据接地与凭据（强制）：
- 每个量化结论必须来自你真实 Read 到的数据；读不到就把字段置 null 并在 reasoning 注明「未读到 X」，严禁编造，也不得套用提示里的示例数字。
- 额外输出 evidence 数组：[{"claim":"关键数据点","source":"来源文件名 或 llm_knowledge","status":"verified|estimated|missing"}]。`;

const RUN_MODE = portfolioFile ? 'ai_proxy' : 'local';

// ── 工具：解析 selector ─────────────────────────────────────
function parseSelector(sel) {
  const [prefix, ...rest] = sel.split(':');
  const tail = rest.join(':');
  if (prefix === 'asset') return { type: 'asset', key: tail };
  if (prefix === 'plan') return { type: 'plan', key: tail };
  if (prefix === 'industry') return { type: 'industry', key: tail };
  if (prefix === 'stock') return { type: 'stock', key: tail };
  if (prefix === 'alloc') {
    if (tail.startsWith('industry:')) return { type: 'alloc_industry', key: tail.slice('industry:'.length) };
    return { type: 'alloc', key: tail };
  }
  throw new Error(`未知 selector 前缀: ${sel}`);
}

function p(name) { return `${dataDir}/${name}`; }

function safeName(s) {
  return String(s).replace(/[\/\\:\*\?"<>\|（）()\s]+/g, '_');
}

// 写 JSON 到文件（供下游 agent Read）
async function writeJson(name, obj) {
  await Bash(`mkdir -p ${dataDir} && cat > ${p(name)} << 'ENDJSON'
${JSON.stringify(obj, null, 2)}
ENDJSON`);
}

// 调 v4_unit_cli.py
async function unitCli(argstr) {
  return String(await Bash(`python3 scripts/v4_unit_cli.py ${argstr} 2>&1`)).trim();
}

async function lockUnit(unitId) {
  const res = await unitCli(`lock '${unitId}'`);
  if (!res.includes('LOCKED_OK')) {
    throw new Error(`单元 ${unitId} 获锁失败（可能正在运行）: ${res}`);
  }
}

async function unlockUnit(unitId) {
  await unitCli(`unlock '${unitId}'`);
}

// 写单元信封：payload 先落临时文件，再交给 cli
async function writeEnvelope(unitId, payload, { upstreamRefs = [], inputs = [], status = 'green', error = '' } = {}) {
  await writeJson('_payload_tmp.json', payload);
  let fp = '';
  if (inputs.length) {
    fp = await unitCli(`fingerprint ${inputs.map((f) => `'${f}'`).join(' ')}`);
  }
  const upArg = upstreamRefs.length ? `--upstream '${upstreamRefs.join(',')}'` : '';
  const errArg = error ? `--error '${error.replace(/'/g, '')}'` : '';
  const out = await unitCli(
    `write '${unitId}' --payload ${p('_payload_tmp.json')} --fingerprint '${fp}' ` +
    `--run-mode ${RUN_MODE} --status ${status} ${upArg} ${errArg}`
  );
  log(`[unit] 落盘 ${unitId} → ${out}`);
  return out;
}

// ── 部门：大类研究（asset:<class> 与 plan:<class> 共用 3 轮辩论 + 总监） ──
async function runAssetDepartment(klass, planMode) {
  const unitId = (planMode ? 'plan:' : 'asset:') + klass;
  phase('大类研究部门');
  log(`运行大类研究部门：${unitId}（3 轮辩论 + 总监拍板）`);

  const packName = planMode ? `inputs/plan_${klass}.json` : `inputs/asset_${klass}.json`;
  const inputs = [p(packName), p('inputs/data_macro.json')];

  await lockUnit(unitId);
  try {
    // 三位专项分析师（各跑一次）
    const macroA = await agent(
      `你是大类宏观视角分析师。Read ${p(packName)} 和 ${p('inputs/data_macro.json')}。` +
      `从利率/通胀/周期/流动性判断 ${klass}（${packName} 里的 label）大类的宏观环境。` +
      `输出 JSON：{role:"macro",asset_class,macro_regime,rate_sensitivity,inflation_view,cycle_position,macro_tilt,reasoning,evidence}。${GROUNDING}`,
      { label: '宏观分析师', phase: '大类研究部门' }
    );
    await writeJson(`asset_analyst_macro_${safeName(klass)}.json`, macroA);

    const flowA = await agent(
      `你是大类资金/舆情视角分析师。Read ${p(packName)}、${p('inputs/data_macro.json')}、${p('inputs/portfolio_classified.json')}。` +
      `从资金流向/拥挤度/情绪/组合内敞口判断 ${klass} 大类。` +
      `输出 JSON：{role:"flow",asset_class,flow_direction,crowding,sentiment,flow_tilt,reasoning,evidence}。${GROUNDING}`,
      { label: '资金分析师', phase: '大类研究部门' }
    );
    await writeJson(`asset_analyst_flow_${safeName(klass)}.json`, flowA);

    const policyA = await agent(
      `你是大类政策/地缘视角分析师。Read ${p(packName)} 和 ${p('inputs/data_macro.json')}。` +
      `从货币/财政/产业/监管政策与地缘判断 ${klass} 大类。监管高风险类必须显式标注合规风险。` +
      `输出 JSON：{role:"policy",asset_class,policy_stance,geopolitical_impact,policy_tilt,reasoning,evidence}。${GROUNDING}`,
      { label: '政策分析师', phase: '大类研究部门' }
    );
    await writeJson(`asset_analyst_policy_${safeName(klass)}.json`, policyA);

    // 3 轮多空辩论
    const rounds = [];
    let lastBear = null;
    for (let r = 1; r <= DEBATE_ROUNDS; r++) {
      const bullPrompt =
        `你是大类多头研究员。Read ${p(packName)}、${p('inputs/data_macro.json')}、${p('inputs/portfolio_classified.json')}。` +
        (r > 1 ? `这是第 ${r} 轮，先回应上一轮空头的挑战（见下），再强化看多论点。上轮空头：${JSON.stringify(lastBear).slice(0, 1200)}。` : `这是第 1 轮，给出看多核心论点。`) +
        `论证 ${klass} 大类当前是否值得增配/持有。若输入包 zero_holding=true 仍要分析是否值得择机建仓。` +
        `输出 JSON：{role:"bull",round:${r},asset_class,thesis,bull_points,catalysts,suggested_tilt,evidence}。${GROUNDING}`;
      const bull = await agent(bullPrompt, { label: `多头 R${r}`, phase: '大类研究部门' });

      const bearPrompt =
        `你是大类空头研究员。先 Read 多头本轮论点：${JSON.stringify(bull).slice(0, 1600)}。再 Read ${p(packName)}、${p('inputs/data_macro.json')}。` +
        `逐条挑战多头，论证 ${klass} 的风险与减配/回避理由。无数据支撑的挑战不计入。` +
        `输出 JSON：{role:"bear",round:${r},asset_class,challenge,bear_points,key_risks,suggested_tilt,evidence}。${GROUNDING}`;
      const bear = await agent(bearPrompt, { label: `空头 R${r}`, phase: '大类研究部门' });

      lastBear = bear;
      rounds.push({ round: r, bull, bear });
    }
    await writeJson(`asset_debate_${safeName(klass)}.json`, { asset_class: klass, rounds });

    // 总监拍板
    const directorPrompt =
      `你是大类研究部门总监。Read ${p(`asset_debate_${safeName(klass)}.json`)}、` +
      `${p(`asset_analyst_macro_${safeName(klass)}.json`)}、${p(`asset_analyst_flow_${safeName(klass)}.json`)}、` +
      `${p(`asset_analyst_policy_${safeName(klass)}.json`)}、${p(packName)}。` +
      `综合 3 轮多空辩论与三位专项分析师意见，不机械平均，拍板 ${klass} 大类的形势/方向/风险/趋势。` +
      `输出 JSON：{asset_class,verdict:{stance,situation,direction,risks,trend,confidence},data_quality,evidence` +
      (planMode
        ? `,plan:{...}}（plan 按大类本质：cash→holding_structure；fixed_income→duration_view+instrument_mix；commodity/precious_metal→instrument_mix+risk_flags；real_estate→instrument_mix(REITs下钻/实物记敞口)+holding_only_note；alternative→instrument_mix+risk_flags；suggest_pct 为类内结构占比之和≈100）`
        : `}`) +
      `。${GROUNDING}`;
    const director = await agent(directorPrompt, { label: '大类总监', phase: '大类研究部门' });

    // 组装 payload（FR-009 同构 schema）
    const bucket = await readClassBucket(klass);
    const payload = {
      asset_class: klass,
      label: director.label || (director.verdict && director.verdict.label) || klass,
      debate_rounds: rounds,
      analysts: { macro: macroA, flow: flowA, policy: policyA },
      verdict: director.verdict || director,
      data_quality: director.data_quality || null,
      tradable: bucket.tradable || [],
      holding_only_exposure: bucket.holding_only_exposure || 0,
      current_weight: bucket.weight || 0,
      evidence: director.evidence || [],
    };
    if (planMode && director.plan) payload.plan = director.plan;

    await writeEnvelope(unitId, payload, { inputs, status: 'green' });
    log(`✅ ${unitId} 完成：stance=${(payload.verdict || {}).stance || '?'}`);
    return { status: 'done', unit_id: unitId };
  } catch (e) {
    log(`[ERROR] ${unitId} 失败: ${e}`);
    await writeEnvelope(unitId, { asset_class: klass, error: String(e) }, { inputs, status: 'red', error: String(e) });
    throw e;
  } finally {
    await unlockUnit(unitId);
  }
}

// 读取归类桶（供 payload 补充 tradable/敞口）
async function readClassBucket(klass) {
  try {
    const raw = await Bash(
      `python3 -c "import json;d=json.load(open('${p('inputs/portfolio_classified.json')}'));print(json.dumps(d.get('by_class',{}).get('${klass}',{}),ensure_ascii=False))" 2>/dev/null || echo '{}'`
    );
    return JSON.parse(String(raw).trim() || '{}');
  } catch (e) {
    return {};
  }
}

// 七大类固定枚举
const CLASS_KEYS = ['equity', 'fixed_income', 'cash', 'commodity', 'precious_metal', 'real_estate', 'alternative'];

// ── 部门：资产配置委员会（alloc:portfolio，FR-003） ──────────
async function runAllocationPortfolio() {
  const unitId = 'alloc:portfolio';
  phase('资产配置委员会');
  log('运行资产配置委员会：综合七大类 verdict 产出配比 + equity_quota');

  // 上游 = 7 个 asset:* 单元（记录其 version+fingerprint，AC3.5）
  const upstreamRefs = CLASS_KEYS.map((k) => `asset:${k}`);
  const inputs = [p('inputs/portfolio_classified.json'),
    ...CLASS_KEYS.map((k) => p(`assets/${k}.json`))];

  await lockUnit(unitId);
  try {
    const director = await agent(
      `你是资产配置委员会总监。Read ${p('inputs/portfolio_classified.json')} 与七个大类 verdict（存在则读）：` +
      CLASS_KEYS.map((k) => p(`assets/${k}.json`)).join('、') + '。' +
      `综合七类研判产出资产配比：每类 current→target + action + reasoning，校验 Σtarget=100（含主动归零类）。` +
      `允许 target_weight=0 但必须 actively_zeroed=true + 归零理由。缺失/过时类记 input_warnings 并按现状 hold。` +
      `设 equity_quota = 权益 target_weight。` +
      `输出 JSON：{assets:[{asset_class,current_weight,target_weight,action,actively_zeroed,reasoning}],equity_quota,sum_check,input_warnings,summary,evidence}。${GROUNDING}`,
      { label: '配置委员会总监', phase: '资产配置委员会' }
    );

    // 兜底校验 Σ=100（仅提醒，不强改）
    const assets = Array.isArray(director.assets) ? director.assets : [];
    const sum = assets.reduce((acc, a) => acc + (Number(a.target_weight) || 0), 0);
    const equityQuota = director.equity_quota != null
      ? director.equity_quota
      : ((assets.find((a) => a.asset_class === 'equity') || {}).target_weight ?? 0);

    const payload = {
      assets,
      equity_quota: equityQuota,
      sum_check: Math.round(sum),
      input_warnings: director.input_warnings || [],
      summary: director.summary || '',
      evidence: director.evidence || [],
    };
    if (Math.abs(sum - 100) > 0.5) {
      payload.input_warnings.push({ asset_class: '*', issue: 'sum_check', detail: `Σtarget=${sum.toFixed(1)}≠100，请复核` });
    }

    await writeEnvelope(unitId, payload, { upstreamRefs, inputs, status: 'green' });
    log(`✅ alloc:portfolio 完成：equity_quota=${equityQuota}% Σ=${sum.toFixed(1)}`);
    if (equityQuota === 0) log('权益 target=0%，本期不触发权益深链（前端标「本期不配置权益」）');
    return { status: 'done', unit_id: unitId, equity_quota: equityQuota };
  } catch (e) {
    log(`[ERROR] ${unitId} 失败: ${e}`);
    await writeEnvelope(unitId, { error: String(e) }, { upstreamRefs, inputs, status: 'red', error: String(e) });
    throw e;
  } finally {
    await unlockUnit(unitId);
  }
}

// ── 工具：读 equity_quota（来自 alloc:portfolio） ─────────────
async function readEquityQuota() {
  try {
    const raw = await Bash(
      `python3 -c "import json;d=json.load(open('${p('allocation/portfolio.json')}'));print(d.get('payload',{}).get('equity_quota',''))" 2>/dev/null || echo ''`
    );
    const v = parseFloat(String(raw).trim());
    return Number.isFinite(v) ? v : null;
  } catch (e) {
    return null;
  }
}

// 列出已落盘的行业深辩单元（供行业配置总监读取）
async function listIndustryUnits() {
  try {
    const raw = await Bash(
      `ls ${dataDir}/industries/*.json 2>/dev/null | grep -v '.tmp' || true`
    );
    return String(raw).trim().split('\n').filter(Boolean);
  } catch (e) {
    return [];
  }
}

// ── 部门：行业研究（industry:<name>，3 轮辩论 + 总监，FR-006 AC6.2） ──
async function runIndustryDepartment(name) {
  const unitId = `industry:${name}`;
  const sn = safeName(name);
  phase('行业研究部门');
  log(`运行行业研究部门：${unitId}（3 轮辩论 + 总监定方向，早于配比）`);

  const packName = `inputs/industry_${sn}.json`;
  const inputs = [p(packName), p('inputs/data_macro.json'), p('allocation/portfolio.json')];
  const upstreamRefs = ['alloc:portfolio', 'asset:equity'];

  await lockUnit(unitId);
  try {
    const rounds = [];
    let lastBear = null;
    for (let r = 1; r <= DEBATE_ROUNDS; r++) {
      const bull = await agent(
        `你是行业多头研究员。Read ${p(packName)}、${p('inputs/data_macro.json')}、${p('allocation/portfolio.json')}。` +
        (r > 1 ? `这是第 ${r} 轮，先回应上一轮空头挑战再强化：${JSON.stringify(lastBear).slice(0, 1200)}。` : `这是第 1 轮，给出看多核心论点。`) +
        `论证行业「${name}」是否景气向上、值得在 equity_quota 内配置。` +
        `输出 JSON：{role:"bull",industry:"${name}",round:${r},thesis,bull_points,vitality_view,catalysts,suggested_stance,evidence}。${GROUNDING}`,
        { label: `行业多头 R${r}`, phase: '行业研究部门' }
      );
      const bear = await agent(
        `你是行业空头研究员。先 Read 多头本轮论点：${JSON.stringify(bull).slice(0, 1600)}。再 Read ${p(packName)}、${p('inputs/data_macro.json')}。` +
        `逐条挑战，论证「${name}」的景气拐点/估值/配置风险。无数据支撑的挑战不计入。` +
        `输出 JSON：{role:"bear",industry:"${name}",round:${r},challenge,bear_points,vitality_view,key_risks,suggested_stance,evidence}。${GROUNDING}`,
        { label: `行业空头 R${r}`, phase: '行业研究部门' }
      );
      lastBear = bear;
      rounds.push({ round: r, bull, bear });
    }
    await writeJson(`industry_debate_${sn}.json`, { industry: name, rounds });

    const director = await agent(
      `你是行业研究部门总监。Read ${p(`industry_debate_${sn}.json`)}、${p(packName)}、${p('allocation/portfolio.json')}。` +
      `综合 ${DEBATE_ROUNDS} 轮多空辩论，拍板「${name}」的方向研判（景气/空间/风险/配置建议 go|watch|avoid）。**此步先于行业间配比**。` +
      `输出 JSON：{industry:"${name}",verdict:{stance,situation,direction,vitality_level,risks,allocation_advice,confidence},data_quality,evidence}。${GROUNDING}`,
      { label: '行业总监', phase: '行业研究部门' }
    );

    const payload = {
      industry: name,
      debate_rounds: rounds,
      verdict: director.verdict || director,
      data_quality: director.data_quality || null,
      evidence: director.evidence || [],
    };
    await writeEnvelope(unitId, payload, { upstreamRefs, inputs, status: 'green' });
    log(`✅ ${unitId} 完成：stance=${(payload.verdict || {}).stance || '?'} advice=${(payload.verdict || {}).allocation_advice || '?'}`);
    return { status: 'done', unit_id: unitId };
  } catch (e) {
    log(`[ERROR] ${unitId} 失败: ${e}`);
    await writeEnvelope(unitId, { industry: name, error: String(e) }, { upstreamRefs, inputs, status: 'red', error: String(e) });
    throw e;
  } finally {
    await unlockUnit(unitId);
  }
}

// ── 部门：行业间配比（alloc:equity_industries，FR-006 AC6.3） ──
async function runEquityIndustriesAllocation() {
  const unitId = 'alloc:equity_industries';
  phase('行业配置团队');
  log('运行行业配置总监：在 equity_quota 内对各行业 verdict 做行业间配比');

  const equityQuota = await readEquityQuota();
  if (equityQuota === 0) {
    log('equity_quota=0%，本期不配置权益，跳过行业间配比');
    throw new Error('equity_quota=0，本期不触发权益深链');
  }
  const industryFiles = await listIndustryUnits();
  if (!industryFiles.length) {
    throw new Error('尚无任何行业深辩单元；请先 analyze industry:<name>（深辩先于配比）');
  }

  const upstreamRefs = ['alloc:portfolio',
    ...industryFiles.map((f) => 'industry:' + f.split('/').pop().replace(/\.json$/, ''))];
  const inputs = [p('allocation/portfolio.json'), ...industryFiles];

  await lockUnit(unitId);
  try {
    const director = await agent(
      `你是行业配置总监。Read ${p('allocation/portfolio.json')}（取 payload.equity_quota=${equityQuota}）` +
      `与已就绪的行业深辩单元：${industryFiles.join('、')}（每份 payload.verdict 含 stance/vitality_level/allocation_advice）。` +
      `基于各行业 verdict 在 equity_quota 内产出行业间配比，校验 Σtarget_weight ≤ equity_quota。只读 verdict 不重研判行业。` +
      `输出 JSON：{equity_quota:${equityQuota},allocations:[{industry,target_weight,reasoning}],sum_weight,cash_buffer_in_equity,input_warnings,summary,evidence}。${GROUNDING}`,
      { label: '行业配置总监', phase: '行业配置团队' }
    );

    const allocations = Array.isArray(director.allocations) ? director.allocations : [];
    const sumW = allocations.reduce((acc, a) => acc + (Number(a.target_weight) || 0), 0);
    const payload = {
      equity_quota: equityQuota,
      allocations,
      sum_weight: Math.round(sumW * 10) / 10,
      cash_buffer_in_equity: director.cash_buffer_in_equity ?? (equityQuota != null ? Math.round((equityQuota - sumW) * 10) / 10 : null),
      input_warnings: director.input_warnings || [],
      summary: director.summary || '',
      evidence: director.evidence || [],
    };
    if (equityQuota != null && sumW > equityQuota + 0.5) {
      payload.input_warnings.push({ industry: '*', issue: 'over_quota', detail: `Σ行业权重=${sumW.toFixed(1)}% > equity_quota=${equityQuota}%，请复核` });
    }
    await writeEnvelope(unitId, payload, { upstreamRefs, inputs, status: 'green' });
    log(`✅ ${unitId} 完成：Σ=${sumW.toFixed(1)}% ≤ quota ${equityQuota}%`);
    return { status: 'done', unit_id: unitId };
  } catch (e) {
    log(`[ERROR] ${unitId} 失败: ${e}`);
    await writeEnvelope(unitId, { error: String(e) }, { upstreamRefs, inputs, status: 'red', error: String(e) });
    throw e;
  } finally {
    await unlockUnit(unitId);
  }
}

// 读个股输入包里的所属行业
async function readStockIndustry(code) {
  const sn = safeName(code);
  try {
    const raw = await Bash(
      `python3 -c "import json;d=json.load(open('${p(`inputs/stock_${sn}.json`)}'));print(d.get('industry',''))" 2>/dev/null || echo ''`
    );
    return String(raw).trim();
  } catch (e) {
    return '';
  }
}

// ── 部门：个股分析（stock:<code>，每只独立单元独立缓存，FR-006 AC6.4） ──
async function runStockDepartment(code) {
  const unitId = `stock:${code}`;
  const sn = safeName(code);
  phase('行业内研究部门');
  log(`运行行业内研究部门：${unitId}（个股独立分析）`);

  const packName = `inputs/stock_${sn}.json`;
  const industry = await readStockIndustry(code);
  const indSafe = safeName(industry);
  const industryFile = industry ? p(`industries/${indSafe}.json`) : '';
  const inputs = [p(packName)];
  if (industryFile) inputs.push(industryFile);
  const upstreamRefs = industry ? [`industry:${industry}`] : [];

  await lockUnit(unitId);
  try {
    const bull = await agent(
      `你是个股多头研究员。Read ${p(packName)}${industryFile ? '、' + industryFile : ''}。` +
      `论证个股 ${code} 的投资价值与上行空间（不逆所属行业大方向）。` +
      `输出 JSON：{role:"bull",code:"${code}",name,thesis,bull_points,upside_target,evidence}。${GROUNDING}`,
      { label: '个股多头', phase: '行业内研究部门' }
    );
    const bear = await agent(
      `你是个股空头研究员。先 Read 多头论点：${JSON.stringify(bull).slice(0, 1400)}。再 Read ${p(packName)}${industryFile ? '、' + industryFile : ''}。` +
      `逐条挑战，揭示 ${code} 的风险与下行。无数据支撑不计入。` +
      `输出 JSON：{role:"bear",code:"${code}",name,challenge,bear_points,downside_risk,evidence}。${GROUNDING}`,
      { label: '个股空头', phase: '行业内研究部门' }
    );
    await writeJson(`stock_debate_${sn}.json`, { code, rounds: [{ round: 1, bull, bear }] });

    const director = await agent(
      `你是行业内研究总监（任务 A 个股评级）。Read ${p(`stock_debate_${sn}.json`)}、${p(packName)}${industryFile ? '、' + industryFile : ''}。` +
      `综合多空拍板 ${code} 的评级/目标价/买入区间。` +
      `输出 JSON：{code:"${code}",name,industry:"${industry}",rating,target_price,entry_price_range,thesis,risks,confidence,evidence}。${GROUNDING}`,
      { label: '行业内总监', phase: '行业内研究部门' }
    );

    const payload = {
      code,
      name: director.name || bull.name || code,
      industry,
      rating: director.rating || null,
      target_price: director.target_price ?? null,
      entry_price_range: director.entry_price_range || null,
      thesis: director.thesis || '',
      risks: director.risks || [],
      debate_rounds: [{ round: 1, bull, bear }],
      confidence: director.confidence || null,
      evidence: director.evidence || [],
    };
    await writeEnvelope(unitId, payload, { upstreamRefs, inputs, status: 'green' });
    log(`✅ ${unitId} 完成：rating=${payload.rating || '?'} tp=${payload.target_price ?? '?'}`);
    return { status: 'done', unit_id: unitId };
  } catch (e) {
    log(`[ERROR] ${unitId} 失败: ${e}`);
    await writeEnvelope(unitId, { code, error: String(e) }, { upstreamRefs, inputs, status: 'red', error: String(e) });
    throw e;
  } finally {
    await unlockUnit(unitId);
  }
}

// 列出某行业内已落盘的个股单元
async function listStockUnitsForIndustry(name) {
  try {
    const raw = await Bash(
      `for f in ${dataDir}/stocks/*.json; do [ -f "$f" ] || continue; python3 -c "import json,sys;d=json.load(open('$f'));print('$f') if d.get('payload',{}).get('industry')=='''${name}''' else None" 2>/dev/null; done || true`
    );
    return String(raw).trim().split('\n').filter(Boolean);
  } catch (e) {
    return [];
  }
}

// ── 部门：行业内资金配比（alloc:industry:<name>，FR-006 AC6.5） ──
async function runIntraIndustryAllocation(name) {
  const unitId = `alloc:industry:${name}`;
  const sn = safeName(name);
  phase('行业内研究部门');
  log(`运行行业内资金配比：${unitId}`);

  const stockFiles = await listStockUnitsForIndustry(name);
  if (!stockFiles.length) {
    throw new Error(`行业「${name}」尚无个股分析单元；请先 analyze stock:<code>`);
  }
  const upstreamRefs = ['alloc:equity_industries',
    ...stockFiles.map((f) => 'stock:' + f.split('/').pop().replace(/\.json$/, ''))];
  const inputs = [p('allocation/equity_industries.json'), ...stockFiles];

  await lockUnit(unitId);
  try {
    const director = await agent(
      `你是行业内研究总监（任务 B 行业内配比）。Read ${p('allocation/equity_industries.json')}（取「${name}」的 target_weight 为上限）` +
      `与本行业个股单元：${stockFiles.join('、')}（读各自 rating/target_price/entry_price_range）。` +
      `在行业目标权重内对个股做配比，校验 Σstock_weight ≤ 行业 target_weight。高评级/高确定性多配，避免单股过度集中。` +
      `输出 JSON：{industry:"${name}",industry_target_weight,stock_weights:[{code,target_weight,entry_price_range,reasoning}],sum_weight,input_warnings,evidence}。${GROUNDING}`,
      { label: '行业内配比总监', phase: '行业内研究部门' }
    );
    const stockWeights = Array.isArray(director.stock_weights) ? director.stock_weights : [];
    const sumW = stockWeights.reduce((acc, s) => acc + (Number(s.target_weight) || 0), 0);
    const payload = {
      industry: name,
      industry_target_weight: director.industry_target_weight ?? null,
      stock_weights: stockWeights,
      sum_weight: Math.round(sumW * 10) / 10,
      input_warnings: director.input_warnings || [],
      evidence: director.evidence || [],
    };
    const cap = director.industry_target_weight;
    if (cap != null && sumW > cap + 0.5) {
      payload.input_warnings.push({ code: '*', issue: 'over_weight', detail: `Σ个股权重=${sumW.toFixed(1)}% > 行业上限=${cap}%，请复核` });
    }
    await writeEnvelope(unitId, payload, { upstreamRefs, inputs, status: 'green' });
    log(`✅ ${unitId} 完成：Σ=${sumW.toFixed(1)}%`);
    return { status: 'done', unit_id: unitId };
  } catch (e) {
    log(`[ERROR] ${unitId} 失败: ${e}`);
    await writeEnvelope(unitId, { industry: name, error: String(e) }, { upstreamRefs, inputs, status: 'red', error: String(e) });
    throw e;
  } finally {
    await unlockUnit(unitId);
  }
}

// ── 主调度 ──────────────────────────────────────────────────
async function main() {
  const sel = parseSelector(selector);
  log(`v4 编排器：verb=${verb} selector=${selector} type=${sel.type} run_mode=${RUN_MODE}`);

  switch (sel.type) {
    case 'asset':
      return runAssetDepartment(sel.key, false);
    case 'plan':
      return runAssetDepartment(sel.key, true);
    case 'alloc':
      if (sel.key === 'portfolio') return runAllocationPortfolio();
      if (sel.key === 'equity_industries') return runEquityIndustriesAllocation();
      throw new Error(`未知 alloc 单元: alloc:${sel.key}`);
    case 'alloc_industry':
      return runIntraIndustryAllocation(sel.key);
    case 'industry':
      return runIndustryDepartment(sel.key);
    case 'stock':
      return runStockDepartment(sel.key);
    default:
      throw new Error(`未知单元类型: ${sel.type}`);
  }
}

await main();
