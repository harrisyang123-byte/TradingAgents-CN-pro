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
      throw new Error(`alloc:${sel.key} 的编排在 Task 3 扩展（equity_industries）`);
    // industry / stock / alloc_industry 路径在 Task 3 扩展
    default:
      throw new Error(`单元类型 ${sel.type} 的编排尚未实现（将在后续阶段补全）`);
  }
}

await main();
