// Workflow: v3 行业层 — 研究员并行 → 反向者挑战 → 跨行业裁判
// 用于替代 advisor_graph.py 中的 new_event_loop() + llm.ainvoke() 模式
// 用法: claude -p "Run workflow with args {dataDir: '...'}"

export const meta = {
  name: 'v3-industry-layer',
  description: 'v3 行业层 — 并行研究员 + 反向者 + 跨行业裁判',
  phases: [
    { title: '宏观裁判' },
    { title: '行业研究' },
    { title: '跨行业配置' },
  ],
};

const dataDir = args.dataDir;

// ── Step 0: 宏观裁判 ──
phase('宏观裁判');

log('运行宏观裁判...');
const macroResult = await agent(
  `Read ${dataDir}/data_macro.json and ${dataDir}/data_market_temp.json. \
Perform as Macro Judge. Determine current risk environment and total_weight_limit.`,
  { label: '宏观裁判', phase: '宏观裁判' }
);
await Bash(`echo '${JSON.stringify(macroResult)}' > ${dataDir}/macro_verdict.json`);
const totalLimit = macroResult.total_weight_limit || 70;
const cashFloor = macroResult.cash_floor || 10;
log(`宏观裁判: total_weight_limit=${totalLimit}%, cash_floor=${cashFloor}%`);

// ── Step 1: 并行行业研究员 + 反向者 ──
phase('行业研究');

// 获取行业列表
let industries;
try {
  const raw = await Bash(`cat ${dataDir}/industry_list.json 2>/dev/null || echo '["消费（必选）","科技","医药健康","金融/保险","新能源（发电）"]'`);
  industries = JSON.parse(raw);
} catch (e) {
  log(`[WARNING] 无法读取行业列表: ${e}`);
  industries = [];
}

log(`需要研究 ${industries.length} 个行业`);

// pipeline: 研究员 → 反向者（每个行业一线）
const researchResults = await pipeline(
  industries,
  // 阶段1: 研究员首发
  async (industry) => {
    const prompt = `Read ${dataDir}/macro_verdict.json first. \
You are the chief industry researcher for ${industry}. \
Read and analyze available data, then output your judgment.`;

    const result = await agent(prompt, {
      label: `研究员:${industry}`,
      phase: '行业研究',
    });

    await Bash(`echo '${JSON.stringify(result)}' > ${dataDir}/researcher_${industry}.json`);
    log(`${industry} 研究员完成`);
    return { industry, result };
  },
  // 阶段2: 反向者挑战
  async (prev) => {
    const industry = prev.industry;

    const prompt = `Read ${dataDir}/researcher_${industry}.json. \
You are the contrarian. Challenge the researcher's conclusions for ${industry}.`;

    const result = await agent(prompt, {
      label: `反向者:${industry}`,
      phase: '行业研究',
    });

    await Bash(`echo '${JSON.stringify(result)}' > ${dataDir}/contrarian_${industry}.json`);
    log(`${industry} 反向者完成`);
    return { industry, researcher: prev.result, contrarian: result };
  }
);

// 汇总所有行业结论
const allResults = researchResults.map(r => ({
  industry: r.industry,
  researcher: r.researcher,
  contrarian: r.contrarian,
}));
await Bash(`echo '${JSON.stringify(allResults, null, 2)}' > ${dataDir}/all_researchers.json`);
log(`所有行业研究完成: ${allResults.length} 个行业`);

// ── Step 2: 跨行业配置裁判 ──
phase('跨行业配置');

log('运行跨行业配置裁判...');
const crossResult = await agent(
  `Read ${dataDir}/all_researchers.json and ${dataDir}/macro_verdict.json. \
You are the Cross-Industry Judge. Allocate ${totalLimit}% across Go industries. \
Max single industry ${args.max_industry_weight || 30}%. \
Output allocations with each industry's final_weight.`,
  { label: '跨行业配置裁判', phase: '跨行业配置' }
);

await Bash(`echo '${JSON.stringify(crossResult, null, 2)}' > ${dataDir}/industry_allocations.json`);

log(`跨行业配置完成: ${crossResult.allocations?.length || 0} 个行业获配额`);

return {
  status: 'done',
  macro: { total_weight_limit: totalLimit, cash_floor: cashFloor },
  allocations: crossResult,
  data_dir: dataDir,
};
