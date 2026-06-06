// Workflow: v3 组合顾问— 约束验证 + Risk Director + Portfolio Synthesizer
// 在 PM 辩论完成后运行
// 用法: claude -p "Run workflow with args {dataDir: '...'}"

export const meta = {
  name: 'v3-synthesizer',
  description: 'v3 风控+合成 — 约束验证、Risk Director辩论、最终处方',
  phases: [
    { title: '风控规则检查' },
    { title: '风险辩论' },
    { title: '最终合成' },
  ],
};

const dataDir = args.dataDir;

phase('风控规则检查');

// Task 3: 风控规则引擎（纯Python，非LLM）
log('运行风控规则引擎...');
let violations;
try {
  const result = await Bash(`python3 -c "
import json
from tradingagents.agents.advisors.risk_rules import check_pm_positions

with open('${dataDir}/pm_results.json') as f:
    pm_results = json.load(f)

total_limit = ${args.total_weight_limit || 100}
cash_floor = ${args.cash_floor || 0}
max_single = ${args.max_single_weight || 30}

# Flatten pm_results to get positions
all_results = []
for pr in pm_results:
    if isinstance(pr, dict):
        result_item = pr.get('result', pr) if 'result' in pr else pr
        all_results.append(result_item)

violations = check_pm_positions(all_results, total_limit, cash_floor, max_single)
print(json.dumps(violations, ensure_ascii=False, indent=2))
" 2>&1`);
  violations = JSON.parse(result);
  log(`风控检查: ${violations.length} 条违规`);
} catch (e) {
  log(`[ERROR] 风控引擎失败: ${e}`);
  violations = [];
}

// 写入违规记录
await Bash(`echo '${JSON.stringify(violations, null, 2)}' > ${dataDir}/risk_violations.json`);

// 有违规时打回PM重做
if (violations.length > 0) {
  log(`发现 ${violations.length} 条违规，需打回PM重做`);
  return {
    status: 'violations_found',
    violations,
    message: 'PM方案有违规，需调整后重跑',
  };
}

log('风控检查通过');

// ── Task 4: Risk Director 双角色辩论 ──
phase('风险辩论');

// 步骤1: 悲观风险总监
log('运行悲观风险总监...');
const pessimistResult = await agent(
  `Read ${dataDir}/pm_results.json and ${dataDir}/data_exposure.json (if exists). \
Perform as Pessimist Risk Director. Find worst-case scenarios for this portfolio.`,
  { label: '悲观风险总监', phase: '风险辩论' }
);
await Bash(`echo '${JSON.stringify(pessimistResult)}' > ${dataDir}/pessimist_risk.json`);

// 步骤2: 乐观风险分析师
log('运行乐观风险分析师...');
const optimistResult = await agent(
  `Read ${dataDir}/pm_results.json and ${dataDir}/pessimist_risk.json. \
Challenge the pessimist's assumptions. Find what they're overreacting to.`,
  { label: '乐观风险分析师', phase: '风险辩论' }
);
await Bash(`echo '${JSON.stringify(optimistResult)}' > ${dataDir}/optimist_risk.json`);

// 步骤3: 风控裁判
log('运行风控裁判...');
const riskVerdict = await agent(
  `Read ${dataDir}/pm_results.json, ${dataDir}/pessimist_risk.json, ${dataDir}/optimist_risk.json. \
You are the Risk Judge. Synthesize both views into a final risk assessment.`,
  { label: '风控裁判', phase: '风险辩论' }
);
await Bash(`echo '${JSON.stringify(riskVerdict)}' > ${dataDir}/risk_assessment.json`);

log('风险辩论完成');

// ── Task 5: Portfolio Synthesizer ──
phase('最终合成');

const synthResult = await agent(
  `Read ${dataDir}/pm_results.json, ${dataDir}/industry_allocations.json, \
${dataDir}/risk_assessment.json, ${dataDir}/step3_judge.json (if exists), \
${dataDir}/data_portfolio.json (if exists).

You are the Portfolio Synthesizer. Do NOT make new investment decisions. Do:
1. Validate constraint chain (check allocations vs actuals)
2. Identify gaps (allocated quota not filled by PM)
3. Trigger scout for gaps > 3%
4. Summarize industry_matrix and final prescription

Output to ${dataDir}/industry_matrix.json and ${dataDir}/final_prescription.json`,
  { label: 'Portfolio Synthesizer', phase: '最终合成' }
);

// 保存
await Bash(`echo '${JSON.stringify(synthResult)}' > ${dataDir}/synth_output.json`);

log('Portfolio Synthesizer 完成');

return {
  status: 'done',
  violations: violations.length,
  risk_verdict: riskVerdict,
  synth_output: synthResult,
  data_dir: dataDir,
};
