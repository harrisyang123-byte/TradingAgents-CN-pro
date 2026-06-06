// Workflow: v3 并行行业PM辩论 — 每个Go行业独立spawn激进PM vs 保守PM
// 用法: claude -p "Run workflow with args {dataDir: '...'}"
//
// 前置: 行业层已输出 industry_allocations.json（含各行业的 final_weight）

export const meta = {
  name: 'v3-pm-debate',
  description: 'v3 并行行业PM辩论 — 每个Go行业独立配仓辩论',
  phases: [
    { title: '准备数据' },
    { title: 'PM辩论' },
    { title: '汇总结果' },
  ],
};

phase('准备数据');

const dataDir = args.dataDir;

// 读行业分配表
let allocations;
try {
  const raw = await Bash(`cat ${dataDir}/industry_allocations.json`);
  allocations = JSON.parse(raw);
  log(`读取到 ${allocations.length} 个行业的配额分配`);
} catch (e) {
  log(`[ERROR] 无法读取行业分配表: ${e}`);
  return { status: 'failed', error: 'no_industry_allocations' };
}

// 只处理 Go 且有配额的行业
const goIndustries = allocations.filter(a => a.go_nogo === 'Go' && a.final_weight > 0);
log(`Go行业: ${goIndustries.length} 个（待配仓）`);

if (goIndustries.length === 0) {
  log('无Go行业需要配仓，跳过PM辩论');
  return { status: 'done', pm_results: [] };
}

// 为每个Go行业准备候选标的数据文件
const maxSingle = args.max_single_weight || 30;
for (const ind of goIndustries) {
  const indName = ind.industry;
  // 生成候选标的JSON（从持仓或 Step2 产出中获取）
  try {
    await Bash(`python3 -c "
import json
# 从 stock_candidates 中筛选属于该行业的候选
with open('${dataDir}/step4_scout.json') as f:
    candidates = json.load(f)
ind_candidates = [c for c in (candidates if isinstance(candidates, list) else candidates.get('candidates', []))
                  if c.get('industry', '').startswith('${indName[:2]}') or c.get('industry_bucket', '').startswith('${indName[:2]}')]
with open('${dataDir}/candidates_${indName}.json', 'w') as f:
    json.dump(ind_candidates, f, ensure_ascii=False, indent=2)
print(f'行业 ${indName}: {len(ind_candidates)} 个候选标的')
" 2>&1`);
  } catch (e) {
    log(`候选标的处理失败 ${indName}: ${e}`);
    await Bash(`echo '[]' > ${dataDir}/candidates_${indName}.json`);
  }
}

// ── PM辩论 ──
phase('PM辩论');

const pmResults = await pipeline(
  goIndustries,
  // 阶段1：激进PM
  async (ind) => {
    const indName = ind.industry;
    const fw = ind.final_weight;
    const ms = maxSingle;

    const agPrompt = `Read ${dataDir}/candidates_${indName}.json first, then ${dataDir}/industry_allocations.json. \
Perform as Aggressive PM for ${indName} industry with ${fw}% quota, max single ${ms}%.`;

    const result = await agent(agPrompt, {
      label: `激进:${indName}`,
      phase: 'PM辩论',
    });

    // 保存激进PM结果
    try {
      await Bash(`cat > ${dataDir}/aggressive_pm_${indName}.json << 'ENDJSON'
${result}
ENDJSON`);
    } catch (e) {
      await Bash(`echo '${JSON.stringify(result)}' > ${dataDir}/aggressive_pm_${indName}.json`);
    }
    log(`${indName} 激进PM完成`);
    return { industry: indName, final_weight: fw };
  },
  // 阶段2：保守PM（读激进PM方案后挑战）
  async (prev) => {
    const indName = prev.industry;
    const fw = prev.final_weight;
    const ms = maxSingle;

    const conPrompt = `Read ${dataDir}/candidates_${indName}.json and ${dataDir}/aggressive_pm_${indName}.json. \
Challenge the aggressive PM's plan. Output your conservative plan for ${indName} with ${fw}% quota.`;

    const result = await agent(conPrompt, {
      label: `保守:${indName}`,
      phase: 'PM辩论',
    });

    try {
      await Bash(`cat > ${dataDir}/conservative_pm_${indName}.json << 'ENDJSON'
${result}
ENDJSON`);
    } catch (e) {
      await Bash(`echo '${JSON.stringify(result)}' > ${dataDir}/conservative_pm_${indName}.json`);
    }
    log(`${indName} 保守PM完成`);
    return { industry: indName, final_weight: fw, max_single: ms };
  },
  // 阶段3：PM裁判（综合激进和保守）
  async (prev) => {
    const indName = prev.industry;
    const fw = prev.final_weight;
    const ms = prev.max_single;

    const judgePrompt = `Read ${dataDir}/candidates_${indName}.json, \
${dataDir}/aggressive_pm_${indName}.json, ${dataDir}/conservative_pm_${indName}.json. \
You are the PM Judge. Synthesize both PMs' opinions. Final allocation for ${indName}, ${fw}% quota.`;

    const result = await agent(judgePrompt, {
      label: `裁判:${indName}`,
      phase: 'PM辩论',
    });

    pmResults.push({ industry: indName, result });
    log(`${indName} PM裁判完成`);
    return { industry: indName, result };
  }
);

// ── 汇总结果 ──
phase('汇总结果');

try {
  await Bash(`cat > ${dataDir}/pm_results.json << 'ENDJSON'
${JSON.stringify(pmResults, null, 2)}
ENDJSON`);
  log(`PM辩论完成，共 ${pmResults.length} 个行业`);
} catch (e) {
  log(`[WARNING] 保存PM结果失败: ${e}`);
}

return {
  status: 'done',
  pm_results: pmResults,
  data_dir: dataDir,
};
