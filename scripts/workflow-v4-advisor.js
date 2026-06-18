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
//       存储/锁/指纹/写信封统一走 scripts/v4_unit_cli.py（由 persist agent 执行）。
//
// ⚠️ Workflow 沙箱无 Bash 全局 — 所有文件 I/O 必须通过 agent() 内部的 Bash/Write 工具执行。
//    中间数据在 JS 变量中流转，分析 agent 间通过 prompt 注入传递，不写临时文件。

export const meta = {
  name: 'v4-advisor',
  description: 'v4 单元化分层投研编排器 — 大类研究/配置委员会/行业深辩/个股，按单元独立调度',
  phases: [
    { title: '准备' },
    { title: '大类研究部门' },
    { title: '资产配置委员会' },
    { title: '行业研究部门' },
    { title: '行业配置团队' },
    { title: '行业内研究部门' },
    { title: '落盘' },
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

// ── I/O Agent：落盘（lock → write payload → cli write → unlock） ──
// 合并所有 shell 操作为单个 agent，避免多个轻量 agent stall（Issue #3 根因）
async function persistUnit(unitId, payloadObj, opts = {}) {
  const { upstreamRefs = [], inputs = [], status = 'green', error = '' } = opts;
  const payloadJson = JSON.stringify(payloadObj, null, 2);
  const upArg = upstreamRefs.length ? `--upstream '${upstreamRefs.join(',')}'` : '';
  const errArg = error ? `--error '${error.replace(/'/g, '')}'` : '';
  const fpCmd = inputs.length
    ? `FP=$(python3 scripts/v4_unit_cli.py fingerprint ${inputs.map(f => `'${f}'`).join(' ')} 2>&1) && echo "FP=$FP"`
    : 'FP=""';

  const result = await agent(
    `你是 I/O 执行器。按顺序用 Bash 工具执行以下命令，每步检查结果。

步骤 1 — 创建目录 + 获锁：
\`\`\`bash
mkdir -p ${dataDir}
python3 scripts/v4_unit_cli.py lock '${unitId}'
\`\`\`
如果输出不含 LOCKED_OK，直接返回 JSON：{"error":"lock_failed","detail":"<输出内容>"}

步骤 2 — 写 payload 文件（用 Write 工具写入 ${p('_payload_tmp.json')}）：
文件内容为以下 JSON（原样写入，不要修改）：
${payloadJson}

步骤 3 — 计算指纹：
\`\`\`bash
${fpCmd}
\`\`\`

步骤 4 — 写信封：
\`\`\`bash
python3 scripts/v4_unit_cli.py write '${unitId}' --payload ${p('_payload_tmp.json')} --fingerprint "$FP" --run-mode ${RUN_MODE} --status ${status} ${upArg} ${errArg}
\`\`\`

步骤 5 — 释放锁：
\`\`\`bash
python3 scripts/v4_unit_cli.py unlock '${unitId}'
\`\`\`

最终返回步骤 4 的 stdout JSON。如果步骤 2-4 任何一步失败，先执行步骤 5 释放锁，再返回 {"error":"<失败原因>"}。`,
    { label: `persist:${unitId}`, phase: '落盘' }
  );
  return result;
}

// ── I/O Agent：批量读取上下文 ────────────────────────────────
// 单个 agent 读多个文件/运行多个命令，返回结构化结果
async function ioRead(commands, label) {
  const result = await agent(
    `你是 I/O 读取器。按顺序执行以下读取操作，将每个结果存入对应的 key，最终返回一个 JSON 对象。

${commands.map((c, i) => `操作 ${i + 1} (key="${c.key}")：
${c.type === 'bash' ? `用 Bash 执行：\`${c.cmd}\`` : `用 Read 工具读取：${c.path}`}
${c.extract ? `从输出中提取：${c.extract}` : ''}
如果失败或文件不存在，该 key 值为 null。`).join('\n\n')}

返回 JSON 对象，每个 key 对应其结果值（字符串或解析后的值）。`,
    { label: label || 'io:read', phase: '准备' }
  );
  return result || {};
}

// 七大类固定枚举
const CLASS_KEYS = ['equity', 'fixed_income', 'cash', 'commodity', 'precious_metal', 'real_estate', 'alternative'];

// ── 部门：大类研究（asset:<class> 与 plan:<class> 共用 3 轮辩论 + 总监） ──
async function runAssetDepartment(klass, planMode) {
  const unitId = (planMode ? 'plan:' : 'asset:') + klass;
  phase('大类研究部门');
  log(`运行大类研究部门：${unitId}（3 轮辩论 + 总监拍板）`);

  const packName = planMode ? `inputs/plan_${klass}.json` : `inputs/asset_${klass}.json`;
  const inputs = [p(packName), p('inputs/data_macro.json')];

  // 读取归类桶（tradable/holding_only 信息）
  const setupCtx = await ioRead([
    { key: 'bucket', type: 'bash',
      cmd: `python3 -c "import json;d=json.load(open('${p('inputs/portfolio_classified.json')}'));print(json.dumps(d.get('by_class',{}).get('${klass}',{}),ensure_ascii=False))" 2>/dev/null || echo '{}'` },
  ], `setup:${unitId}`);
  const bucket = (function() {
    try { return JSON.parse(setupCtx.bucket || '{}'); } catch(e) { return {}; }
  })();

  // 三位专项分析师（各跑一次）
  const macroA = await agent(
    `你是大类宏观视角分析师。Read ${p(packName)} 和 ${p('inputs/data_macro.json')}。` +
    `从利率/通胀/周期/流动性判断 ${klass}（${packName} 里的 label）大类的宏观环境。` +
    `输出 JSON：{role:"macro",asset_class:"${klass}",macro_regime,rate_sensitivity,inflation_view,cycle_position,macro_tilt,reasoning,evidence}。${GROUNDING}`,
    { label: '宏观分析师', phase: '大类研究部门' }
  );

  const flowA = await agent(
    `你是大类资金/舆情视角分析师。Read ${p(packName)}、${p('inputs/data_macro.json')}、${p('inputs/portfolio_classified.json')}。` +
    `从资金流向/拥挤度/情绪/组合内敞口判断 ${klass} 大类。` +
    `输出 JSON：{role:"flow",asset_class:"${klass}",flow_direction,crowding,sentiment,flow_tilt,reasoning,evidence}。${GROUNDING}`,
    { label: '资金分析师', phase: '大类研究部门' }
  );

  const policyA = await agent(
    `你是大类政策/地缘视角分析师。Read ${p(packName)} 和 ${p('inputs/data_macro.json')}。` +
    `从货币/财政/产业/监管政策与地缘判断 ${klass} 大类。监管高风险类必须显式标注合规风险。` +
    `输出 JSON：{role:"policy",asset_class:"${klass}",policy_stance,geopolitical_impact,policy_tilt,reasoning,evidence}。${GROUNDING}`,
    { label: '政策分析师', phase: '大类研究部门' }
  );

  // 3 轮多空辩论（数据在 JS 变量中流转，不写中间文件）
  const rounds = [];
  let lastBear = null;
  for (let r = 1; r <= DEBATE_ROUNDS; r++) {
    const bullPrompt =
      `你是大类多头研究员。Read ${p(packName)}、${p('inputs/data_macro.json')}、${p('inputs/portfolio_classified.json')}。` +
      (r > 1 ? `这是第 ${r} 轮，先回应上一轮空头的挑战（见下），再强化看多论点。上轮空头：${JSON.stringify(lastBear).slice(0, 1200)}。` : `这是第 1 轮，给出看多核心论点。`) +
      `论证 ${klass} 大类当前是否值得增配/持有。若输入包 zero_holding=true 仍要分析是否值得择机建仓。` +
      `输出 JSON：{role:"bull",round:${r},asset_class:"${klass}",thesis,bull_points,catalysts,suggested_tilt,evidence}。${GROUNDING}`;
    const bull = await agent(bullPrompt, { label: `多头 R${r}`, phase: '大类研究部门' });

    const bearPrompt =
      `你是大类空头研究员。以下是多头本轮论点（无需 Read 文件）：
${JSON.stringify(bull).slice(0, 2000)}

另外 Read ${p(packName)}、${p('inputs/data_macro.json')}。` +
      `逐条挑战多头，论证 ${klass} 的风险与减配/回避理由。无数据支撑的挑战不计入。` +
      `输出 JSON：{role:"bear",round:${r},asset_class:"${klass}",challenge,bear_points,key_risks,suggested_tilt,evidence}。${GROUNDING}`;
    const bear = await agent(bearPrompt, { label: `空头 R${r}`, phase: '大类研究部门' });

    lastBear = bear;
    rounds.push({ round: r, bull, bear });
  }

  // 总监拍板（所有分析师结果 + 辩论结果通过 prompt 注入，不依赖中间文件）
  const directorPrompt =
    `你是大类研究部门总监。以下是三位专项分析师的研判（JSON）：

【宏观分析师】：${JSON.stringify(macroA)}
【资金分析师】：${JSON.stringify(flowA)}
【政策分析师】：${JSON.stringify(policyA)}

以下是 3 轮多空辩论记录：
${JSON.stringify(rounds).slice(0, 8000)}

另外 Read ${p(packName)} 获取输入包上下文。
综合 3 轮多空辩论与三位专项分析师意见，不机械平均，拍板 ${klass} 大类的形势/方向/风险/趋势。` +
    `输出 JSON：{asset_class:"${klass}",verdict:{stance,situation,direction,risks,trend,confidence},data_quality,evidence` +
    (planMode
      ? `,plan:{...}}（plan 按大类本质：cash→holding_structure；fixed_income→duration_view+instrument_mix；commodity/precious_metal→instrument_mix+risk_flags；real_estate→instrument_mix(REITs下钻/实物记敞口)+holding_only_note；alternative→instrument_mix+risk_flags；suggest_pct 为类内结构占比之和≈100）`
      : `}`) +
    `。${GROUNDING}`;
  const director = await agent(directorPrompt, { label: '大类总监', phase: '大类研究部门' });

  // 组装 payload（FR-009 同构 schema）
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

  // 落盘
  const writeResult = await persistUnit(unitId, payload, { inputs, status: 'green' });
  log(`✅ ${unitId} 完成：stance=${(payload.verdict || {}).stance || '?'}`);
  return { status: 'done', unit_id: unitId, write: writeResult };
}

// ── 部门：资产配置委员会（alloc:portfolio，FR-003） ──────────
async function runAllocationPortfolio() {
  const unitId = 'alloc:portfolio';
  phase('资产配置委员会');
  log('运行资产配置委员会：综合七大类 verdict 产出配比 + equity_quota');

  const upstreamRefs = CLASS_KEYS.map((k) => `asset:${k}`);
  const inputs = [p('inputs/portfolio_classified.json'),
    ...CLASS_KEYS.map((k) => p(`assets/${k}.json`))];

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

  const writeResult = await persistUnit(unitId, payload, { upstreamRefs, inputs, status: 'green' });
  log(`✅ alloc:portfolio 完成：equity_quota=${equityQuota}% Σ=${sum.toFixed(1)}`);
  if (equityQuota === 0) log('权益 target=0%，本期不触发权益深链（前端标「本期不配置权益」）');
  return { status: 'done', unit_id: unitId, equity_quota: equityQuota, write: writeResult };
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

  // 3 轮多空辩论（数据在 JS 变量中流转）
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
      `你是行业空头研究员。以下是多头本轮论点（无需 Read 文件）：
${JSON.stringify(bull).slice(0, 2000)}

另外 Read ${p(packName)}、${p('inputs/data_macro.json')}。` +
      `逐条挑战，论证「${name}」的景气拐点/估值/配置风险。无数据支撑的挑战不计入。` +
      `输出 JSON：{role:"bear",industry:"${name}",round:${r},challenge,bear_points,vitality_view,key_risks,suggested_stance,evidence}。${GROUNDING}`,
      { label: `行业空头 R${r}`, phase: '行业研究部门' }
    );
    lastBear = bear;
    rounds.push({ round: r, bull, bear });
  }

  // 总监拍板（辩论结果通过 prompt 注入）
  const director = await agent(
    `你是行业研究部门总监。以下是 ${DEBATE_ROUNDS} 轮多空辩论记录：
${JSON.stringify(rounds).slice(0, 8000)}

另外 Read ${p(packName)}、${p('allocation/portfolio.json')} 获取上下文。
综合辩论拍板「${name}」的方向研判（景气/空间/风险/配置建议 go|watch|avoid）。**此步先于行业间配比**。` +
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
  const writeResult = await persistUnit(unitId, payload, { upstreamRefs, inputs, status: 'green' });
  log(`✅ ${unitId} 完成：stance=${(payload.verdict || {}).stance || '?'} advice=${(payload.verdict || {}).allocation_advice || '?'}`);
  return { status: 'done', unit_id: unitId, write: writeResult };
}

// ── 部门：行业间配比（alloc:equity_industries，FR-006 AC6.3） ──
async function runEquityIndustriesAllocation() {
  const unitId = 'alloc:equity_industries';
  phase('行业配置团队');
  log('运行行业配置总监：在 equity_quota 内对各行业 verdict 做行业间配比');

  // 读取 equity_quota + 已有行业单元列表
  const setupCtx = await ioRead([
    { key: 'equity_quota', type: 'bash',
      cmd: `python3 -c "import json;d=json.load(open('${p('allocation/portfolio.json')}'));print(d.get('payload',{}).get('equity_quota',''))" 2>/dev/null || echo ''` },
    { key: 'industry_files', type: 'bash',
      cmd: `ls ${dataDir}/industries/*.json 2>/dev/null | grep -v '.tmp' || echo ''` },
  ], `setup:${unitId}`);

  const equityQuota = parseFloat(setupCtx.equity_quota);
  if (!Number.isFinite(equityQuota) || equityQuota === 0) {
    log('equity_quota=0% 或不可用，本期不配置权益，跳过行业间配比');
    throw new Error('equity_quota=0 或不可用，本期不触发权益深链');
  }
  const industryFiles = (setupCtx.industry_files || '').split('\n').filter(Boolean);
  if (!industryFiles.length) {
    throw new Error('尚无任何行业深辩单元；请先 analyze industry:<name>（深辩先于配比）');
  }

  const upstreamRefs = ['alloc:portfolio',
    ...industryFiles.map((f) => 'industry:' + f.split('/').pop().replace(/\.json$/, ''))];
  const inputs = [p('allocation/portfolio.json'), ...industryFiles];

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
  const writeResult = await persistUnit(unitId, payload, { upstreamRefs, inputs, status: 'green' });
  log(`✅ ${unitId} 完成：Σ=${sumW.toFixed(1)}% ≤ quota ${equityQuota}%`);
  return { status: 'done', unit_id: unitId, write: writeResult };
}

// ── 部门：个股分析（stock:<code>，每只独立单元独立缓存，FR-006 AC6.4） ──
async function runStockDepartment(code) {
  const unitId = `stock:${code}`;
  const sn = safeName(code);
  phase('行业内研究部门');
  log(`运行行业内研究部门：${unitId}（个股独立分析）`);

  const packName = `inputs/stock_${sn}.json`;

  // 读取个股所属行业
  const setupCtx = await ioRead([
    { key: 'industry', type: 'bash',
      cmd: `python3 -c "import json;d=json.load(open('${p(`inputs/stock_${sn}.json`)}'));print(d.get('industry',''))" 2>/dev/null || echo ''` },
  ], `setup:${unitId}`);

  const industry = (setupCtx.industry || '').trim();
  const indSafe = safeName(industry);
  const industryFile = industry ? p(`industries/${indSafe}.json`) : '';
  const inputs = [p(packName)];
  if (industryFile) inputs.push(industryFile);
  const upstreamRefs = industry ? [`industry:${industry}`] : [];

  const bull = await agent(
    `你是个股多头研究员。Read ${p(packName)}${industryFile ? '、' + industryFile : ''}。` +
    `论证个股 ${code} 的投资价值与上行空间（不逆所属行业大方向）。` +
    `输出 JSON：{role:"bull",code:"${code}",name,thesis,bull_points,upside_target,evidence}。${GROUNDING}`,
    { label: '个股多头', phase: '行业内研究部门' }
  );
  const bear = await agent(
    `你是个股空头研究员。以下是多头论点（无需 Read 文件）：
${JSON.stringify(bull).slice(0, 2000)}

另外 Read ${p(packName)}${industryFile ? '、' + industryFile : ''}。` +
    `逐条挑战，揭示 ${code} 的风险与下行。无数据支撑不计入。` +
    `输出 JSON：{role:"bear",code:"${code}",name,challenge,bear_points,downside_risk,evidence}。${GROUNDING}`,
    { label: '个股空头', phase: '行业内研究部门' }
  );

  // 总监拍板（多空结果 prompt 注入）
  const director = await agent(
    `你是行业内研究总监（任务 A 个股评级）。以下是多空辩论结果：
【多头】：${JSON.stringify(bull).slice(0, 2000)}
【空头】：${JSON.stringify(bear).slice(0, 2000)}

另外 Read ${p(packName)}${industryFile ? '、' + industryFile : ''}。
综合多空拍板 ${code} 的评级/目标价/买入区间。` +
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
  const writeResult = await persistUnit(unitId, payload, { upstreamRefs, inputs, status: 'green' });
  log(`✅ ${unitId} 完成：rating=${payload.rating || '?'} tp=${payload.target_price ?? '?'}`);
  return { status: 'done', unit_id: unitId, write: writeResult };
}

// ── 部门：行业内资金配比（alloc:industry:<name>，FR-006 AC6.5） ──
async function runIntraIndustryAllocation(name) {
  const unitId = `alloc:industry:${name}`;
  const sn = safeName(name);
  phase('行业内研究部门');
  log(`运行行业内资金配比：${unitId}`);

  // 读取该行业内已落盘的个股单元列表
  const setupCtx = await ioRead([
    { key: 'stock_files', type: 'bash',
      cmd: `for f in ${dataDir}/stocks/*.json; do [ -f "$f" ] || continue; python3 -c "import json,sys;d=json.load(open('$f'));sys.stdout.write('$f\\n') if d.get('payload',{}).get('industry')=='${name}' else None" 2>/dev/null; done || echo ''` },
  ], `setup:${unitId}`);

  const stockFiles = (setupCtx.stock_files || '').split('\n').filter(Boolean);
  if (!stockFiles.length) {
    throw new Error(`行业「${name}」尚无个股分析单元；请先 analyze stock:<code>`);
  }
  const upstreamRefs = ['alloc:equity_industries',
    ...stockFiles.map((f) => 'stock:' + f.split('/').pop().replace(/\.json$/, ''))];
  const inputs = [p('allocation/equity_industries.json'), ...stockFiles];

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
  const writeResult = await persistUnit(unitId, payload, { upstreamRefs, inputs, status: 'green' });
  log(`✅ ${unitId} 完成：Σ=${sumW.toFixed(1)}%`);
  return { status: 'done', unit_id: unitId, write: writeResult };
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
