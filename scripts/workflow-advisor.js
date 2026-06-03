// Workflow: Claude Code 组合顾问引擎 — 9 Agent 4 层辩论编排
//
// 用法（通过 run.sh 调用）:
//   claude workflow run advisor --args '{"data_dir": "...", "user_id": "..."}'
//
// Agent 文件位于 agents/advisor/（通过 setup.sh 安装到 .claude/agents/advisor/）

export const meta = {
  name: 'advisor',
  description: '组合顾问引擎 — 9 Agent 4 层辩论 → 处方',
  phases: [
    { title: 'L1 行业方向' },
    { title: 'L2 标的筛选' },
    { title: 'L3 组合诊断' },
    { title: '交叉验证' },
    { title: 'L4 最终处方' },
  ],
};

const STEP_ORDER = [
  // L1 辩论 (辩论2轮: strategist → contrarian → strategist_r2 → judge)
  { name: 'l1-strategist', layer: 'L1', agentType: 'l1-strategist' },
  { name: 'l1-contrarian', layer: 'L1', agentType: 'l1-contrarian' },
  { name: 'l1-strategist-r2', layer: 'L1', agentType: 'l1-strategist' },
  { name: 'l1-judge', layer: 'L1', agentType: 'l1-judge' },
  // L2 标的筛选
  { name: 'l2-scout', layer: 'L2', agentType: 'l2-scout' },
  // L3 辩论 (辩论2轮: analyst → strategist → analyst_r2 → strategist_r2)
  { name: 'l3-analyst', layer: 'L3', agentType: 'l3-analyst' },
  { name: 'l3-strategist', layer: 'L3', agentType: 'l3-strategist' },
  { name: 'l3-analyst-r2', layer: 'L3', agentType: 'l3-analyst' },
  { name: 'l3-strategist-r2', layer: 'L3', agentType: 'l3-strategist' },
  // L4 处方
  { name: 'l4-cio', layer: 'L4', agentType: 'l4-cio' },
  { name: 'l4-risk', layer: 'L4', agentType: 'l4-risk' },
  { name: 'l4-cio-final', layer: 'L4', agentType: 'l4-cio-final' },
];

const STEP_TO_FILE = {
  'l1-strategist': 'step1_strategist.json',
  'l1-contrarian': 'step2_contrarian.json',
  'l1-strategist-r2': 'step1_strategist_r2.json',
  'l1-judge': 'step3_judge.json',
  'l2-scout': 'step4_scout.json',
  'l3-analyst': 'step5_analyst.json',
  'l3-strategist': 'step6_strategist.json',
  'l3-analyst-r2': 'step5_analyst_r2.json',
  'l3-strategist-r2': 'step6_strategist_r2.json',
  'l4-cio': 'step7_cio.json',
  'l4-risk': 'step8_risk.json',
  'l4-cio-final': 'step9_final.json',
};

function inputFiles(step, dataDir) {
  const base = [`${dataDir}/data_portfolio.json`];

  switch (step.name) {
    case 'l1-strategist':
      base.push(`${dataDir}/data_macro.json`, `${dataDir}/data_market_temp.json`);
      break;
    case 'l1-contrarian':
      base.push(`${dataDir}/data_macro.json`, `${dataDir}/step1_strategist.json`);
      break;
    case 'l1-strategist-r2':
      base.push(`${dataDir}/data_macro.json`, `${dataDir}/step1_strategist.json`,
                `${dataDir}/step2_contrarian.json`);
      break;
    case 'l1-judge':
      base.push(`${dataDir}/data_macro.json`, `${dataDir}/step1_strategist.json`,
                `${dataDir}/step2_contrarian.json`, `${dataDir}/step1_strategist_r2.json`);
      break;
    case 'l2-scout':
      base.push(`${dataDir}/step3_judge.json`, `${dataDir}/data_pe.json`,
                `${dataDir}/data_tier1.json`);
      break;
    case 'l3-analyst':
      base.push(`${dataDir}/step3_judge.json`, `${dataDir}/step4_scout.json`,
                `${dataDir}/data_tier1.json`, `${dataDir}/data_pe.json`);
      break;
    case 'l3-strategist':
      base.push(`${dataDir}/step5_analyst.json`, `${dataDir}/data_exposure.json`,
                `${dataDir}/step3_judge.json`);
      break;
    case 'l3-analyst-r2':
      base.push(`${dataDir}/step5_analyst.json`, `${dataDir}/step6_strategist.json`,
                `${dataDir}/data_tier1.json`, `${dataDir}/data_pe.json`,
                `${dataDir}/step3_judge.json`);
      break;
    case 'l3-strategist-r2':
      base.push(`${dataDir}/step5_analyst_r2.json`, `${dataDir}/data_exposure.json`,
                `${dataDir}/step3_judge.json`);
      break;
    case 'l4-cio':
      base.push(`${dataDir}/step3_judge.json`, `${dataDir}/step4_scout.json`,
                `${dataDir}/step5_analyst_r2.json`, `${dataDir}/step6_strategist_r2.json`,
                `${dataDir}/conflicts.json`, `${dataDir}/data_exposure.json`,
                `${dataDir}/data_market_temp.json`);
      break;
    case 'l4-risk':
      base.push(`${dataDir}/step7_cio.json`, `${dataDir}/conflicts.json`,
                `${dataDir}/data_exposure.json`);
      break;
    case 'l4-cio-final':
      base.push(`${dataDir}/step7_cio.json`, `${dataDir}/step8_risk.json`,
                `${dataDir}/conflicts.json`, `${dataDir}/data_exposure.json`,
                `${dataDir}/data_market_temp.json`);
      break;
  }
  return base;
}

function buildPrompt(step, dataDir, user_id) {
  const files = inputFiles(step, dataDir);
  const fileList = files.map(f => `- ${f}`).join('\n');
  const outputFile = `${dataDir}/${STEP_TO_FILE[step.name]}`;

  const debateContext = getDebateContext(step.name);

  return `## 任务
你是 ${step.agentType}。请严格按照你的 system prompt 中定义的角色身份和输出格式执行任务。

## 用户 ID
${user_id}

## 数据目录
${dataDir}

## 输入数据文件
请使用 Read 工具读取以下文件（按需读取，不要一次性全读）：
${fileList}

${debateContext}

## 输出
将你的分析结果以 JSON 格式写入文件: ${outputFile}

先用 Read 工具读取你需要的数据文件，然后推理，最后将 JSON 写入 ${outputFile}。

重要：确保你的输出符合你在 system prompt 中看到的 JSON 格式。`;
}

function getDebateContext(stepName) {
  if (stepName === 'l1-contrarian') {
    return `## 辩论上下文
你正在挑战 L1-策略师的行业判定。步骤：
1. 先 Read step1_strategist.json，逐条审视策略师的每个行业判定
2. 再 Read data_macro.json 验证策略师引用的数据
3. 对每条判定提出你的挑战（或确认"无重大异议"）`;
  }
  if (stepName === 'l1-strategist-r2') {
    return `## 辩论上下文（第 2 轮）
你是 L1-策略师。反向者已经挑战了你的第一轮判定（见 step2_contrarian.json）。

你的任务：
1. Read step1_strategist.json（你的第一轮判定）
2. Read step2_contrarian.json（反向者的挑战）
3. 对反向者的每一条严重挑战（severity=high）做出回应：
   - 接受：修正你的判定
   - 反驳：用数据证明你的原判定正确
   - 折中：调整置信度或方向

输出你修正后的行业判定（格式和第一轮相同）。`;
  }
  if (stepName === 'l1-judge') {
    return `## 裁定上下文
你是 L1-裁判。策略师和反向者已经完成了辩论。你的任务是做最终裁定。

1. Read step1_strategist.json + step1_strategist_r2.json（策略师的完整立场）
2. Read step2_contrarian.json（反向者的挑战）
3. Read data_macro.json（原始数据——这是你的判断基准）
4. 做出最终裁定，逐行业给出超配/标配/低配/零配方向

原则：数据优先。策略师和反向者有分歧时，以 data_macro.json 中的原始数据为准。`;
  }
  if (stepName === 'l3-strategist') {
    return `## 诊断上下文
你是 L3-组合策略师（诊断报告员）。分析师已经完成了逐只持仓的安全边际评估。

1. Read step5_analyst.json（分析师对每只持仓的评估）
2. Read data_exposure.json（敞口矩阵）
3. Read data_portfolio.json（原始持仓）
4. 从组合全局视角做诊断：集中度、一致性风险、隐形敞口

重要：你不输出操作建议——那是 CIO 的事。你只输出诊断报告。`;
  }
  if (stepName === 'l3-analyst-r2') {
    return `## 辩论上下文（第 2 轮）
你是 L3-分析师。策略师已经对你的第一轮评估做了组合层面的诊断。

1. Read step5_analyst.json（你的第一轮评估）
2. Read step6_strategist.json（策略师的诊断报告）
3. 回应策略师发现的集中度风险和一致性矛盾
4. 更新你对每只持仓的评估（如果策略师的诊断让你改变了判断）

输出更新后的逐只持仓评估。`;
  }
  if (stepName === 'l3-strategist-r2') {
    return `## 辩论上下文（第 2 轮）
你是 L3-策略师。分析师已经回应了你的第一轮诊断。

1. Read step5_analyst_r2.json（分析师更新后的评估）
2. Read step6_strategist.json（你的第一轮诊断）
3. 基于分析师的最新评估，更新你的组合诊断报告`;
  }
  if (stepName === 'l4-cio') {
    return `## CIO 初稿上下文
你是 L4-CIO。你是首席投资官。前面所有分析已经完成——现在你要把分析变成具体的资金分配方案。

重要：
1. 先 Read conflicts.json —— 交叉验证发现了矛盾，你必须逐条处理
2. 每条 BUY/ADD 处方必须标注 capital_source（钱从哪来）
3. 处方覆盖全部持仓`;
  }
  if (stepName === 'l4-risk') {
    return `## 风险审查上下文
你是 L4-风险总监。CIO 已经出了初稿处方。你的任务是攻击这个方案。

1. Read step7_cio.json（CIO 初稿）
2. Read conflicts.json（交叉验证冲突）
3. Read data_exposure.json（敞口矩阵）
4. 从攻击者视角审视：集中度、流动性、黑天鹅、Tier1矛盾处理

你的产出是风险审查报告——不是替代 CIO 做决策。`;
  }
  if (stepName === 'l4-cio-final') {
    return `## CIO 终裁上下文
你是 L4-CIO 终裁官。这是最终裁定——没有上诉。

1. Read step7_cio.json（你的初稿）
2. Read step8_risk.json（风险总监的审查意见 —— 必须逐条回应）
3. Read conflicts.json（交叉验证冲突）
4. 出最终处方

重要：
- 必须逐条回应风险总监的意见（接受/驳回/折中）
- 每条处方带 capital_source + timing + suggested_price
- cio_verdict ≥ 500字`;
  }
  return '';
}

// ── Main ────────────────────────────────────────────────────

const dataDir = args.data_dir;
const user_id = args.user_id || '6a094caea814b57d3357fa0b';
const fromStep = args.from_step || null;
const onlyStep = args.only_step || null;

// Find starting index
let startIdx = 0;
let skipTo = false;
if (fromStep) {
  for (let i = 0; i < STEP_ORDER.length; i++) {
    if (STEP_ORDER[i].name === fromStep) {
      startIdx = i;
      skipTo = true;
      break;
    }
  }
  if (skipTo) {
    log(`从 ${fromStep} 开始（跳过前 ${startIdx} 步）`);
  }
}

// ── L1: 行业方向 ──────────────────────────────────────────
phase('L1 行业方向');

const l1Steps = STEP_ORDER.filter(s => s.layer === 'L1').slice(
  onlyStep ? 0 : (fromStep && STEP_ORDER.findIndex(s => s.name === fromStep) > 3 ? 0 : Math.max(0, startIdx))
);

// Build L1 pipeline: run each step, save after each
for (const step of STEP_ORDER) {
  if (step.layer !== 'L1') continue;

  const stepIdx = STEP_ORDER.indexOf(step);
  if (stepIdx < startIdx && !onlyStep) continue;
  if (onlyStep && step.name !== onlyStep) continue;

  const prompt = buildPrompt(step, dataDir, user_id);
  const outputFile = `${dataDir}/${STEP_TO_FILE[step.name]}`;

  log(`${step.name} (${step.agentType}) 开始...`);
  await agent(prompt, {
    agentType: step.agentType,
    label: step.name,
    phase: 'L1 行业方向',
  });
  log(`${step.name} 完成 → ${outputFile}`);

  // 渐进式保存
  try {
    await Bash(`python scripts/save_step.py --dir ${dataDir} --step ${step.name}`);
  } catch (e) {
    log(`[WARNING] save_step failed for ${step.name}: ${e}`);
  }

  if (onlyStep) break;
}

if (onlyStep) {
  log(`单步调试完成: ${onlyStep}`);
  return { status: 'done', only_step: onlyStep };
}

// ── L2: 标的筛选 ──────────────────────────────────────────
phase('L2 标的筛选');

const l2Step = STEP_ORDER.find(s => s.name === 'l2-scout');
if (l2Step) {
  const prompt = buildPrompt(l2Step, dataDir, user_id);
  log(`l2-scout 开始...`);
  await agent(prompt, { agentType: 'l2-scout', label: 'l2-scout', phase: 'L2 标的筛选' });
  log(`l2-scout 完成`);

  try {
    await Bash(`python scripts/save_step.py --dir ${dataDir} --step l2-scout`);
  } catch (e) {
    log(`[WARNING] save_step failed for l2-scout: ${e}`);
  }
}

// ── L3: 组合诊断 ──────────────────────────────────────────
phase('L3 组合诊断');

for (const step of STEP_ORDER) {
  if (step.layer !== 'L3') continue;
  const prompt = buildPrompt(step, dataDir, user_id);
  log(`${step.name} 开始...`);
  await agent(prompt, { agentType: step.agentType, label: step.name, phase: 'L3 组合诊断' });
  log(`${step.name} 完成`);

  try {
    await Bash(`python scripts/save_step.py --dir ${dataDir} --step ${step.name}`);
  } catch (e) {
    log(`[WARNING] save_step failed for ${step.name}: ${e}`);
  }
}

// ── 交叉验证 ──────────────────────────────────────────────
phase('交叉验证');

log('运行交叉验证规则引擎...');
try {
  await Bash(`python scripts/cross_validate.py --dir ${dataDir}`);
  log('交叉验证完成 → conflicts.json');
} catch (e) {
  log(`[WARNING] 交叉验证失败: ${e}`);
}

// ── L4: 最终处方 ──────────────────────────────────────────
phase('L4 最终处方');

for (const step of STEP_ORDER) {
  if (step.layer !== 'L4') continue;
  const prompt = buildPrompt(step, dataDir, user_id);
  log(`${step.name} (${step.agentType}) 开始...`);
  await agent(prompt, { agentType: step.agentType, label: step.name, phase: 'L4 最终处方' });
  log(`${step.name} 完成`);

  try {
    await Bash(`python scripts/save_step.py --dir ${dataDir} --step ${step.name}`);
  } catch (e) {
    log(`[WARNING] save_step failed for ${step.name}: ${e}`);
  }
}

log('全部 Agent 推理完成');
return { status: 'done', data_dir: dataDir };
