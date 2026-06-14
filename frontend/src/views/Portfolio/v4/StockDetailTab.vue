<template>
  <div class="stock-detail-tab">
    <div v-if="loading" class="sdt-loading"><el-skeleton :rows="6" animated /></div>
    <template v-else-if="detail && detail.code">

      <!-- ===== 头部 ===== -->
      <div class="card sdt-head">
        <div class="sdt-head-row">
          <span class="sdt-title">
            {{ detail.name }} <span class="sdt-code">{{ detail.code }}</span>
            <span v-if="detail.industry" class="sdt-industry">· {{ detail.industry }}</span>
          </span>
          <span class="sdt-tags">
            <el-tag :type="ratingType" effect="dark" size="large">{{ detail.rating }}</el-tag>
            <span v-if="detail.credibility?.critic_score != null" class="sdt-credit-tag">
              评审 <b v-if="detail.credibility.initial_score != null && detail.credibility.initial_score !== detail.credibility.critic_score">{{ detail.credibility.initial_score }}→</b>{{ detail.credibility.critic_score }} ✓
            </span>
          </span>
        </div>
      </div>

      <!-- ===== ① 操作建议（直接照做） ===== -->
      <div class="card sdt-action">
        <div class="sdt-section-title sdt-action-title">💼 ① 操作建议（直接照做）</div>
        <div class="sdt-action-grid">
          <div class="sdt-action-cell">
            <span class="sdt-action-label">当前/判断价</span>
            <b class="sdt-action-val">¥{{ detail.price_at_judgment ?? '-' }}</b>
          </div>
          <div class="sdt-action-cell">
            <span class="sdt-action-label">建议买点</span>
            <b class="sdt-action-val">{{ fmtRange(detail.entry_price_range) }}</b>
          </div>
          <div class="sdt-action-cell">
            <span class="sdt-action-label">目标价</span>
            <b class="sdt-action-val">{{ fmtTarget(detail.target_price) }}</b>
          </div>
          <div class="sdt-action-cell">
            <span class="sdt-action-label">硬止损线</span>
            <b class="sdt-action-val sdt-action-stop">¥{{ stopPrice ?? '-' }}</b>
          </div>
        </div>
        <div v-if="detail.industry_weight_pct != null" class="sdt-pos-calc">
          <b>📊 建议仓位：</b>行业内配比 <b>{{ detail.industry_weight_pct }}%</b>
          <span v-if="detail.industry">（来自 {{ detail.industry }} 资金配比层）</span>。
          若组合总市值 <input class="sdt-pos-input" type="number" v-model.number="capInput" /> 万元，
          建议金额约 <b>{{ posAmount.toFixed(1) }}</b> 万元 ≈ <b>{{ posShares }}</b> 股
          <span class="sdt-pos-note">A股 100 股/手，不足 1 手等回调或小额参与</span>
        </div>
        <div :class="['sdt-action-alert', alertClass]">
          ⚠️ <b>{{ alertHeadline }}</b>：{{ alertBody }}
        </div>
        <div v-if="topSells.length" class="sdt-action-sells">
          <span class="sdt-action-sells-label">⚡ 关键止损线（看到立即执行）</span>
          <ol><li v-for="(s, i) in topSells" :key="i">{{ s }}</li></ol>
        </div>
      </div>

      <!-- ===== ② 为什么这样判断（30 秒精炼,5 行核心） ===== -->
      <div class="card sdt-why">
        <div class="sdt-section-title sdt-why-title">📄 ② 为什么这样判断（30 秒读完核心）</div>
        <div v-if="detail.verdict_oneliner" class="sdt-why-oneliner">
          <span class="sdt-why-icon">📌</span>{{ detail.verdict_oneliner }}
        </div>
        <ul class="sdt-why-points">
          <li v-if="whyChain"><span class="sdt-why-tag sdt-tag-chain">🎯 投什么</span>{{ whyChain }}</li>
          <li v-if="whyMoat"><span class="sdt-why-tag sdt-tag-moat">🏰 凭什么</span>{{ whyMoat }}</li>
          <li v-if="whyValuation"><span class="sdt-why-tag sdt-tag-val">💰 估值</span>{{ whyValuation }}</li>
          <li v-if="whyTam"><span class="sdt-why-tag sdt-tag-chain">📈 成长空间</span>{{ whyTam }}</li>
          <li v-if="whyRoic"><span class="sdt-why-tag sdt-tag-moat">🏭 价值创造</span>{{ whyRoic }}</li>
          <li v-if="whyDcf"><span class="sdt-why-tag sdt-tag-val">📐 内在值</span>{{ whyDcf }}</li>
          <li v-if="whyWorst"><span class="sdt-why-tag sdt-tag-worst">⚠️ 最坏</span>{{ whyWorst }}</li>
          <li v-if="whyExpGap"><span class="sdt-why-tag sdt-tag-gap">🎲 预期差</span>{{ whyExpGap }}</li>
        </ul>
        <!-- 🎯 可操作结论(2026-06-14 三维: 好公司ROIC × 好价格PE × 好未来PEG, 全 verified) -->
        <div v-if="actionableVerdict" class="sdt-actionable">
          <div class="sdt-actionable-head">
            <span class="sdt-actionable-tag">🎯 明天可操作</span>
            <b class="sdt-actionable-stance">{{ actionableVerdict.stance }}</b>
          </div>
          <div v-if="actionableText" class="sdt-actionable-data">{{ actionableText }}</div>
          <p v-if="actionableVerdict.reason" class="sdt-actionable-reason">{{ actionableVerdict.reason }}</p>
          <p v-if="actionableVerdict.future_market_correction" class="sdt-actionable-correction">🔮 未来维度修正：{{ actionableVerdict.future_market_correction }}</p>
          <p v-if="actionableVerdict.critic_correction" class="sdt-actionable-correction">🎓 critic修正：{{ actionableVerdict.critic_correction }}</p>
        </div>
        <!-- 辅助标签栏: 较上次自检 + 可信度 + 历史准确率 -->
        <div class="sdt-why-aux">
          <div v-if="detail.reflection?.what_changed" class="sdt-aux-card sdt-aux-reflection">
            <span class="sdt-aux-label">🔄 较上次/自检</span>
            <p>{{ detail.reflection.what_changed }}</p>
            <p v-if="detail.reflection.self_check" class="sdt-aux-sub">{{ detail.reflection.self_check }}</p>
          </div>
          <div v-if="detail.credibility" class="sdt-aux-card sdt-aux-cred">
            <span class="sdt-aux-label">🎩 可信度</span>
            <p>
              经 <b>{{ detail.credibility.reviewers?.join('/') || '四视角' }}</b> 评审,
              <b>{{ detail.credibility.initial_score ?? '?' }}→{{ detail.credibility.critic_score ?? '?' }}</b> 分
              <b>{{ detail.credibility.final_verdict || 'ACCEPT' }}</b>
            </p>
            <p v-if="detail.credibility.challenges?.length" class="sdt-aux-sub">
              关键挑战：{{ detail.credibility.challenges.slice(0, 2).join('；') }}
            </p>
          </div>
          <div v-if="detail.historical_alpha" class="sdt-aux-card sdt-aux-alpha">
            <span class="sdt-aux-label">📊 历史准确率</span>
            <p>
              <el-tag :type="hitType" size="small">{{ hitLabel }}</el-tag>
              {{ (detail.historical_alpha.alpha_note || '').slice(0, 60) }}
            </p>
          </div>
        </div>
      </div>

      <!-- ===== ③ 支撑分析（按编排器流程顺序展开,看完整推理链） ===== -->
      <div class="card sdt-support">
        <div class="sdt-section-title">🔬 ③ 支撑分析 — 完整推理链（点击每步展开）</div>
        <p class="sdt-support-desc">展示系统按编排器实际流程的完整推理链：「数据采集 → 4 分析师并列 → 多空辩论 → 3 方风险辩论 → director 综合 → critic 评审」。Step 1-4 是 director 的 4 类输入信号，Step 5 是 director 综合产出，Step 6 是质量闸门。</p>
        <el-collapse>

          <!-- Step 1 数据采集 -->
          <el-collapse-item name="step1">
            <template #title>
              <span class="sdt-step-title">
                📥 Step 1 · 数据采集（data-desk）
                <el-tag size="small" type="info" class="sdt-step-tag">{{ detail.evidence?.length ?? 0 }} 条数据</el-tag>
                <el-tag v-if="evidenceCoverage.verified > 0" size="small" type="success" class="sdt-step-tag">✓ verified {{ evidenceCoverage.verified }}</el-tag>
                <el-tag v-if="evidenceCoverage.estimated > 0" size="small" type="warning" class="sdt-step-tag">⚠ estimated {{ evidenceCoverage.estimated }}</el-tag>
                <el-tag v-if="evidenceCoverage.missing > 0" size="small" type="info" class="sdt-step-tag">- missing {{ evidenceCoverage.missing }}</el-tag>
              </span>
            </template>
            <p class="sdt-step-desc">data-desk 是唯一联网取数台，按 schema 分组采集：估值/财务/5力深做(21字段)/同业可比/政策催化/资金面/一致预期。所有 5 力分析师消费的数据都来自这里。</p>
            <div v-if="!detail.evidence?.length" class="sdt-empty">（暂无数据）</div>
            <div v-else>
              <div v-for="(items, group) in groupedEvidence" :key="group" class="sdt-evi-group">
                <div class="sdt-evi-group-head">
                  <b>{{ group }}</b>
                  <span class="sdt-evi-group-count">{{ items.length }} 条</span>
                </div>
                <ul class="sdt-evidence-list">
                  <li v-for="(e, i) in items" :key="i">
                    <el-tag :type="evidenceTagType(e.status)" size="small" effect="plain">{{ e.status }}</el-tag>
                    <el-tag v-if="(e as any).used_in?.length" size="small" type="success" effect="plain" class="sdt-used-tag">used in {{ (e as any).used_in.length }}</el-tag>
                    <el-tag v-else size="small" type="info" effect="plain" class="sdt-unused-tag">unused</el-tag>
                    {{ e.claim }}
                    <span v-if="e.source" class="sdt-evidence-src">— {{ e.source }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </el-collapse-item>

          <!-- Step 2 三分析师 -->
          <el-collapse-item name="step2">
            <template #title>
              <span class="sdt-step-title">
                👔 Step 2 · 4 分析师并列分析 (财务/竞争+5力/估值/舆情)
                <el-tag v-if="ff.moat_rating" :type="moatType(ff.moat_rating)" size="small" class="sdt-step-tag">护城河 {{ ff.moat_rating }}</el-tag>
                <el-tag v-if="cfd?.weakest_link" type="danger" size="small" effect="plain" class="sdt-step-tag">weakest = {{ extractWeakestForce(cfd.weakest_link) }}</el-tag>
              </span>
            </template>
            <!-- 2a 财务分析师 -->
            <details class="sdt-substep">
              <summary>📊 a · 财务分析师</summary>
              <p v-if="detail.analysts?.financial">{{ detail.analysts.financial }}</p>
              <p v-else class="sdt-empty">（payload.analysts.financial 未提供）</p>
            </details>
            <!-- 2b 竞争分析师 + 五力深做 -->
            <details class="sdt-substep" open>
              <summary>🏰 b · 竞争分析师 + 波特五力深做（核心展示）</summary>
              <p v-if="ff.moat_synthesis" class="sdt-moat-synthesis">{{ ff.moat_synthesis }}</p>
              <table v-if="ff.five_forces_summary" class="sdt-ff-table">
                <tr><td class="sdt-ff-name">🚧 进入威胁</td><td :class="ffLevelClass(ff.five_forces_summary.entry)">{{ ff.five_forces_summary.entry }}</td></tr>
                <tr><td class="sdt-ff-name">🔄 替代威胁</td><td :class="ffLevelClass(ff.five_forces_summary.substitute)">{{ ff.five_forces_summary.substitute }}</td></tr>
                <tr><td class="sdt-ff-name">🛒 买方议价</td><td :class="ffLevelClass(ff.five_forces_summary.buyer)">{{ ff.five_forces_summary.buyer }}</td></tr>
                <tr><td class="sdt-ff-name">📦 供方议价</td><td :class="ffLevelClass(ff.five_forces_summary.supplier)">{{ ff.five_forces_summary.supplier }}</td></tr>
                <tr><td class="sdt-ff-name">⚔️ 同业竞争</td><td :class="ffLevelClass(ff.five_forces_summary.rivalry)">{{ ff.five_forces_summary.rivalry }}</td></tr>
              </table>
              <div v-if="cfd?.mutual_reinforcement?.length" class="sdt-cfd-block">
                <b>🔗 力间互相强化（飞轮）：</b>
                <ol><li v-for="(m, i) in cfd.mutual_reinforcement" :key="'r'+i">{{ m.force_a }} × {{ m.force_b }}：{{ m.mechanism }}</li></ol>
              </div>
              <div v-if="cfd?.mutual_offset?.length" class="sdt-cfd-block">
                <b>⚖️ 力间互相抵消：</b>
                <ol><li v-for="(m, i) in cfd.mutual_offset" :key="'o'+i">{{ m.force_a }} × {{ m.force_b }}：{{ m.mechanism }}</li></ol>
              </div>
              <p v-if="cfd?.weakest_link" class="sdt-weakest"><b>⚠️ 最弱一环（护城河上限）：</b>{{ cfd.weakest_link }}</p>
              <p v-if="ff.moat_durability" class="sdt-key-risk"><b>⏳ 持续性：</b>{{ ff.moat_durability }}</p>
              <p v-if="ff.key_risk" class="sdt-key-risk"><b>🎯 最大单一风险：</b>{{ ff.key_risk }}</p>
              <details v-if="ff.monitoring_signals?.length" class="sdt-mon-details">
                <summary>👀 护城河监控信号（{{ ff.monitoring_signals.length }} 条）</summary>
                <ul><li v-for="(s, i) in ff.monitoring_signals" :key="i">{{ s }}</li></ul>
              </details>
              <!-- 产业链卡位放进竞争分析师下面 -->
              <details v-if="detail.chain_positioning?.industry_top?.length" class="sdt-mon-details" style="margin-top:10px">
                <summary>🎯 产业链卡位（同环节 top {{ detail.chain_positioning.industry_top.length }} 横向比较）</summary>
                <p v-if="detail.chain_positioning.chokepoint" class="sdt-chain-flow">
                  <span class="sdt-chain-node">{{ detail.chain_positioning.industry }}</span> →
                  <span class="sdt-chain-node">{{ detail.chain_positioning.chokepoint }}</span> →
                  <span class="sdt-chain-rank">本股 #{{ detail.chain_positioning.my_rank ?? '?' }}</span>
                </p>
                <table class="sdt-chain-table">
                  <thead><tr><th>排序</th><th>标的</th><th>评级</th><th>目标价</th><th>为什么</th></tr></thead>
                  <tbody>
                    <tr v-for="(r, i) in detail.chain_positioning.industry_top" :key="i" :class="{ 'sdt-chain-self': r.is_self }">
                      <td><span :class="r.is_self ? 'sdt-chain-rk-self' : 'sdt-chain-rk'">#{{ r.rank }}</span></td>
                      <td><b>{{ r.recommended }}</b></td>
                      <td>{{ r.rating }}</td>
                      <td>{{ r.target_price_live != null ? `¥${r.target_price_live}` : '-' }}</td>
                      <td class="sdt-chain-why">{{ r.why }}</td>
                    </tr>
                  </tbody>
                </table>
              </details>
            </details>
            <!-- 2c 估值分析师 -->
            <!-- 2c 估值分析师 — D0-8 升级反向DCF + SOTP + 多方法交叉 -->
            <details class="sdt-substep" open>
              <summary>💰 c · 估值分析师（反向DCF + SOTP + 多方法交叉 + 锚定自查）</summary>

              <!-- 反向DCF 量化对照(核心) -->
              <div v-if="rdcf" class="sdt-rdcf-block">
                <div class="sdt-rdcf-title">🔄 反向 DCF — 市场在赌什么 vs 可验证现实</div>
                <p v-if="rdcf.current_price" class="sdt-rdcf-price"><b>当前价：</b>{{ rdcf.current_price }}</p>
                <p v-if="rdcf.market_implied_assumptions" class="sdt-rdcf-implied">
                  <b>📊 市场隐含假设：</b>{{ rdcf.market_implied_assumptions }}
                </p>
                <p v-if="rdcf.verifiable_reality" class="sdt-rdcf-reality">
                  <b>🔍 可验证现实：</b>{{ rdcf.verifiable_reality }}
                </p>
                <table v-if="rdcf.assumption_vs_reality?.length" class="sdt-rdcf-table">
                  <thead><tr><th>市场隐含假设</th><th>可验证现实</th><th>判定</th></tr></thead>
                  <tbody>
                    <tr v-for="(a, i) in rdcf.assumption_vs_reality" :key="i" :class="verdictCls(a.verdict)">
                      <td>{{ a.assumption }}</td><td>{{ a.reality }}</td>
                      <td><span :class="['sdt-verdict-tag', verdictCls(a.verdict)]">{{ a.verdict }}</span></td>
                    </tr>
                  </tbody>
                </table>
                <p v-if="rdcf.gap_conclusion" class="sdt-rdcf-conclusion">
                  <b>🎯 缺口结论：</b>{{ rdcf.gap_conclusion }}
                </p>
              </div>

              <!-- 多方法交叉验证 -->
              <div v-if="vcc" class="sdt-vcc-block">
                <div class="sdt-rdcf-title">🧮 多方法交叉验证（避免单一 PE 锚定）</div>
                <div v-if="vcc.comparable" class="sdt-vcc-row"><b>📐 可比估值：</b>{{ vcc.comparable }}</div>
                <div v-if="vcc.sotp" class="sdt-vcc-row"><b>🧩 SOTP 分部估值：</b>{{ vcc.sotp }}</div>
                <div v-if="vcc.optionality" class="sdt-vcc-row"><b>🎰 可选性价值（期权）：</b>{{ vcc.optionality }}</div>
                <div v-if="vcc.methods_divergence" class="sdt-vcc-divergence"><b>⚠️ 多方法分歧：</b>{{ vcc.methods_divergence }}</div>
              </div>

              <!-- analysts.valuation 完整文字（保留作为补充） -->
              <details v-if="detail.analysts?.valuation" class="sdt-vfull">
                <summary>📋 估值分析师完整文字（含三锚 + 三情景 + 买卖信号 + 锚定自查）</summary>
                <pre class="sdt-vfull-text">{{ detail.analysts.valuation }}</pre>
              </details>

              <p v-if="!rdcf && !vcc && !detail.analysts?.valuation" class="sdt-empty">（valuation 未提供）</p>
            </details>
            <!-- 2d 舆情分析师 (sentiment) — 与财务/竞争/估值并列的第 4 个分析师 -->
            <details class="sdt-substep" v-if="detail.sentiment_view || detail.sentiment_full">
              <summary>📰 d · 舆情分析师（sentiment — 5 维:温度/新闻/一致预期/资金面/情绪vs基本面）</summary>
              <p v-if="detail.sentiment_view" class="sdt-thesis-text">{{ detail.sentiment_view }}</p>
              <div v-if="detail.sentiment_full" class="sdt-sentiment-detail">
                <p v-if="detail.sentiment_full.sentiment_temperature"><b>🌡️ 温度：</b>{{ detail.sentiment_full.sentiment_temperature }} ({{ detail.sentiment_full.temperature_score }}分)</p>
                <p v-if="detail.sentiment_full.consensus_view?.our_view_vs_consensus"><b>📊 vs 一致预期：</b>{{ detail.sentiment_full.consensus_view.our_view_vs_consensus }}</p>
                <p v-if="detail.sentiment_full.capital_flow?.interpretation"><b>💰 资金面：</b>{{ detail.sentiment_full.capital_flow.interpretation }}</p>
                <p v-if="detail.sentiment_full.sentiment_vs_fundamental"><b>⚖️ 情绪vs基本面：</b>{{ detail.sentiment_full.sentiment_vs_fundamental }}</p>
                <details v-if="detail.sentiment_full.key_underpriced?.length" class="sdt-sentiment-sub">
                  <summary>未充分定价的利空/利好 ({{ detail.sentiment_full.key_underpriced.length }} 项)</summary>
                  <ul><li v-for="(k, i) in detail.sentiment_full.key_underpriced" :key="i">{{ k }}</li></ul>
                </details>
              </div>
            </details>
          </el-collapse-item>

          <!-- Step 3 多空辩论 -->
          <el-collapse-item v-if="debatePairs.length" name="step3">
            <template #title>
              <span class="sdt-step-title">
                ⚔️ Step 3 · 多空 {{ debatePairs.length }} 轮辩论
                <el-tag size="small" type="info" class="sdt-step-tag">{{ debatePairs.length }} 轮交锋</el-tag>
              </span>
            </template>
            <p class="sdt-step-desc">3 分析师产出后,bull/bear 对立角色 N 轮辩论, R3 终局双方诚实让步形成共识区</p>
            <div v-for="(pair, i) in debatePairs" :key="i" class="sdt-debate-block">
              <div class="sdt-debate-round-tag">第 {{ pair.round }} 轮{{ pair.round === debatePairs.length ? ' · 终局' : '' }}</div>
              <div class="sdt-duel">
                <div class="sdt-bull-side">
                  <div class="sdt-side-tag sdt-bull-tag">多头</div>
                  <p>{{ pair.bull }}</p>
                </div>
                <div class="sdt-bear-side">
                  <div class="sdt-side-tag sdt-bear-tag">空头</div>
                  <p>{{ pair.bear }}</p>
                </div>
              </div>
            </div>
          </el-collapse-item>

          <!-- Step 4 3 方风险辩论 (TradingAgents 风格独立步骤, 是 director 的输入之一) -->
          <el-collapse-item v-if="detail.risk_debate_summary || detail.risk_debate_full" name="step4">
            <template #title>
              <span class="sdt-step-title">
                ⚖️ Step 4 · 3 方风险辩论 (aggressive / safe / neutral)
                <el-tag size="small" type="info" class="sdt-step-tag">TradingAgents 风格 · director 输入之一</el-tag>
              </span>
            </template>
            <p class="sdt-step-desc">基于多空辩论结论, 3 方对仓位/止损/tail risk 等执行参数辩论。aggressive 攻保守 / safe 攻激进 / neutral 协调给 director 修正建议。这与 Step 3 多空辩论维度不同(方向 vs 执行)。</p>
            <div v-if="detail.risk_debate_summary" class="sdt-risk-summary">
              <p v-if="detail.risk_debate_summary.aggressive_main_attack"><b>🔥 激进派核心攻击：</b>{{ detail.risk_debate_summary.aggressive_main_attack }}</p>
              <p v-if="detail.risk_debate_summary.safe_main_attack"><b>🛡️ 保守派核心攻击：</b>{{ detail.risk_debate_summary.safe_main_attack }}</p>
              <p v-if="detail.risk_debate_summary.neutral_proposal_adopted" class="sdt-risk-adopted"><b>✅ 中立派建议（director 已采纳）：</b>{{ detail.risk_debate_summary.neutral_proposal_adopted }}</p>
              <p v-if="detail.risk_debate_summary.neutral_proposal_rejected" class="sdt-risk-rejected"><b>❌ 中立派建议（director 拒绝）：</b>{{ detail.risk_debate_summary.neutral_proposal_rejected }}</p>
            </div>
            <details v-if="detail.risk_debate_full?.aggressive" class="sdt-substep">
              <summary>🔥 aggressive 完整产出（含 alternative_proposal + non_negotiable）</summary>
              <p v-if="detail.risk_debate_full.aggressive.stance"><b>立场：</b>{{ detail.risk_debate_full.aggressive.stance }}</p>
              <p v-if="detail.risk_debate_full.aggressive.alternative_proposal"><b>alternative：</b>{{ JSON.stringify(detail.risk_debate_full.aggressive.alternative_proposal) }}</p>
              <p v-if="detail.risk_debate_full.aggressive.data_status" class="sdt-data-status">data_status: {{ detail.risk_debate_full.aggressive.data_status }}</p>
            </details>
            <details v-if="detail.risk_debate_full?.safe" class="sdt-substep">
              <summary>🛡️ safe 完整产出</summary>
              <p v-if="detail.risk_debate_full.safe.stance"><b>立场：</b>{{ detail.risk_debate_full.safe.stance }}</p>
              <p v-if="detail.risk_debate_full.safe.alternative_proposal"><b>alternative：</b>{{ JSON.stringify(detail.risk_debate_full.safe.alternative_proposal) }}</p>
              <p v-if="detail.risk_debate_full.safe.data_status" class="sdt-data-status">data_status: {{ detail.risk_debate_full.safe.data_status }}</p>
            </details>
            <details v-if="detail.risk_debate_full?.neutral" class="sdt-substep">
              <summary>⚖️ neutral 完整产出</summary>
              <p v-if="detail.risk_debate_full.neutral.neutral_proposal"><b>neutral_proposal：</b>{{ JSON.stringify(detail.risk_debate_full.neutral.neutral_proposal) }}</p>
              <p v-if="detail.risk_debate_full.neutral.data_status" class="sdt-data-status">data_status: {{ detail.risk_debate_full.neutral.data_status }}</p>
            </details>
          </el-collapse-item>

          <!-- Step 5 director 综合拍板 (消费 Step 1-4 全部) -->
          <el-collapse-item name="step5">
            <template #title><span class="sdt-step-title">🎩 Step 5 · director 综合拍板（消费 Step 1-4 全部产出）</span></template>
            <p class="sdt-step-desc">director 综合 data-desk + 4 分析师 + 多空辩论 + 3 方风险辩论 + memory, 给反骑墙立场 + reflection + forward_view 6 维 + valuation_basis 推导链</p>
            <p v-if="detail.thesis" class="sdt-thesis-text"><b>核心论述：</b>{{ detail.thesis }}</p>
            <div class="sdt-thesis-grid">
              <p v-if="detail.business_quality"><b>🏢 生意质量：</b>{{ detail.business_quality }}</p>
              <p v-if="detail.position_nature"><b>📌 投资 or 交易：</b>{{ detail.position_nature }}</p>
              <p v-if="detail.worst_case"><b>🧠 逆向最坏：</b>{{ detail.worst_case }}</p>
              <p v-if="detail.downside"><b>🌊 赔率+周期：</b>{{ detail.downside }}</p>
              <p v-if="detail.expectation_gap"><b>🎲 预期差：</b>{{ detail.expectation_gap }}</p>
            </div>
            <!-- forward_view -->
            <details class="sdt-substep" v-if="detail.forward_view">
              <summary>🔭 forward_view · 三情景 + 触发监控 + 6 维多维推演</summary>
              <div v-if="fv.path_scenarios?.length" class="sdt-fv-scn">
                <b>🎯 三情景：</b>
                <div v-for="(s, i) in fv.path_scenarios" :key="i" class="sdt-scn">
                  {{ scnLabel(s.name) }} ({{ Math.round((s.prob||0)*100) }}%): {{ s.trigger }} →
                  目标 {{ s.implied_target_price ?? '-' }}{{ s.implied_pe ? ` (PE ${s.implied_pe})` : '' }}
                </div>
              </div>
              <div v-if="fv.trigger_monitor?.length" class="sdt-fv-trigger">
                <b>⚡ 触发监控（绝对阈值）：</b>
                <ol><li v-for="(t, i) in fv.trigger_monitor" :key="i">{{ t }}</li></ol>
              </div>
              <p v-if="fv.mid_term_path"><b>📈 中长期路径：</b>{{ fv.mid_term_path }}</p>
              <p v-if="fv.expectation_vs_consensus"><b>📊 vs 一致预期：</b>{{ fv.expectation_vs_consensus }}</p>
              <div v-if="fv.market_regime || fv.liquidity_environment || fv.industry_cycle_phase || fv.systematic_risk_beta || fv.comparable_matrix || fv.pricing_power_analysis" class="sdt-fv-6d">
                <div class="sdt-fv-6d-title">🌐 多维推演（不只 PE）</div>
                <div v-if="fv.market_regime" class="sdt-fv-6d-row"><b>📈 市场风格：</b>{{ fv.market_regime }}</div>
                <div v-if="fv.liquidity_environment" class="sdt-fv-6d-row"><b>💧 流动性：</b>{{ fv.liquidity_environment }}</div>
                <div v-if="fv.industry_cycle_phase" class="sdt-fv-6d-row"><b>🔄 行业周期：</b>{{ fv.industry_cycle_phase }}</div>
                <div v-if="fv.systematic_risk_beta" class="sdt-fv-6d-row"><b>⚡ 系统性 β：</b>{{ typeof fv.systematic_risk_beta === 'string' ? fv.systematic_risk_beta : JSON.stringify(fv.systematic_risk_beta) }}</div>
                <div v-if="fv.comparable_matrix" class="sdt-fv-6d-row"><b>📊 对标矩阵：</b>{{ typeof fv.comparable_matrix === 'string' ? fv.comparable_matrix : JSON.stringify(fv.comparable_matrix) }}</div>
                <div v-if="fv.pricing_power_analysis" class="sdt-fv-6d-row"><b>🛒 定价能力：</b>{{ fv.pricing_power_analysis }}</div>
              </div>
            </details>
            <!-- reflection 完整版 -->
            <details class="sdt-substep" v-if="detail.reflection">
              <summary>🔄 reflection · 较上次完整自检</summary>
              <p v-if="detail.reflection.prev_stance"><b>上次立场：</b>{{ detail.reflection.prev_stance }}</p>
              <p v-if="detail.reflection.what_changed"><b>本次变化：</b>{{ detail.reflection.what_changed }}</p>
              <p v-if="detail.reflection.why_changed"><b>为何改：</b>{{ detail.reflection.why_changed }}</p>
              <p v-if="detail.reflection.self_check"><b>自检：</b>{{ detail.reflection.self_check }}</p>
            </details>
            <!-- memory_used -->
            <details class="sdt-substep" v-if="detail.memory_used?.length">
              <summary>🧠 memory 已引用过往经验（{{ detail.memory_used.length }} 条）</summary>
              <ul><li v-for="(m, i) in detail.memory_used" :key="i">{{ m }}</li></ul>
            </details>
          </el-collapse-item>

          <!-- Step 6 critic 评审 -->
          <el-collapse-item v-if="detail.credibility" name="step6">
            <template #title>
              <span class="sdt-step-title">
                🎓 Step 6 · critic 评审（4 视角质量闸门）
                <el-tag size="small" type="success" class="sdt-step-tag">{{ detail.credibility.final_verdict || 'ACCEPT' }} {{ detail.credibility.critic_score }} 分</el-tag>
              </span>
            </template>
            <p class="sdt-step-desc">芒格/段永平/Serenity/达里奥 4 视角评审委员会拷问 verdict, 必须 ≥85 分且无 fatal_flaw 才通过</p>
            <p>
              <b>评审委员：</b>
              <el-tag v-for="(r, i) in (detail.credibility.reviewers || ['芒格', '段永平', 'Serenity', '达里奥'])" :key="i" type="info" size="small" class="sdt-rev-tag">{{ r }}</el-tag>
            </p>
            <p>
              <b>评审分数：</b>
              <span v-if="detail.credibility.initial_score != null && detail.credibility.initial_score !== detail.credibility.critic_score">
                初始 {{ detail.credibility.initial_score }} 分 →
              </span>
              终评 <b>{{ detail.credibility.critic_score }} 分</b>
              <span v-if="detail.credibility.critic_iterations">（{{ detail.credibility.critic_iterations }} 轮迭代）</span>
            </p>
            <div v-if="detail.credibility.challenges?.length">
              <b>关键挑战 / 微调建议：</b>
              <ol class="sdt-cred-chals">
                <li v-for="(c, i) in detail.credibility.challenges" :key="i">{{ c }}</li>
              </ol>
            </div>

            <!-- 锚定自查融入 critic 评审(D0-8 用户发现的方法论漏洞,critic 必查的一部分) -->
            <details v-if="detail.anchoring_check" class="sdt-substep" open style="margin-top:10px">
              <summary>🧭 锚定 vs 预期差自查（critic 6.7 必查项）</summary>
              <p v-if="detail.anchoring_check.honest_answer" class="sdt-anchor-line"><b>结论：</b>{{ detail.anchoring_check.honest_answer }}</p>
              <p v-if="detail.anchoring_check.corrected_framing" class="sdt-anchor-line sdt-anchor-fix"><b>✅ 已修正：</b>{{ detail.anchoring_check.corrected_framing }}</p>
            </details>
          </el-collapse-item>

          <!-- Step 7 历史准确率 完整 -->
          <el-collapse-item v-if="detail.historical_alpha" name="step7">
            <template #title>
              <span class="sdt-step-title">
                📈 Step 7 · 历史判断准确率（结果闭环）
                <el-tag size="small" :type="hitType" class="sdt-step-tag">{{ hitLabel }}</el-tag>
              </span>
            </template>
            <p>{{ detail.historical_alpha.alpha_note }}</p>
            <p class="sdt-alpha-meta">数据状态: {{ detail.historical_alpha.data_status }} | 评估日: {{ detail.historical_alpha.evaluated_at }}</p>
          </el-collapse-item>

          <!-- Step 8 风险 + 止损全集 -->
          <el-collapse-item name="step8">
            <template #title>
              <span class="sdt-step-title">
                ⚠️ Step 8 · 风险清单 + 止损纪律全集
                <el-tag v-if="detail.risks?.length" size="small" type="danger" class="sdt-step-tag">{{ detail.risks.length }} 项风险</el-tag>
              </span>
            </template>
            <div v-if="detail.risks?.length" class="sdt-risk-block">
              <b>主要风险（{{ detail.risks.length }} 项）：</b>
              <el-tag v-for="(r, i) in detail.risks" :key="i" type="danger" size="small" effect="plain" class="sdt-risk">{{ r }}</el-tag>
            </div>
            <div v-if="detail.sell_discipline?.length" class="sdt-sell-block">
              <b>止损纪律全集（{{ detail.sell_discipline.length }} 条）：</b>
              <ol><li v-for="(s, i) in detail.sell_discipline" :key="i">{{ s }}</li></ol>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </template>
    <EmptyUnitState v-else title="未找到该个股分析" />
  </div>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import EmptyUnitState from './EmptyUnitState.vue'
import { portfolioV4Api, type StockDetail } from '@/api/portfolioV4'

const props = defineProps<{ code: string }>()
const detail = ref<StockDetail | null>(null)
const loading = ref(false)

async function load(code: string) {
  if (!code) return
  loading.value = true
  try {
    const res: any = await portfolioV4Api.getStockDetail(code)
    // 兼容三种返回形态: {data:{code,...}} / {code,...} 直接对象 / {success,data:...}
    let d: any = res
    if (d && typeof d === 'object') {
      if (d.data && typeof d.data === 'object' && (d.data.code || d.data.name)) d = d.data
      else if (!d.code && d.payload) d = d.payload  // unit envelope 兜底
    }
    detail.value = d && d.code ? d : null
    if (!detail.value) {
      console.warn('[v4-stock] detail empty for', code, 'raw:', res)
    }
  } catch (e) {
    console.error('[v4-stock] load failed', code, e)
    detail.value = null
  } finally { loading.value = false }
}

const fv = computed(() => detail.value?.forward_view || {})
const ff = computed(() => detail.value?.five_forces || {})
const cfd = computed(() => (detail.value?.five_forces || {}).cross_force_dynamics || {})
const topSells = computed(() => (detail.value?.sell_discipline || []).slice(0, 3))
const ratingType = computed(() => ratingTypeFor(detail.value?.rating))
const hitLabel = computed(() => ({ hit: '✅ 命中', miss: '❌ 未命中', flat: '➖ 持平', tracking: '🔍 追踪中' } as Record<string, string>)[detail.value?.historical_alpha?.hit || ''] || detail.value?.historical_alpha?.hit || '-')
const hitType = computed(() => ({ hit: 'success', miss: 'danger', flat: 'info' } as Record<string, any>)[detail.value?.historical_alpha?.hit || ''] || 'info')

// 仓位计算器
const capInput = ref(100)
const posAmount = computed(() => (capInput.value || 0) * (detail.value?.industry_weight_pct ?? 0) / 100)
const posShares = computed(() => {
  const price = detail.value?.price_at_judgment ?? 0
  if (!price) return 0
  return Math.round(posAmount.value * 10000 / price)
})
// 止损线 — 从 sell_discipline 解析"硬止损 ¥X"(优先)或匹配 元/¥
const stopPrice = computed(() => {
  const sells = detail.value?.sell_discipline || []
  // 优先找含"硬止损"的条目
  const hard = sells.find((s: any) => typeof s === 'string' && /硬止损/.test(s)) || sells[0] || ''
  const m = String(hard).match(/[¥$]?\s*(\d{2,6}(?:\.\d+)?)/)
  return m ? parseFloat(m[1]) : null
})

// 警告框
const alertClass = computed(() => {
  const r = detail.value?.rating || ''
  if (/买入|增持/.test(r)) return 'sdt-alert-bull'
  if (/减持|卖出|清仓/.test(r)) return 'sdt-alert-bear'
  return 'sdt-alert-neutral'
})
const alertHeadline = computed(() => {
  const r = detail.value?.rating || ''
  const price = detail.value?.price_at_judgment
  const range = detail.value?.entry_price_range || []
  if (/买入|增持/.test(r) && price && range[1] && price > range[1]) return '当前价高于买点上沿'
  if (/减持|卖出/.test(r)) return '建议减持/退出'
  if (/持有/.test(r) && /反对加仓|不加仓/.test(r)) return '当前不建议新建仓+不加仓'
  return '注意风险边界'
})
const alertBody = computed(() => {
  const r = detail.value?.rating || ''
  const price = detail.value?.price_at_judgment
  const stop = stopPrice.value
  if (/持有/.test(r) && /反对加仓|不加仓/.test(r)) {
    return `现价 ¥${price ?? '-'} 缺乏安全边际。已持有者：持有但绝不加仓，严守止损线 ¥${stop ?? '-'}。新介入仅限组合 ≤ 5% 试探。`
  }
  if (/买入|增持/.test(r)) {
    return `建议在 ${fmtRange(detail.value?.entry_price_range)} 区间分批建仓，单次不超过组合 ${detail.value?.industry_weight_pct ?? '配比'}%。跌破止损 ¥${stop ?? '-'} 立即清仓。`
  }
  if (/减持|卖出/.test(r)) {
    return '基本面/估值已不支持持仓，建议在反弹时分批退出，避免一次性全清造成被动。'
  }
  return '中性持有，关注 trigger_monitor 中的关键指标，触发立即调整。'
})

// "为什么"5 行精炼(从已有字段提炼)
// D0-8 类型安全: 字段在新 schema 是 dict, 旧 schema 是 string, 需兼容
function _safeStr(x: any, max = 100): string {
  if (x == null) return ''
  if (typeof x === 'string') return x.slice(0, max)
  if (typeof x === 'object') {
    // dict → 提取常见 'core_logic'/'summary'/'implication' 字段, 否则 JSON 化
    const v = x.core_logic || x.summary || x.implication || x.thesis || x.value || ''
    if (typeof v === 'string') return v.slice(0, max)
    return JSON.stringify(x).slice(0, max)
  }
  return String(x).slice(0, max)
}
function _safeSplit(x: any, sep: string | RegExp): string[] {
  const s = _safeStr(x, 500)
  return s ? s.split(sep) : ['']
}

const whyChain = computed(() => {
  const cp = detail.value?.chain_positioning
  if (!cp) return ''
  return `${cp.industry} → ${cp.chokepoint} → 排 #${cp.my_rank}（${cp.my_why ? _safeStr(cp.my_why, 50) + '…' : ''}）`
})
const whyMoat = computed(() => {
  const f = detail.value?.five_forces
  if (!f) return ''
  const rating = f.moat_rating || '?'
  const dur = _safeSplit(f.moat_durability, '；')[0].slice(0, 30)
  const weak = _safeSplit(f.cross_force_dynamics?.weakest_link, '—')[0].slice(0, 40)
  return `护城河 ${rating}（${dur}） · 最弱一环：${weak}`
})
const whyValuation = computed(() => {
  const v = detail.value?.valuation_basis
  return _safeSplit(v, /[;。]/)[0].slice(0, 100)
})
const whyWorst = computed(() => {
  return _safeStr(detail.value?.worst_case || detail.value?.downside, 100)
})
const whyExpGap = computed(() => {
  return _safeStr(detail.value?.expectation_gap, 100)
})
const whyTam = computed(() => {
  const vc = (detail.value as any)?.value_creation
  return vc?.tam_penetration ? _safeStr(vc.tam_penetration, 110) : ''
})
const whyRoic = computed(() => {
  const vc = (detail.value as any)?.value_creation
  return vc?.roic_vs_wacc ? _safeStr(vc.roic_vs_wacc, 110) : ''
})
const whyDcf = computed(() => {
  return _safeStr((detail.value as any)?.dcf_intrinsic, 110)
})
// 🎯 可操作结论(2026-06-14 三维: 好公司ROIC × 好价格PE × 好未来PEG/增速) — verified 数据驱动
const actionableVerdict = computed(() => {
  const vc = (detail.value as any)?.value_creation
  return vc?.actionable_verdict || null
})
const actionableText = computed(() => {
  const av = actionableVerdict.value
  if (!av) return ''
  const parts: string[] = []
  if (av.verified_price != null) parts.push(`现价¥${av.verified_price}`)
  if (av.verified_pe != null) parts.push(`PE ${av.verified_pe}x`)
  if (av.roic_range || av.roic_pct) parts.push(`ROIC ${av.roic_range || av.roic_pct}%`)
  if (av.net_income_growth_pct != null) parts.push(`净利增速 ${av.net_income_growth_pct}%`)
  if (av.forward_peg) parts.push(`forward PEG ${av.forward_peg}`)
  if (av.industry_wacc != null) parts.push(`行业WACC ${av.industry_wacc}%`)
  return parts.join(' · ')
})

// evidence 按 group 分组(数据采集 Step 1 用)
const groupedEvidence = computed(() => {
  const ev = detail.value?.evidence || []
  const groups: Record<string, any[]> = {}
  for (const e of ev) {
    const g = (e as any).group || '其他'
    if (!groups[g]) groups[g] = []
    groups[g].push(e)
  }
  return groups
})
const evidenceCoverage = computed(() => {
  const ev = detail.value?.evidence || []
  return {
    verified: ev.filter((e: any) => e.status === 'verified').length,
    estimated: ev.filter((e: any) => e.status === 'estimated').length,
    missing: ev.filter((e: any) => e.status === 'missing').length,
  }
})

// 辩论双栏配对
const debatePairs = computed(() => {
  const rounds = detail.value?.debate_rounds || []
  const map: Record<number, { round: number; bull?: string; bear?: string }> = {}
  for (const r of rounds) {
    const rd = r.round || 0
    if (!map[rd]) map[rd] = { round: rd }
    // bull 与 bear 独立判断(不能用 else if 链 — 同一 round 对象可能同时含 bull+bear)
    if (r.side === 'bull' && r.thesis) map[rd].bull = r.thesis
    else if (typeof r.bull === 'string') map[rd].bull = r.bull
    else if (r.bull?.thesis) map[rd].bull = r.bull.thesis
    if (r.side === 'bear' && r.thesis) map[rd].bear = r.thesis
    else if (typeof r.bear === 'string') map[rd].bear = r.bear
    else if (r.bear?.thesis) map[rd].bear = r.bear.thesis
  }
  return Object.values(map).filter(p => p.bull || p.bear).sort((a, b) => a.round - b.round)
})

function fmtRange(r?: number[]) { return r && r.length === 2 ? `¥${r[0]} - ¥${r[1]}` : '-' }
// 反向DCF / 多方法交叉 (D0-8 valuation 升级)
const rdcf = computed(() => {
  const v: any = detail.value?.valuation_basis
  // 优先从 valuation_basis(dict) 取, fallback 到 spawn 出的字段
  if (v && typeof v === 'object' && (v.market_implied_assumptions || v.reverse_dcf)) {
    return v.reverse_dcf || v
  }
  return (detail.value as any)?.reverse_dcf || null
})
const vcc = computed(() => (detail.value as any)?.valuation_cross_check || null)
function verdictCls(v?: string): string {
  if (!v) return ''
  if (/超越|超过|超出/.test(v)) return 'verdict-positive'
  if (/达不到|低于|缺/.test(v)) return 'verdict-negative'
  return 'verdict-neutral'
}
// 目标价: 数字→加¥; 已带¥/HK$前缀的字符串→原样; null→区间法
function fmtTarget(t: any): string {
  if (t == null) return '区间法'
  if (typeof t === 'number') return `¥${t}`
  const s = String(t)
  return /^[¥$]|HK\$|US\$/.test(s) ? s : `¥${s}`
}
function scnLabel(n?: string) { return ({ base: '基准', bull: '乐观', bear: '悲观' } as Record<string, string>)[n || ''] || n }
function moatType(r?: string): any { return ({ '宽': 'success', '中上': 'success', '中': 'info', '中下': 'warning', '窄': 'danger' } as Record<string, any>)[r || ''] || 'info' }
function ratingTypeFor(r?: string): any {
  if (!r) return 'info'
  if (/买入|增持/.test(r)) return 'success'
  if (/减持|卖出/.test(r)) return 'danger'
  return 'info'
}
function ffLevelClass(text?: string): string {
  if (!text) return 'sdt-ff-level'
  if (/极高|高|中高|中偏强|中偏高/.test(text)) return 'sdt-ff-level sdt-ff-high'
  if (/中(?!偏)/.test(text)) return 'sdt-ff-level sdt-ff-mid'
  if (/低|弱|极低/.test(text)) return 'sdt-ff-level sdt-ff-low'
  return 'sdt-ff-level'
}
function evidenceTagType(s?: string): any {
  if (s === 'verified') return 'success'
  if (s === 'estimated') return 'warning'
  if (s === 'missing') return 'info'
  return 'info'
}
function extractWeakestForce(weak?: string): string {
  if (!weak) return '?'
  // 例如 "买方议价力(4/5)是护城河上限..." → "买方议价"
  const m = weak.match(/^([\u4e00-\u9fa5]+(?:议价|威胁|竞争))/)
  return m ? m[1] : weak.slice(0, 6)
}

watch(() => props.code, (c) => { if (c) load(c) }, { immediate: true })
</script>

<style scoped>
.sdt-loading { padding: 20px; }
.card { border: 1px solid #ebeef5; border-radius: 8px; background: #fff; padding: 16px; margin-bottom: 14px; }

/* 头部 */
.sdt-head-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.sdt-title { font-size: 20px; font-weight: 700; color: #303133; }
.sdt-code { font-size: 14px; color: #909399; font-weight: 400; margin-left: 6px; }
.sdt-industry { font-size: 13px; color: #2f4f8f; font-weight: 500; }
.sdt-tags { display: inline-flex; align-items: center; gap: 8px; }
.sdt-credit-tag { display: inline-block; background: #eef2ff; color: #4f46e5; font-size: 13px; font-weight: 600; padding: 3px 12px; border-radius: 14px; }

/* ① 操作建议 */
.sdt-action { background: linear-gradient(135deg, #fff7e6 0%, #fff 100%); border: 2px solid #ffd591; }
.sdt-action-title { color: #d46b08; font-size: 16px; font-weight: 700; }
.sdt-action-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 14px; }
.sdt-action-cell { display: flex; flex-direction: column; align-items: center; padding: 10px; background: rgba(255,255,255,0.6); border-radius: 6px; text-align: center; }
.sdt-action-label { color: #8c6e00; font-size: 12px; margin-bottom: 4px; }
.sdt-action-val { color: #303133; font-size: 18px; font-weight: 700; }
.sdt-action-stop { color: #cf1322; }
.sdt-pos-calc { background: #fffbe6; border-radius: 8px; padding: 12px; font-size: 14px; line-height: 2; margin-bottom: 12px; }
.sdt-pos-calc b { color: #d46b08; }
.sdt-pos-input { width: 80px; padding: 3px 6px; border: 1px solid #ffd591; border-radius: 4px; font-size: 13px; }
.sdt-pos-note { display: block; font-size: 12px; color: #bfbfbf; margin-top: 4px; }
.sdt-action-alert { padding: 10px 12px; border-radius: 6px; font-size: 14px; margin-bottom: 12px; line-height: 1.7; }
.sdt-alert-bull { background: #f6ffed; border-left: 3px solid #67c23a; color: #2f6627; }
.sdt-alert-bear { background: #fff1f0; border-left: 3px solid #cf1322; color: #a8071a; }
.sdt-alert-neutral { background: #fff7e6; border-left: 3px solid #faad14; color: #874d00; }
.sdt-action-sells { background: #fef0f0; border-radius: 6px; padding: 10px 14px; }
.sdt-action-sells-label { color: #c45656; font-weight: 600; font-size: 13px; }
.sdt-action-sells ol { padding-left: 22px; margin-top: 6px; line-height: 1.8; font-size: 13px; color: #6a3030; }

/* ② 为什么 5 行精炼 */
.sdt-why { border-left: 4px solid #67c23a; }
.sdt-why-title { color: #2f6627; font-size: 16px; font-weight: 700; }
.sdt-why-oneliner { background: #f6ffed; padding: 12px 14px; border-radius: 6px; font-size: 15.5px; font-weight: 600; color: #1d2129; line-height: 1.7; margin-bottom: 14px; }
.sdt-why-icon { font-size: 18px; margin-right: 6px; }
.sdt-why-points { list-style: none; padding: 0; }
.sdt-why-points li { padding: 10px 0; border-bottom: 1px dashed #f0f0f0; font-size: 14px; line-height: 1.7; color: #4e5969; display: flex; align-items: flex-start; gap: 10px; }
.sdt-why-tag { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; flex-shrink: 0; min-width: 80px; text-align: center; }
.sdt-tag-chain { background: #eef2ff; color: #2f4f8f; }
.sdt-tag-moat { background: #fff7e6; color: #d46b08; }
.sdt-tag-val { background: #f6ffed; color: #2f6627; }
.sdt-tag-worst { background: #fff1f0; color: #a8071a; }
.sdt-tag-gap { background: #ecf5ff; color: #2f54eb; }
/* 辅助标签栏 */
.sdt-why-aux { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #f0f0f0; }
/* 🎯 可操作结论(三维 verified) */
.sdt-actionable { margin-top: 14px; padding: 12px 14px; background: linear-gradient(135deg, #fff7e6 0%, #fff 100%); border: 1px solid #ffd591; border-radius: 8px; }
.sdt-actionable-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sdt-actionable-tag { font-size: 12px; font-weight: 700; color: #fff; background: #fa8c16; padding: 2px 8px; border-radius: 4px; }
.sdt-actionable-stance { font-size: 15px; color: #d46b08; }
.sdt-actionable-data { margin-top: 8px; font-size: 13px; color: #595959; font-family: monospace; }
.sdt-actionable-reason { margin: 8px 0 0; font-size: 13px; color: #434343; line-height: 1.6; }
.sdt-actionable-correction { margin: 6px 0 0; font-size: 12.5px; color: #c41d7f; line-height: 1.6; }
.sdt-aux-card { padding: 10px; border-radius: 6px; }
.sdt-aux-reflection { background: #ecf5ff; border-left: 3px solid #409eff; }
.sdt-aux-cred { background: #eef2ff; border-left: 3px solid #4f46e5; }
.sdt-aux-alpha { background: #f0f9eb; border-left: 3px solid #67c23a; }
.sdt-aux-label { font-size: 12px; font-weight: 700; color: #909399; display: block; margin-bottom: 4px; }
.sdt-aux-card p { font-size: 13px; line-height: 1.6; color: #4e5969; margin: 2px 0; }
.sdt-aux-sub { font-size: 12px !important; color: #909399 !important; margin-top: 4px !important; }

/* ③ 支撑分析 */
.sdt-section-title { font-weight: 600; color: #303133; margin-bottom: 8px; font-size: 14px; }
.sdt-support-desc { font-size: 12.5px; color: #909399; margin-bottom: 8px; line-height: 1.6; }
.sdt-step-title { font-weight: 600; color: #303133; font-size: 14px; }
.sdt-step-tag { margin-left: 8px; }
.sdt-step-desc { font-size: 12.5px; color: #909399; margin: 6px 0 10px 0; line-height: 1.6; padding: 6px 10px; background: #fafafa; border-left: 2px solid #e4e7ed; border-radius: 2px; }
.sdt-substep { border: 1px solid #ebeef5; border-radius: 6px; margin: 8px 0; }
.sdt-substep summary { padding: 8px 12px; cursor: pointer; font-weight: 600; font-size: 13px; color: #303133; background: #fafafa; border-radius: 6px; }
.sdt-substep[open] summary { border-bottom: 1px solid #ebeef5; }
.sdt-substep > p, .sdt-substep > details, .sdt-substep > div, .sdt-substep > table { margin: 8px 12px; }
.sdt-empty { color: #c0c4cc; font-style: italic; }

.sdt-evidence-list { padding-left: 0; list-style: none; font-size: 12.5px; line-height: 1.8; }
.sdt-evidence-list li { padding: 4px 0; border-bottom: 1px dashed #f5f7fa; }
.sdt-evidence-src { color: #909399; font-size: 11.5px; margin-left: 6px; }
.sdt-used-tag { margin: 0 4px; }
.sdt-unused-tag { margin: 0 4px; opacity: 0.6; }

/* forward_view 6 维多维推演 */
.sdt-fv-6d { margin-top: 12px; padding: 10px 12px; background: #f5f7fa; border-radius: 6px; border-left: 3px solid #2f4f8f; }
.sdt-fv-6d-title { font-weight: 700; color: #2f4f8f; margin-bottom: 8px; font-size: 13px; }
.sdt-fv-6d-row { font-size: 13px; line-height: 1.7; margin: 4px 0; color: #4e5969; }

/* 3 方风险辩论展示 */
.sdt-risk-summary { padding: 8px 12px; background: #fafafa; border-radius: 6px; margin-bottom: 8px; }
.sdt-risk-summary p { font-size: 13px; line-height: 1.7; margin: 4px 0; }
.sdt-risk-adopted { background: #f6ffed; padding: 6px 8px; border-radius: 4px; border-left: 2px solid #67c23a; margin: 6px 0; }
.sdt-risk-rejected { background: #fff1f0; padding: 6px 8px; border-radius: 4px; border-left: 2px solid #cf1322; margin: 6px 0; }
.sdt-data-status { color: #909399; font-size: 11.5px; font-style: italic; margin-top: 4px; }
.sdt-sentiment-detail { background: #f5f7fa; padding: 8px 10px; border-radius: 4px; font-size: 13px; line-height: 1.7; }
.sdt-sentiment-detail p { margin: 3px 0; }
.sdt-sentiment-sub { margin-top: 6px; }

/* Step 1 evidence 分组展示 */
.sdt-evi-group { margin: 12px 0; border: 1px solid #ebeef5; border-radius: 6px; overflow: hidden; }
.sdt-evi-group-head { background: #fafafa; padding: 8px 12px; font-size: 13px; color: #303133; display: flex; justify-content: space-between; align-items: center; }
.sdt-evi-group-head b { color: #2f4f8f; }
.sdt-evi-group-count { color: #909399; font-size: 12px; }
.sdt-evi-group .sdt-evidence-list { padding: 8px 12px; }

/* 五力表(原型同款) */
.sdt-moat-synthesis { background: #f5f7fa; padding: 10px 14px; border-left: 3px solid #67c23a; border-radius: 4px; font-size: 13.5px; line-height: 1.8; color: #4e5969; }
.sdt-ff-table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 10px 0; }
.sdt-ff-table td { border: 1px solid #f0f0f0; padding: 8px 12px; }
.sdt-ff-name { width: 25%; background: #fafafa; font-weight: 600; color: #303133; }
.sdt-ff-level { line-height: 1.6; }
.sdt-ff-high { color: #cf1322; font-weight: 600; background: rgba(207, 19, 34, 0.04); }
.sdt-ff-mid { color: #d46b08; font-weight: 500; }
.sdt-ff-low { color: #67c23a; font-weight: 500; }
.sdt-cfd-block { margin: 10px 0; font-size: 13px; line-height: 1.8; }
.sdt-cfd-block ol { padding-left: 22px; margin-top: 4px; }
.sdt-cfd-block ol li { margin: 4px 0; color: #4e5969; }
.sdt-weakest { background: #fff1f0; padding: 10px 12px; border-left: 3px solid #cf1322; border-radius: 4px; font-size: 13.5px; color: #a8071a; line-height: 1.7; }
.sdt-key-risk { background: #fff7e6; padding: 8px 12px; border-left: 3px solid #faad14; border-radius: 4px; font-size: 13px; color: #874d00; }
.sdt-mon-details { margin-top: 10px; border: 1px solid #ebeef5; border-radius: 6px; }
.sdt-mon-details summary { padding: 8px 12px; cursor: pointer; font-size: 13px; color: #909399; background: #fafafa; border-radius: 6px; }
.sdt-mon-details ul, .sdt-mon-details > p, .sdt-mon-details > table { padding: 8px 16px; font-size: 12.5px; line-height: 1.8; color: #606266; }

/* 产业链卡位（嵌入竞争分析师） */
.sdt-chain-flow { font-size: 13px; color: #4e5969; padding: 6px 0; line-height: 2; }
.sdt-chain-node { background: #eef2ff; padding: 3px 9px; border-radius: 12px; color: #2f4f8f; font-weight: 600; font-size: 12.5px; }
.sdt-chain-rank { background: #67c23a; color: #fff; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 12.5px; }
.sdt-chain-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.sdt-chain-table th { background: #fafafa; padding: 6px 10px; text-align: left; border-bottom: 1px solid #ebeef5; font-weight: 600; color: #909399; font-size: 11.5px; }
.sdt-chain-table td { padding: 8px 10px; border-bottom: 1px solid #f5f7fa; vertical-align: top; }
.sdt-chain-self { background: #f0f9eb; }
.sdt-chain-rk { display: inline-block; background: #909399; color: #fff; border-radius: 12px; padding: 1px 8px; font-size: 11px; }
.sdt-chain-rk-self { display: inline-block; background: #67c23a; color: #fff; border-radius: 12px; padding: 1px 8px; font-size: 11px; font-weight: 700; }
.sdt-chain-why { color: #606266; max-width: 240px; }

/* director thesis */
.sdt-thesis-text { font-size: 14px; color: #4e5969; line-height: 1.8; white-space: pre-wrap; padding: 10px 12px; background: #f5f7fa; border-radius: 6px; }
.sdt-thesis-grid p { font-size: 13px; line-height: 1.7; margin: 4px 0; color: #606266; }
.sdt-thesis-valuation { background: #f0f9eb; border-left: 3px solid #67c23a; padding: 10px 12px; border-radius: 4px; font-size: 13px; line-height: 1.7; color: #5a6a4f; }

/* forward_view */
.sdt-fv-trigger { background: #fef3e6; padding: 8px; border-radius: 4px; margin-bottom: 8px; font-size: 13px; line-height: 1.8; }
.sdt-fv-scn { font-size: 13px; line-height: 1.8; margin-bottom: 8px; }
.sdt-scn { margin: 3px 0; font-size: 12.5px; }

/* critic */
.sdt-rev-tag { margin: 0 4px; }
.sdt-cred-chals { padding-left: 22px; line-height: 1.8; font-size: 13px; }
.sdt-cred-chals li { margin: 4px 0; color: #4e5969; }

/* 辩论双栏 */
.sdt-debate-block { margin: 10px 0; padding: 10px; background: #fafafa; border-radius: 6px; }
.sdt-debate-round-tag { font-size: 13px; font-weight: 700; color: #303133; margin-bottom: 8px; }
.sdt-duel { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.sdt-bull-side { background: #f6ffed; border-radius: 6px; padding: 10px; }
.sdt-bear-side { background: #fff1f0; border-radius: 6px; padding: 10px; }
.sdt-side-tag { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-bottom: 6px; }
.sdt-bull-tag { background: #67c23a; color: #fff; }
.sdt-bear-tag { background: #cf1322; color: #fff; }
.sdt-bull-side p, .sdt-bear-side p { font-size: 12.5px; line-height: 1.7; color: #4e5969; }

/* 历史/风险 */
.sdt-alpha-meta { font-size: 11px; color: #909399; margin-top: 6px; }
.sdt-risk-block, .sdt-sell-block { margin: 10px 0; }
.sdt-risk { margin: 3px; }
.sdt-sell-block ol { padding-left: 22px; line-height: 1.9; font-size: 13px; }

.sdt-anchor { border-left: 4px solid #722ed1; }
.sdt-anchor-title { color: #722ed1; }
.sdt-anchor-q { font-size: 13px; color: #606266; font-style: italic; margin: 6px 0; }
.sdt-anchor-honest { font-size: 13px; color: #303133; margin: 6px 0; line-height: 1.6; }
.sdt-anchor-dist { font-size: 12.5px; color: #4e5969; margin: 6px 0; line-height: 1.6; }
.sdt-anchor-risk { font-size: 12.5px; color: #c45656; margin: 6px 0; line-height: 1.6; }
.sdt-anchor-fix { font-size: 13px; color: #67c23a; margin: 6px 0; line-height: 1.6; background:#f6ffed; padding:8px; border-radius:6px; }

.sdt-rdcf-block { background: #f5f7ff; border-left: 3px solid #5b6dde; padding: 10px 12px; border-radius: 6px; margin: 8px 0; }
.sdt-rdcf-title { font-weight: 600; color: #5b6dde; font-size: 13px; margin-bottom: 6px; }
.sdt-rdcf-price { font-size: 12.5px; color: #303133; margin: 4px 0; }
.sdt-rdcf-implied { font-size: 12.5px; color: #c45656; margin: 6px 0; line-height: 1.6; }
.sdt-rdcf-reality { font-size: 12.5px; color: #67c23a; margin: 6px 0; line-height: 1.6; }
.sdt-rdcf-table { width: 100%; font-size: 12px; border-collapse: collapse; margin: 8px 0; background:#fff; border-radius:4px; overflow:hidden; }
.sdt-rdcf-table th { background: #ecf0fb; color: #303133; padding: 6px 8px; text-align: left; font-weight: 600; }
.sdt-rdcf-table td { padding: 6px 8px; border-bottom: 1px solid #f0f2f5; vertical-align: top; }
.sdt-rdcf-table tr.verdict-positive { background: #f6ffed; }
.sdt-rdcf-table tr.verdict-negative { background: #fef0f0; }
.sdt-verdict-tag { font-size: 11px; padding: 1px 6px; border-radius: 4px; font-weight: 600; }
.sdt-verdict-tag.verdict-positive { background: #67c23a; color: #fff; }
.sdt-verdict-tag.verdict-negative { background: #f56c6c; color: #fff; }
.sdt-verdict-tag.verdict-neutral { background: #909399; color: #fff; }
.sdt-rdcf-conclusion { font-size: 13px; color: #303133; margin-top: 8px; padding: 6px 10px; background: #fff; border-radius: 4px; line-height: 1.6; }
.sdt-vcc-block { background: #fff7e6; border-left: 3px solid #faad14; padding: 10px 12px; border-radius: 6px; margin: 8px 0; }
.sdt-vcc-row { font-size: 12.5px; color: #4e5969; margin: 4px 0; line-height: 1.6; }
.sdt-vcc-divergence { font-size: 12.5px; color: #c45656; margin-top: 6px; padding: 6px; background: #fff; border-radius: 4px; line-height: 1.6; }
.sdt-vfull { margin-top: 10px; }
.sdt-vfull summary { font-size: 12px; color: #909399; cursor: pointer; }
.sdt-vfull-text { white-space: pre-wrap; font-size: 12px; color: #4e5969; line-height: 1.7; padding: 8px; background: #fafafa; border-radius: 4px; max-height: 400px; overflow-y: auto; }
</style>
