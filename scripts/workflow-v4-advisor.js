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
// 瓶颈递归深挖：AI 自评估收敛（触底/供需松/已price-in 即停），层数不写死；
// MAX_DRILL_DEPTH 纯为防跑飞的硬上限，非业务限制（不同行业实际深度由 AI 判定）。
const MAX_DRILL_DEPTH = Number(args.max_drill_depth || 6);
const DRILL_TOP_N = Number(args.drill_top_n || 2); // 对骨架里 top 几个瓶颈做上溯深挖

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

// Issue #5 修复：agent() 不带 schema 时返回的是 markdown 字符串(含 ```json 块)，不是 object。
// 此前 runCriticGate/drillChokepoint 直接 critique?.score 取到 undefined→0(critic 实评 42 分被吞)。
// 统一用此函数从 agent 返回值提取结构化 JSON：已是 object 直接用；字符串则按优先级容错解析。
function parseAgentJSON(ret) {
  if (ret == null) return {};
  if (typeof ret === 'object') return ret;           // 万一 harness 已解析
  const s = String(ret);
  // 1) ```json ... ``` 代码块(critic/分析师标准输出格式)
  let m = s.match(/```json\s*([\s\S]*?)```/i);
  if (m) { try { return JSON.parse(m[1].trim()); } catch (e) { /* 落到下一策略 */ } }
  // 2) 任意 ``` ... ``` 代码块
  m = s.match(/```\s*([\s\S]*?)```/);
  if (m) { try { return JSON.parse(m[1].trim()); } catch (e) { /* next */ } }
  // 3) 第一个 { 到最后一个 } 的片段(无围栏直接吐 JSON)
  const i = s.indexOf('{'), j = s.lastIndexOf('}');
  if (i !== -1 && j > i) { try { return JSON.parse(s.slice(i, j + 1)); } catch (e) { /* next */ } }
  // 4) 整串就是 JSON
  try { return JSON.parse(s); } catch (e) { /* 全失败 */ }
  log(`[WARN] parseAgentJSON 解析失败，返回空对象（原文前120字: ${s.slice(0, 120)}）`);
  return {};
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

// ── 瓶颈递归深挖（上溯式：每层 AI 自评估是否继续，不写死层数） ──────────
// 思路（用户拍板）：价格=供需。某环节是瓶颈 → 它上游用什么 → 那层供不应求吗 →
// 供需最紧 + 市场未发现的那一环，才是还没被 price-in 的超额收益所在。
// 收敛条件（任一满足即停）：① 触底(材料/矿源，无更上游) ② 供需已松(不再瓶颈)
// ③ 已被市场充分 price-in(alpha 没了)。MAX_DRILL_DEPTH 仅防跑飞。
async function drillChokepoint(industry, startNode, packPath) {
  const chain = []; // 上溯链：[{depth, node, ...}]
  let current = startNode; // 起点瓶颈环节（一句话描述）
  for (let depth = 1; depth <= MAX_DRILL_DEPTH; depth++) {
    const prevChain = chain.length
      ? `\n已上溯路径：${chain.map((c) => `L${c.depth} ${c.node}`).join(' → ')}\n`
      : '';
    const node = parseAgentJSON(await agent(
      `你是产业链「上溯调研员」(upstream supply-chain driller)。Read ${packPath}。\n` +
      `行业「${industry}」。当前聚焦环节：【${current}】。${prevChain}\n` +
      `第一性原理：市场价格 = 供需关系。瓶颈环节供不应求 → 涨价 → 利润上来 → 股市有故事。\n` +
      `你的任务——只往上游钻一层：回答「制造/实现【${current}】，还必须依赖什么更上游的关键投入(材料/部件/设备/特种工艺/矿源)？」\n` +
      `挑出其中供需最紧张的那一个上游环节，评估它：\n` +
      `- supply_demand_gap：当前供需缺口(紧缺/平衡/过剩 + 一句话证据，如"全球仅2家供,在建产能2027才投产")\n` +
      `- expansion_cycle：扩产/认证周期(决定缺口能否快速缓解)\n` +
      `- global_players：全球玩家数 + CR1/CR3 集中度\n` +
      `- pricing_power：是否具备涨价能力(BOM占比可能小但断供整线停=议价强)\n` +
      `- discovery_level：🔴已拥挤/🟡半发现/🟢未发现(市场是否已认识到这个上游瓶颈)\n` +
      `- beneficiaries_a / beneficiaries_qdii：受益标的(只列名/代码，数字不编)\n` +
      `然后自评估是否继续上溯，给出 should_continue(bool) + stop_reason：\n` +
      `  停(should_continue=false) 当：① 已触底(纯大宗材料/矿源，无更上游卡点) ② 该上游供需已松(不再是瓶颈) ③ 已被市场充分 price-in(无 alpha)。\n` +
      `  继续(true) 当：钻出的上游仍紧缺且未被充分发现，值得再往上一层。\n` +
      `输出 JSON：{depth:${depth},node:"上游环节名",needs_what:"${current}依赖它的原因",` +
      `supply_demand_gap,expansion_cycle,global_players,pricing_power,discovery_level,` +
      `beneficiaries_a:[],beneficiaries_qdii:[],should_continue:bool,stop_reason:"",` +
      `evidence:[{claim,source,status}]}。${GROUNDING}`,
      { label: `上溯钻 L${depth}:${String(current).slice(0, 10)}`, phase: '行业研究部门' }
    ));
    chain.push(node);
    if (!node || node.should_continue === false) break;
    if (!node.node) break; // 没钻出新环节，停
    current = node.node; // 下一层聚焦点 = 本层钻出的上游
  }
  return { start: startNode, depth_reached: chain.length, chain };
}

// ── critic 评审闸门 + director 迭代闭环（真 spawn v4-investor-critic，禁自评） ──────────
// AGENTS.md 铁律：GATE 必须真 spawn critic 禁自评。<85 分或有 fatal_flaw → 打回 director
// 修订（最多 CRITIC_MAX_ITERS 轮），ACCEPT 后把 critic 结论写进 credibility 再落盘。
const CRITIC_MAX_ITERS = Number(args.critic_max_iters || 2);
const CRITIC_PASS_SCORE = Number(args.critic_pass_score || 85);

async function runCriticGate({ unitId, payloadFile, directorSchema, kind, readRefs, upstreamRefs, inputs }) {
  let lastVerdict = null;
  let critique = null;
  for (let iter = 1; iter <= CRITIC_MAX_ITERS + 1; iter++) {
    // 评审当前 payload（首轮评 director 初稿，后续评修订稿）
    log(`[${unitId}] Step E: critic 评审（第 ${iter} 轮，真 spawn 评委）`);
    critique = parseAgentJSON(await agent(
      `你是 v4 专业投资者评审官(v4-investor-critic)，由芒格/段永平/Serenity/达里奥四视角组成评审委员会。\n` +
      `⚠️ 必须读取并应用 agents/advisor/v4-investor-critic.md 的四视角拷问框架 + 评审铁律（${kind === 'industry' ? '行业层重点查 6.11 未来市场必查 + 6.11.x 7把辩证尺 + 瓶颈不可替代性/预期差' : '6.12-6.16 个股必查项'}）。\n` +
      `Read 待评审产出 ${payloadFile}，及上游依据 ${readRefs}。\n` +
      `严苛拷问这份 ${kind} 分析，宁苛勿松：数据是否 verified（编造/未核实关键数字一票否决）、瓶颈不可替代性是否成立、是否用预期差而非涨幅锚、最坏情况是否诚实、辩论是否真攻防。\n` +
      `输出 JSON：{verdict_reviewed:"${unitId}",munger:{pass:bool,critique},duan:{pass:bool,critique},serenity:{pass:bool,critique},dalio:{pass:bool,critique},fatal_flaws:[],improvements:["具体可执行,指出哪里/为什么/怎么改"],score:0-100,decision:"ACCEPT|NEEDS_CHANGES"}。只输出 JSON。`,
      { label: `评审委员会 R${iter}`, phase: '行业研究部门' }
    ));
    const score = Number(critique?.score || 0);
    const decision = String(critique?.decision || 'NEEDS_CHANGES');
    const fatal = Array.isArray(critique?.fatal_flaws) ? critique.fatal_flaws : [];
    const passed = decision === 'ACCEPT' && score >= CRITIC_PASS_SCORE && fatal.length === 0;
    log(`[${unitId}]   critic: ${decision} ${score}分, fatal=${fatal.length}`);

    if (passed) {
      // 评审通过：critic 结论写进 credibility(final_verdict=ACCEPT) → cli 放行落盘 → 解锁
      lastVerdict = await agent(
        `Read ${payloadFile}（director 当前产出）。把评审委员会结论合并进 credibility 字段后整体写回 ${payloadFile}。\n` +
        `评审结论：score=${score}, decision=ACCEPT, fatal_flaws=${JSON.stringify(fatal).slice(0, 500)}。\n` +
        `在 payload 顶层加/更新：credibility={final_verdict:"ACCEPT",critic_score:${score},reviewer:"v4-investor-critic(独立评审)",reviewers:["芒格","段永平","Serenity","达里奥"],challenges:${JSON.stringify((critique?.improvements || []).slice(0, 5))},critic_iterations:${iter}}。\n` +
        `用 Write 写回 ${payloadFile} 后，落单元信封：` +
        mkEnvelopeInstr(unitId, payloadFile, upstreamRefs, inputs, 'green') +
        mkUnlockInstr(unitId),
        { label: '评审通过落盘', phase: '行业研究部门' }
      );
      // 落盘 agent 返回的是文本总结，verdict 真身在 payloadFile；这里只回传评审元信息供主流程 log
      return { _critic_score: score, _critic_decision: 'ACCEPT', verdict: parseAgentJSON(lastVerdict).verdict || {} };
    }

    if (iter === CRITIC_MAX_ITERS + 1) {
      // 到迭代上限仍未过线：诚实落「红」信封(error 说明评审未通过) + 必须解锁(防锁泄漏)。
      // 不写绿/黄信封——那会被 cli ACCEPT 闸门 exit=4 阻断、且 agent 见错可能跳过 unlock。
      // 用错误信封路径(status=red)如实记账，cli 写 error 信封不走 ACCEPT 校验，能成功落盘+解锁。
      log(`[${unitId}]   ⚠️ 迭代 ${CRITIC_MAX_ITERS} 轮仍未过线(${score}分)，落红信封如实记账`);
      const errSummary = `critic 未通过(score=${score}, decision=${decision}); fatal=${JSON.stringify(fatal).slice(0, 300)}`;
      await agent(
        `Read ${payloadFile}。把评审结论合并进 credibility 后写回 ${payloadFile}：` +
        `credibility={final_verdict:"NEEDS_CHANGES",critic_score:${score},reviewer:"v4-investor-critic(独立评审)",reviewers:["芒格","段永平","Serenity","达里奥"],challenges:${JSON.stringify((critique?.improvements || []).slice(0, 5))},critic_iterations:${iter},unresolved:true}。\n` +
        `这是诚实降级：行业分析经 ${CRITIC_MAX_ITERS} 轮修订仍未达专业水准，如实标红，不强行通过。\n` +
        `用 Write 写回 ${payloadFile} 后，落「红」信封（--status red 不走 ACCEPT 校验，能成功记账）：` +
        mkEnvelopeInstr(unitId, payloadFile, upstreamRefs, inputs, 'red') +
        `\n\n【必须解锁】无论上一步成败，最后务必执行 Bash: python3 scripts/v4_unit_cli.py unlock '${unitId}' 2>&1（防锁泄漏）。`,
        { label: '迭代上限·红信封落盘', phase: '行业研究部门' }
      );
      return { _critic_score: score, _critic_decision: 'NEEDS_CHANGES', verdict: {}, unresolved: true };
    }

    // 未通过 → 把 critic 反馈喂回 director 修订（重写 payloadFile，下一轮再评）
    log(`[${unitId}]   未过线，打回 director 修订（improvements ${(critique?.improvements || []).length} 条）`);
    lastVerdict = await agent(
      `你是行业研究部门总监。你上一版 ${kind} 分析被评审委员会判 NEEDS_CHANGES（${score}分）。\n` +
      `Read 你的上一版产出 ${payloadFile}，及依据 ${readRefs}。\n` +
      `评审委员会的硬伤与改进意见（必须逐条针对性修订，不许换个说法重复）：\n` +
      `fatal_flaws=${JSON.stringify(fatal)}\nimprovements=${JSON.stringify(critique?.improvements || [])}\n` +
      `针对每条意见实质修订你的 verdict/investment_map/forward_view 等，${directorSchema}。${GROUNDING}\n` +
      `用 Write 工具将修订后的完整 JSON 覆盖写回 ${payloadFile}（先 Bash: mkdir -p ${dataDir}），本步骤不落信封。`,
      { label: `总监修订 R${iter}`, phase: '行业研究部门' }
    );
  }
  return lastVerdict || {};
}

// ── 部门：行业研究（industry:<name>，FR-006 AC6.2） ──────────
async function runIndustryDepartment(name) {
  const unitId = `industry:${name}`;
  const sn = safeName(name);
  phase('行业研究部门');
  log(`运行行业研究部门：${unitId}（chokepoint→深挖→future-market→辩论→总监→critic评审闭环）`);

  const packName = `inputs/industry_${sn}.json`;
  const inputs = [p(packName), p('inputs/data_macro.json'), p('allocation/portfolio.json')];
  const upstreamRefs = ['alloc:portfolio', 'asset:equity'];
  const chFile = `industry_chokepoint_${sn}.json`;
  const fmFile = `industry_future_market_${sn}.json`;
  const dbFile = `industry_debate_${sn}.json`;
  const drillFile = `industry_drill_${sn}.json`;

  try {
    // ── Step A: Chokepoint 产业链瓶颈拆解 ──
    log(`[${sn}] Step A: 产业链瓶颈拆解`);
    const chokepoint = parseAgentJSON(await agent(
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
    ));

    // ── Step A2: 瓶颈递归深挖（粗评估出骨架 → 对 top 瓶颈逐层上溯，AI 自评估收敛） ──
    log(`[${sn}] Step A2: 瓶颈递归深挖（上溯式，AI 自评估层数）`);
    // 选 top 瓶颈作为深挖起点：优先 chokepoint_map 里 is_top，回退 top_chokepoints 文本
    const cmap = Array.isArray(chokepoint?.chokepoint_map) ? chokepoint.chokepoint_map : [];
    let drillStarts = cmap.filter((n) => n && n.is_top).map((n) => n.node).filter(Boolean);
    if (!drillStarts.length && Array.isArray(chokepoint?.top_chokepoints)) {
      drillStarts = chokepoint.top_chokepoints.map((t) => String(t).split(/[—（(]/)[0].trim()).filter(Boolean);
    }
    drillStarts = drillStarts.slice(0, DRILL_TOP_N);
    const drills = [];
    for (const startNode of drillStarts) {
      log(`[${sn}]   上溯深挖起点：${startNode}`);
      drills.push(await drillChokepoint(name, startNode, p(packName)));
    }
    // 落盘上溯链
    await agent(
      `请用 Write 工具将以下内容写入 ${p(drillFile)}（先 Bash: mkdir -p ${dataDir}）：
${JSON.stringify({ industry: name, drills }, null, 2)}`,
      { label: '写深挖文件', phase: '行业研究部门' }
    );

    // ── Step B: Future-Market 7把辩证尺消化 ──
    log(`[${sn}] Step B: 未来市场7把尺分析`);
    const futureMarket = parseAgentJSON(await agent(
      `你是行业未来市场专职分析师(future-market-analyst)。Read ${p(packName)}、${p('inputs/data_macro.json')}、${p(chFile)}。\n` +
      `★Issue#4：输入包 packName 内含 valuation_inputs(关联个股 verified PE 聚合 + 折现率锚 cn10y/lpr_5y + fetch_tasks)。第⑤尺 forward PEG 必须消费它：用 peer_pe_median/peer_pe_range 算行业 PE 中枢，用 cn10y 推合理折现率；若 valuation_inputs.available=false 则按 fetch_tasks 提示联网补，仍取不到才标 industry_forward_peg=null 并说明，不编造。\n` +
      `对行业「${name}」用7把辩证分析尺消化数据，产出独立的行业未来市场全景：\n` +
      `① TAM三角验证(≥3独立来源,差异>30%标分歧) ② TAM拆解还原(因子反推) ③ CAGR久期(历史可比) ` +
      `④ 渗透率阶段类比 ⑤ forward PEG跨期对比(消费 valuation_inputs，给出 industry_pe_anchor + leaders_forward_peg) ⑥ 龙头瓜分检验 ⑦ 景气先行指标交叉(≥3同向才确认)。\n` +
      `输出 JSON：{role:"future_market",industry:"${name}",tam_now_usd_b,tam_2030E_usd_b,cagr_pct,` +
      `penetration_stage,industry_forward_peg,leaders_share_distribution,key_drivers_5yr:[],` +
      `methodology_applied:[{ruler,result,data_ref}],data_sources:[{url,status}],evidence:[{claim,source,status}]}。${GROUNDING}` +
      mkWriteInstr(fmFile, 'futureMarket'),
      { label: '未来市场分析师', phase: '行业研究部门' }
    ));

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
      const bull = parseAgentJSON(await agent(bullPrompt, { label: `行业多头 R${r}`, phase: '行业研究部门' }));

      const bearPrompt =
        `你是行业空头研究员。先 Read 多头本轮论点：${JSON.stringify(bull).slice(0, 1600)}。再 Read ${p(packName)}、${p('inputs/data_macro.json')}。` +
        `同时消化前置分析结论：${preContext}` +
        `逐条挑战多头，可质疑前置分析的假设(如TAM拆解的因子是否合理、瓶颈是否真那么刚性、替代路径是否被低估)。` +
        `输出 JSON：{role:"bear",industry:"${name}",round:${r},challenge,bear_points:[{point,evidence_ref,confidence}],vitality_view,key_risks:[],suggested_stance,evidence:[{claim,source,status}],methodology_used:[]}。${GROUNDING}`;
      const bear = parseAgentJSON(await agent(bearPrompt, { label: `行业空头 R${r}`, phase: '行业研究部门' }));

      lastBear = bear;
      rounds.push({ round: r, bull, bear });
    }

    // 落盘辩论记录（由代理 agent 写入）
    await agent(
      `请用 Write 工具将以下内容写入 ${p(dbFile)}（先 Bash: mkdir -p ${dataDir}）：
${JSON.stringify({ industry: name, rounds }, null, 2)}`,
      { label: `写辩论文件`, phase: '行业研究部门' }
    );

    // ── Step D: Director 整合拍板（只产出 payload，不落盘——落盘留给 critic 通过后） ──
    log(`[${sn}] Step D: 总监整合拍板`);
    const payloadFile = p('_payload_tmp.json');
    const directorSchema =
      `输出 JSON：{industry:"${name}",verdict:{stance,situation,direction,vitality_level,` +
      `track_quality,worst_case,cycle_position,downgrade_trigger,` +
      `chokepoint_conclusion,risks:[],allocation_advice,confidence},` +
      `chokepoint_map:[],top_chokepoints:[],` +
      `deep_chokepoint_chains:[{start:"表层瓶颈",chain:[{depth,node,supply_demand_gap,expansion_cycle,global_players,pricing_power,discovery_level,beneficiaries_a:[],beneficiaries_qdii:[]}],deepest_alpha:"最深且未发现的那一环+理由"}],` +
      `industry_future_market:{},` +
      `investment_map:[{chokepoint_node,beneficiary,code,reason,discovery_level,position_priority,chain_depth}],` +
      `forward_view:{near_term_calendar:[],mid_term_path,path_scenarios:[]},` +
      `data_quality,evidence:[]}`;
    // director 初稿（产出写入 payloadFile，评审闭环在 Step E）
    await agent(
      `你是行业研究部门总监。Read ${p(dbFile)}、${p(chFile)}、` +
      `${p(fmFile)}、${p(drillFile)}、${p(packName)}、${p('allocation/portfolio.json')}。\n` +
      `综合：① 产业链瓶颈地图 ② 瓶颈递归深挖的上溯链(industry_drill：每个 top 瓶颈往上游钻出的更深紧缺环节) ③ 未来市场7把尺结论 ④ ${DEBATE_ROUNDS}轮多空辩论。\n` +
      `拍板「${name}」的方向研判。输出必含 chokepoint_map + deep_chokepoint_chains + industry_future_market + investment_map。\n` +
      `★特别要求：investment_map 不能只停在表层瓶颈(如"光模块制造")，必须把上溯链钻出的【更深、供需更紧、市场更未发现】的环节(如光模块→EML芯片→磷化铟衬底)也作为投资标的纳入，并标 discovery_level——这些深层环节才是还没被 price-in 的超额收益来源。\n` +
      directorSchema + `。${GROUNDING}` +
      `\n\n【产出落盘】用 Write 工具将上述完整 JSON 写入 ${payloadFile}（先 Bash: mkdir -p ${dataDir}）。本步骤先不写单元信封，等评审委员会通过后再落盘。`,
      { label: '行业总监', phase: '行业研究部门' }
    );

    // ── Step E: 独立 critic 评审闸门 + director 迭代闭环（真 spawn v4-investor-critic，禁自评） ──
    const verdict = await runCriticGate({
      unitId, payloadFile, directorSchema, kind: 'industry',
      readRefs: `${p(chFile)}、${p(fmFile)}、${p(drillFile)}、${p(dbFile)}、${p(packName)}`,
      upstreamRefs, inputs,
    });

    log(`✅ ${unitId} 完成：stance=${(verdict.verdict || {}).stance || '?'} | critic=${verdict._critic_score}/${verdict._critic_decision}`);
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
