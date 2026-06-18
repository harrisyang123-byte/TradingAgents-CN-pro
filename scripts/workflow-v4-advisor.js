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
//       存储/锁/指纹/写信封统一走 scripts/v4_unit_cli.py（由 agent 自行执行 Bash）。
//       注意：workflow 脚本沙箱不暴露 Bash，所有文件 I/O 必须嵌入 agent prompt。

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

// ── 内联文件 I/O 指令（嵌入 agent prompt） ──────────────────
function mkWriteInstr(filePath, jsonVar) {
  return `\n\n【文件写入指令】请用 Write 工具将以上完整 JSON 写入 "${p(filePath)}"（先确保目录存在: Bash: mkdir -p ${dataDir}）。`;
}

function mkLockInstr(unitId) {
  return `\n\n【前置操作】先执行 Bash: python3 scripts/v4_unit_cli.py lock '${unitId}' 2>&1，如果输出不含 LOCKED_OK 则报错退出。`;
}

function mkUnlockInstr(unitId) {
  return `\n\n【后置操作】完成分析后执行 Bash: python3 scripts/v4_unit_cli.py unlock '${unitId}' 2>&1。`;
}

function mkEnvelopeInstr(unitId, payloadFile, upstreamRefs, inputs, status) {
  const upStr = upstreamRefs.length ? `--upstream '${upstreamRefs.join(',')}'` : '';
  const inStr = inputs.map((f) => `'${f}'`).join(' ');
  return `\n\n【信封落盘】执行以下 Bash 命令序列：
1. fp=$(python3 scripts/v4_unit_cli.py fingerprint ${inStr} 2>&1 | tail -1)
2. python3 scripts/v4_unit_cli.py write '${unitId}' --payload ${payloadFile} --fingerprint "$fp" --run-mode ${RUN_MODE} --status ${status} ${upStr} 2>&1
确保输出包含 ENVELOPE_OK。`;
}

// 七大类固定枚举
const CLASS_KEYS = ['equity', 'fixed_income', 'cash', 'commodity', 'precious_metal', 'real_estate', 'alternative'];

// ── 部门：行业研究（industry:<name>，FR-006 AC6.2） ──────────
async function runIndustryDepartment(name) {
  const unitId = `industry:${name}`;
  const sn = safeName(name);
  phase('行业研究部门');
  log(`运行行业研究部门：${unitId}（chokepoint→future-market→辩论→总监）`);

  const packName = `inputs/industry_${sn}.json`;
  const inputs = [p(packName), p('inputs/data_macro.json'), p('allocation/portfolio.json')];
  const upstreamRefs = ['alloc:portfolio', 'asset:equity'];
  const chFile = `industry_chokepoint_${sn}.json`;
  const fmFile = `industry_future_market_${sn}.json`;
  const dbFile = `industry_debate_${sn}.json`;

  try {
    // ── Step A: Chokepoint 产业链瓶颈拆解 ──
    log(`[${sn}] Step A: 产业链瓶颈拆解`);
    const chokepoint = await agent(
      mkLockInstr(unitId) +
      `\n你是产业链瓶颈分析师(chokepoint analyst)。Read ${p(packName)}、${p('inputs/data_macro.json')}。\n` +
      `对行业「${name}」做自下而上逆向工程拆解：终端需求→系统级→部件级→关键器件→材料/设备级。\n` +
      `每个环节用四维判定(不可替代性/供给集中度/产能刚性/价值卡位) + 波特五力 + 替代路径 + 市场发现度(🔴已拥挤/🟡半发现/🟢未发现)。\n` +
      `输出 JSON：{role:"chokepoint",industry:"${name}",reverse_engineering_path:"拆解链描述",` +
      `chokepoint_map:[{layer,node,irreplaceability,supply_concentration,capacity_rigidity,value_capture,` +
      `substitution_risk,discovery_level,five_forces:{entry_threat,substitute_threat,buyer_power,supplier_power,internal_rivalry,moat_verdict},` +
      `beneficiaries_a:[],beneficiaries_qdii:[],is_top:bool}],` +
      `top_chokepoints:["四维最强的1-3个环节及理由"],evidence:[{claim,source,status}]}。${GROUNDING}` +
      mkWriteInstr(chFile, 'chokepoint'),
      { label: '瓶颈分析师', phase: '行业研究部门' }
    );

    // ── Step B: Future-Market 7把辩证尺消化 ──
    log(`[${sn}] Step B: 未来市场7把尺分析`);
    const futureMarket = await agent(
      `你是行业未来市场专职分析师(future-market-analyst)。Read ${p(packName)}、${p('inputs/data_macro.json')}、${p(chFile)}。\n` +
      `对行业「${name}」用7把辩证分析尺消化数据，产出独立的行业未来市场全景：\n` +
      `① TAM三角验证(≥3独立来源,差异>30%标分歧) ② TAM拆解还原(因子反推) ③ CAGR久期(历史可比) ` +
      `④ 渗透率阶段类比 ⑤ forward PEG跨期对比 ⑥ 龙头瓜分检验 ⑦ 景气先行指标交叉(≥3同向才确认)。\n` +
      `输出 JSON：{role:"future_market",industry:"${name}",tam_now_usd_b,tam_2030E_usd_b,cagr_pct,` +
      `penetration_stage,industry_forward_peg,leaders_share_distribution,key_drivers_5yr:[],` +
      `methodology_applied:[{ruler,result,data_ref}],data_sources:[{url,status}],evidence:[{claim,source,status}]}。${GROUNDING}` +
      mkWriteInstr(fmFile, 'futureMarket'),
      { label: '未来市场分析师', phase: '行业研究部门' }
    );

    // ── Step C: Bull/Bear 3轮辩论 ──
    log(`[${sn}] Step C: 多空辩论`);
    const chokeSummary = JSON.stringify(chokepoint).slice(0, 3000);
    const futureSummary = JSON.stringify(futureMarket).slice(0, 2000);
    const preContext = `\n\n【前置分析产出——产业链瓶颈结构】\n${chokeSummary}\n\n【前置分析产出——未来市场7把尺结论】\n${futureSummary}\n`;

    const rounds = [];
    let lastBear = null;
    for (let r = 1; r <= DEBATE_ROUNDS; r++) {
      const bullPrompt =
        `你是行业多头研究员。Read ${p(packName)}、${p('inputs/data_macro.json')}、${p('allocation/portfolio.json')}。` +
        `同时消化以下前置分析结论（产业链瓶颈+未来市场），辩论时引用这些结论而非原始数字：${preContext}` +
        (r > 1 ? `这是第 ${r} 轮，先回应上一轮空头挑战再强化：${JSON.stringify(lastBear).slice(0, 1200)}。` : `这是第 1 轮，给出看多核心论点。`) +
        `论证行业「${name}」景气向上、瓶颈环节投资价值、渗透率空间。必须引用前置分析的具体结论。` +
        `输出 JSON：{role:"bull",industry:"${name}",round:${r},thesis,bull_points:[{point,evidence_ref,confidence}],vitality_view,catalysts:[],suggested_stance,evidence:[{claim,source,status}],methodology_used:[]}。${GROUNDING}`;
      const bull = await agent(bullPrompt, { label: `行业多头 R${r}`, phase: '行业研究部门' });

      const bearPrompt =
        `你是行业空头研究员。先 Read 多头本轮论点：${JSON.stringify(bull).slice(0, 1600)}。再 Read ${p(packName)}、${p('inputs/data_macro.json')}。` +
        `同时消化前置分析结论：${preContext}` +
        `逐条挑战多头，可质疑前置分析的假设(如TAM拆解的因子是否合理、瓶颈是否真那么刚性、替代路径是否被低估)。` +
        `输出 JSON：{role:"bear",industry:"${name}",round:${r},challenge,bear_points:[{point,evidence_ref,confidence}],vitality_view,key_risks:[],suggested_stance,evidence:[{claim,source,status}],methodology_used:[]}。${GROUNDING}`;
      const bear = await agent(bearPrompt, { label: `行业空头 R${r}`, phase: '行业研究部门' });

      lastBear = bear;
      rounds.push({ round: r, bull, bear });
    }

    // 落盘辩论记录（由代理 agent 写入）
    await agent(
      `请用 Write 工具将以下内容写入 ${p(dbFile)}（先 Bash: mkdir -p ${dataDir}）：
${JSON.stringify({ industry: name, rounds }, null, 2)}`,
      { label: `写辩论文件`, phase: '行业研究部门' }
    );

    // ── Step D: Director 整合拍板（含锁释放 + 信封落盘） ──
    log(`[${sn}] Step D: 总监整合拍板`);
    const payloadFile = p('_payload_tmp.json');
    const director = await agent(
      `你是行业研究部门总监。Read ${p(dbFile)}、${p(chFile)}、` +
      `${p(fmFile)}、${p(packName)}、${p('allocation/portfolio.json')}。\n` +
      `综合：① 产业链瓶颈地图 ② 未来市场7把尺结论 ③ ${DEBATE_ROUNDS}轮多空辩论。\n` +
      `拍板「${name}」的方向研判。输出必含 chokepoint_map + industry_future_market + investment_map。\n` +
      `输出 JSON：{industry:"${name}",verdict:{stance,situation,direction,vitality_level,` +
      `track_quality,worst_case,cycle_position,downgrade_trigger,` +
      `chokepoint_conclusion,risks:[],allocation_advice,confidence},` +
      `chokepoint_map:[],top_chokepoints:[],industry_future_market:{},` +
      `investment_map:[{chokepoint_node,beneficiary,code,reason,discovery_level,position_priority}],` +
      `forward_view:{near_term_calendar:[],mid_term_path,path_scenarios:[]},` +
      `data_quality,evidence:[]}。${GROUNDING}` +
      `\n\n【最终落盘】用 Write 工具将上述完整 JSON 写入 ${payloadFile}（先 Bash: mkdir -p ${dataDir}）。` +
      mkEnvelopeInstr(unitId, payloadFile, upstreamRefs, inputs, 'green') +
      mkUnlockInstr(unitId),
      { label: '行业总监', phase: '行业研究部门' }
    );

    log(`✅ ${unitId} 完成：stance=${(director.verdict || {}).stance || '?'}`);
    return { status: 'done', unit_id: unitId };
  } catch (e) {
    log(`[ERROR] ${unitId} 失败: ${e}`);
    const errPf = p('_payload_tmp.json');
    await agent(
      `【错误恢复】请将错误信封写入单元 ${unitId}。\n` +
      `Bash: mkdir -p ${dataDir}\n` +
      `Write 工具写 ${errPf}: ${JSON.stringify({ industry: name, error: String(e) })}\n` +
      mkEnvelopeInstr(unitId, errPf, upstreamRefs, inputs, 'red') +
      mkUnlockInstr(unitId),
      { label: '错误恢复', phase: '行业研究部门' }
    );
    throw e;
  }
}

// ── 主调度 ──────────────────────────────────────────────────
async function main() {
  const sel = parseSelector(selector);
  log(`v4 编排器：verb=${verb} selector=${selector} type=${sel.type} run_mode=${RUN_MODE}`);

  switch (sel.type) {
    case 'industry':
      return runIndustryDepartment(sel.key);
    default:
      throw new Error(`selector type "${sel.type}" 暂未适配 agent-embedded I/O 模式，请先跑 industry`);
  }
}

await main();
