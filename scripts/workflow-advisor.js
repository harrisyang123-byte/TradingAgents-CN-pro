// Workflow: Claude Code 组合顾问引擎 — 9 Agent 4 层辩论编排
// 用法: claude -p "Run workflow with args {data_dir: '...', user_id: '...'}"
//
// 注: 自定义 agentType 在 Workflow 子 Agent 内不可用（已知限制），
// 改用 general-purpose + 嵌入 system prompt

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
  { name: 'l1-strategist', layer: 'L1', agentFile: 'agents/advisor/l1-strategist.md' },
  { name: 'l1-contrarian', layer: 'L1', agentFile: 'agents/advisor/l1-contrarian.md' },
  { name: 'l1-strategist-r2', layer: 'L1', agentFile: 'agents/advisor/l1-strategist.md' },
  { name: 'l1-judge', layer: 'L1', agentFile: 'agents/advisor/l1-judge.md' },
  { name: 'l2-scout', layer: 'L2', agentFile: 'agents/advisor/l2-scout.md' },
  { name: 'l3-analyst', layer: 'L3', agentFile: 'agents/advisor/l3-analyst.md' },
  { name: 'l3-strategist', layer: 'L3', agentFile: 'agents/advisor/l3-strategist.md' },
  { name: 'l3-analyst-r2', layer: 'L3', agentFile: 'agents/advisor/l3-analyst.md' },
  { name: 'l3-strategist-r2', layer: 'L3', agentFile: 'agents/advisor/l3-strategist.md' },
  { name: 'l4-cio', layer: 'L4', agentFile: 'agents/advisor/l4-cio.md' },
  { name: 'l4-risk', layer: 'L4', agentFile: 'agents/advisor/l4-risk.md' },
  { name: 'l4-cio-final', layer: 'L4', agentFile: 'agents/advisor/l4-cio-final.md' },
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

function getDebateContext(stepName) {
  if (stepName === 'l1-contrarian') {
    return '你正在挑战 L1-策略师的行业判定。先 Read step1_strategist.json，逐条审视策略师的每个行业判定。再 Read data_macro.json 验证策略师引用的数据。对每条判定提出挑战。';
  }
  if (stepName === 'l1-strategist-r2') {
    return '辩论第2轮。你是策略师。反向者已挑战了你的第一轮判定(step2_contrarian.json)。回应每一条severity=high的挑战：接受并修正/反驳并证明/折中调整。输出修正后的行业判定。';
  }
  if (stepName === 'l1-judge') {
    return '你是L1裁判。策略师和反向者已辩论完。Read 双方的判定+step1_strategist_r2.json+data_macro.json原始数据。数据优先——分歧时以原始数据为准。做出最终行业裁定(超配/标配/低配/零配)。';
  }
  if (stepName === 'l3-strategist') {
    return '你是L3组合策略师(诊断报告员)。分析师已完成逐只持仓评估。Read step5_analyst.json+data_exposure.json+data_portfolio.json。从组合全局做诊断:集中度/一致性风险/隐形敞口。不输出操作建议。';
  }
  if (stepName === 'l3-analyst-r2') {
    return '辩论第2轮。你是分析师。策略师对你的评估做了组合诊断(step6_strategist.json)。回应发现的集中度风险和一致性矛盾。更新你的逐只持仓评估。';
  }
  if (stepName === 'l3-strategist-r2') {
    return '辩论第2轮。你是策略师。分析师已回应你的诊断。Read step5_analyst_r2.json。基于最新评估更新诊断报告。';
  }
  if (stepName === 'l4-cio') {
    return '你是CIO首席投资官。前面所有分析已完成。Read conflicts.json(必须逐条处理)。每条BUY/ADD处方标注capital_source。处方覆盖全部持仓。产出敞口诊断+行业配置+资金分配方案。';
  }
  if (stepName === 'l4-risk') {
    return '你是风险总监。CIO已出初稿。Read step7_cio.json+conflicts.json+data_exposure.json。攻击这个方案:集中度/流动性/黑天鹅/Tier1矛盾处理。产出风险审查报告。';
  }
  if (stepName === 'l4-cio-final') {
    return '你是CIO终裁官。最终裁定——没有上诉。Read step7_cio.json(你的初稿)+step8_risk.json(必须逐条回应)+conflicts.json。出最终处方。每条约带capital_source+timing+suggested_price。cio_verdict≥500字。';
  }
  return '';
}

// ── Main ────────────────────────────────────────────────────

const dataDir = args.data_dir;
const user_id = args.user_id || '6a094caea814b57d3357fa0b';
const fromStep = args.from_step || null;
const onlyStep = args.only_step || null;

let startIdx = 0;
if (fromStep) {
  for (let i = 0; i < STEP_ORDER.length; i++) {
    if (STEP_ORDER[i].name === fromStep) { startIdx = i; break; }
  }
  log(`从 ${fromStep} 开始（跳过前 ${startIdx} 步）`);
}

// ── 辅助: 读 Agent 文件内容 ─────────────────────────────────
async function readAgentFile(agentFile) {
  try {
    const result = await Bash(`cat ${agentFile}`);
    return result || '';
  } catch (e) {
    log(`[WARNING] Cannot read agent file: ${agentFile}`);
    return '';
  }
}

// ── 辅助: 构建完整 prompt ───────────────────────────────────
async function buildFullPrompt(step, dataDir, user_id) {
  const agentSystemPrompt = await readAgentFile(step.agentFile);
  const files = inputFiles(step, dataDir);
  const fileList = files.map(f => `- ${f}`).join('\n');
  const outputFile = `${dataDir}/${STEP_TO_FILE[step.name]}`;
  const debateContext = getDebateContext(step.name);

  return `${agentSystemPrompt}

---

## 当前任务上下文

用户 ID: ${user_id}
数据目录: ${dataDir}

## 输入数据文件（按需用 Read 工具读取，不要一次性全读）
${fileList}

${debateContext ? '## 辩论上下文\n' + debateContext + '\n' : ''}

## 输出要求
将你的完整分析结果以 JSON 格式写入文件: ${outputFile}

先用 Read 工具读取你需要的数据文件，然后推理分析，最后将 JSON 写入 ${outputFile}。
重要：确保输出严格符合上面 system prompt 中定义的 JSON 格式。`;
}

// ── 辅助: 运行单个 step + 渐进式保存 ─────────────────────────
async function runStep(step, phaseName) {
  const prompt = await buildFullPrompt(step, dataDir, user_id);
  log(`${step.name} 开始...`);
  await agent(prompt, { label: step.name, phase: phaseName });
  log(`${step.name} 完成`);

  // 渐进式保存
  try {
    await Bash(`python scripts/save_step.py --dir ${dataDir} --step ${step.name}`);
  } catch (e) {
    log(`[WARNING] save_step failed for ${step.name}`);
  }
}

// ── 执行 ────────────────────────────────────────────────────

// L1
phase('L1 行业方向');
for (const step of STEP_ORDER) {
  if (step.layer !== 'L1') continue;
  const idx = STEP_ORDER.indexOf(step);
  if (idx < startIdx && !onlyStep) continue;
  if (onlyStep && step.name !== onlyStep) continue;
  await runStep(step, 'L1 行业方向');
  if (onlyStep) break;
}
if (onlyStep) {
  log(`单步调试完成: ${onlyStep}`);
  return { status: 'done', only_step: onlyStep };
}

// L2
phase('L2 标的筛选');
const l2Step = STEP_ORDER.find(s => s.name === 'l2-scout');
await runStep(l2Step, 'L2 标的筛选');

// L3
phase('L3 组合诊断');
for (const step of STEP_ORDER) {
  if (step.layer !== 'L3') continue;
  await runStep(step, 'L3 组合诊断');
}

// Cross-validate
phase('交叉验证');
log('运行交叉验证规则引擎...');
try {
  await Bash(`python scripts/cross_validate.py --dir ${dataDir}`);
  log('交叉验证完成 → conflicts.json');
} catch (e) {
  log(`[WARNING] 交叉验证失败`);
}

// L4
phase('L4 最终处方');
for (const step of STEP_ORDER) {
  if (step.layer !== 'L4') continue;
  await runStep(step, 'L4 最终处方');
}

log('全部 Agent 推理完成');
return { status: 'done', data_dir: dataDir };
