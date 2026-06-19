<template>
  <div class="sfr">
    <!-- Loading -->
    <div v-if="loading" class="sfr-loading">
      <el-skeleton :rows="12" animated />
    </div>

    <template v-else-if="detail && detail.code">
      <!-- Hero Header -->
      <header class="sfr-hero">
        <div class="sfr-hero-main">
          <h1 class="sfr-hero-title">
            {{ detail.name }}
            <span class="sfr-hero-code">{{ detail.code }}</span>
          </h1>
          <div class="sfr-hero-meta">
            <el-tag v-if="detail.industry" type="info" effect="plain">{{ detail.industry }}</el-tag>
            <el-tag :type="ratingType" effect="dark" size="large">{{ detail.rating || '待评' }}</el-tag>
            <span v-if="detail.credibility?.critic_score != null" class="sfr-hero-score">
              评审 {{ detail.credibility.critic_score }}分 {{ detail.credibility.final_verdict }}
            </span>
          </div>
        </div>
        <div class="sfr-hero-kpi">
          <div class="sfr-kpi-item">
            <span class="sfr-kpi-label">当前价</span>
            <span class="sfr-kpi-val">¥{{ payload.action_plan?.current_price ?? detail.price_at_judgment ?? '-' }}</span>
          </div>
          <div class="sfr-kpi-item">
            <span class="sfr-kpi-label">目标价</span>
            <span class="sfr-kpi-val sfr-kpi-green">{{ fmtTarget(detail.target_price) }}</span>
          </div>
          <div class="sfr-kpi-item">
            <span class="sfr-kpi-label">买点区间</span>
            <span class="sfr-kpi-val">{{ fmtRange(detail.entry_price_range) }}</span>
          </div>
          <div class="sfr-kpi-item">
            <span class="sfr-kpi-label">止损</span>
            <span class="sfr-kpi-val sfr-kpi-red">¥{{ stopPrice ?? '-' }}</span>
          </div>
          <div class="sfr-kpi-item">
            <span class="sfr-kpi-label">置信度</span>
            <span class="sfr-kpi-val">{{ ((payload.verdict?.confidence ?? 0) * 100).toFixed(0) }}%</span>
          </div>
        </div>
        <div class="sfr-hero-gen">
          生成于 {{ detail.stock_unit?.generated_at?.slice(0, 10) || '-' }} · v{{ detail.stock_unit?.version ?? '-' }}
          <el-button size="small" text type="primary" @click="router.back()">← 返回</el-button>
        </div>
      </header>

      <!-- Layout: TOC + Content -->
      <div class="sfr-body">
        <!-- Sidebar TOC -->
        <aside class="sfr-toc">
          <nav>
            <div class="sfr-toc-title">目录</div>
            <a v-for="s in tocSections" :key="s.id" :href="'#' + s.id"
               :class="['sfr-toc-link', { active: activeSection === s.id }]"
               @click.prevent="scrollTo(s.id)">
              {{ s.icon }} {{ s.label }}
            </a>
          </nav>
        </aside>

        <!-- Main Content -->
        <main class="sfr-main">

          <!-- §1 核心结论 -->
          <section id="sec-verdict" class="sfr-section">
            <h2 class="sfr-h2">📌 核心结论</h2>
            <div v-if="payload.verdict" class="sfr-verdict-card">
              <div class="sfr-verdict-stance" :class="stanceColorCls">
                {{ payload.verdict.stance }}
              </div>
              <p class="sfr-verdict-summary">{{ payload.verdict.summary }}</p>
              <p v-if="payload.verdict.confidence_reason" class="sfr-verdict-conf">
                <b>置信度推导：</b>{{ payload.verdict.confidence_reason }}
              </p>
            </div>
            <div v-if="payload.thesis" class="sfr-thesis">
              <b>核心论述：</b>{{ payload.thesis }}
            </div>

            <!-- 三维评分框架：好公司 × 好价格 × 好未来 -->
            <div v-if="payload.three_dimension" class="sfr-3d">
              <div class="sfr-3d-title">🎯 三维评分框架</div>
              <div class="sfr-3d-grid">
                <div v-for="(v, k) in payload.three_dimension" :key="k" class="sfr-3d-cell" :class="dimRateCls(String(v))">
                  <div class="sfr-3d-dim">{{ dim3Label(String(k)) }}</div>
                  <div class="sfr-3d-rate">{{ dim3Rate(String(v)) }}</div>
                  <div class="sfr-3d-note">{{ dim3Note(String(v)) }}</div>
                </div>
              </div>
            </div>
          </section>

          <!-- §2 操作计划 -->
          <section id="sec-action" class="sfr-section">
            <h2 class="sfr-h2">💼 操作计划</h2>
            <div v-if="payload.action_plan" class="sfr-action-grid">
              <div class="sfr-action-item sfr-action-immediate">
                <span class="sfr-action-label">即时操作</span>
                <p>{{ payload.action_plan.immediate_action }}</p>
              </div>
              <div v-if="payload.action_plan.buy_back_zones?.length" class="sfr-action-item">
                <span class="sfr-action-label">买入区间</span>
                <ul>
                  <li v-for="(z, i) in payload.action_plan.buy_back_zones" :key="i">{{ typeof z === 'string' ? z : JSON.stringify(z) }}</li>
                </ul>
              </div>
              <div v-if="payload.action_plan.trim_zones?.length" class="sfr-action-item">
                <span class="sfr-action-label">减仓区间</span>
                <ul>
                  <li v-for="(z, i) in payload.action_plan.trim_zones" :key="i">{{ typeof z === 'string' ? z : JSON.stringify(z) }}</li>
                </ul>
              </div>
              <div v-if="payload.action_plan.stop_loss" class="sfr-action-item sfr-action-stop">
                <span class="sfr-action-label">止损规则</span>
                <p v-if="typeof payload.action_plan.stop_loss === 'string'">{{ payload.action_plan.stop_loss }}</p>
                <div v-else>
                  <p v-for="(v, k) in payload.action_plan.stop_loss" :key="k"><b>{{ k }}：</b>{{ v }}</p>
                </div>
              </div>
              <div v-if="payload.action_plan.monitoring_signals?.length" class="sfr-action-item">
                <span class="sfr-action-label">监控信号</span>
                <ol>
                  <li v-for="(s, i) in payload.action_plan.monitoring_signals" :key="i">{{ s }}</li>
                </ol>
              </div>
            </div>
          </section>

          <!-- §3 估值体系 -->
          <section id="sec-valuation" class="sfr-section">
            <h2 class="sfr-h2">💰 估值体系</h2>
            <!-- 估值推导链 -->
            <div v-if="payload.valuation_basis" class="sfr-val-card">
              <h3 class="sfr-h3">估值推导链</h3>
              <p v-if="payload.valuation_basis.core_logic"><b>核心逻辑：</b>{{ payload.valuation_basis.core_logic }}</p>
              <p v-if="payload.valuation_basis.price_derivation"><b>价格推导：</b>{{ payload.valuation_basis.price_derivation }}</p>
              <p v-if="payload.valuation_basis.consensus_target"><b>市场一致目标：</b>{{ payload.valuation_basis.consensus_target }}</p>
              <!-- 反向DCF -->
              <div v-if="payload.valuation_basis.reverse_dcf" class="sfr-rdcf">
                <h4>🔄 反向 DCF</h4>
                <div v-for="(v, k) in payload.valuation_basis.reverse_dcf" :key="k" class="sfr-rdcf-row">
                  <b>{{ k }}：</b><span>{{ v }}</span>
                </div>
              </div>
              <!-- 三情景估值 -->
              <div v-if="payload.valuation_basis.scenarios" class="sfr-scenarios">
                <h4>🎯 三情景估值</h4>
                <div v-for="(v, k) in payload.valuation_basis.scenarios" :key="k" class="sfr-scn-row">
                  <span class="sfr-scn-name">{{ k }}</span>
                  <span class="sfr-scn-val">{{ typeof v === 'string' ? v : JSON.stringify(v) }}</span>
                </div>
              </div>
            </div>

            <!-- 敏感性矩阵 -->
            <div v-if="payload.sensitivity_matrix_3x3" class="sfr-val-card">
              <h3 class="sfr-h3">📊 敏感性矩阵 3×3</h3>
              <p class="sfr-matrix-axes"><b>轴：</b>{{ payload.sensitivity_matrix_3x3.axes }}</p>
              <table v-if="payload.sensitivity_matrix_3x3.matrix" class="sfr-matrix-table">
                <thead>
                  <tr>
                    <th>情景</th>
                    <th>FY26净利(亿)</th>
                    <th>合理PE</th>
                    <th>合理价</th>
                    <th>备注</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(v, k) in payload.sensitivity_matrix_3x3.matrix" :key="k">
                    <td class="sfr-matrix-key">{{ k }}</td>
                    <td>{{ v.FY26_net_yi ?? '-' }}</td>
                    <td>{{ v.fair_pe ?? '-' }}x</td>
                    <td class="sfr-matrix-price">¥{{ v.fair_price ?? '-' }}</td>
                    <td>{{ v.comment }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-if="payload.sensitivity_matrix_3x3.weighted_avg" class="sfr-matrix-avg">
                <b>加权平均：</b>{{ payload.sensitivity_matrix_3x3.weighted_avg }}
              </p>
              <p v-if="payload.sensitivity_matrix_3x3.key_finding" class="sfr-matrix-finding">
                ⚠️ {{ payload.sensitivity_matrix_3x3.key_finding }}
              </p>
            </div>

            <!-- 可比路径量化 -->
            <div v-if="payload.comparable_path_quantified" class="sfr-val-card">
              <h3 class="sfr-h3">📐 可比路径量化</h3>
              <div v-for="(v, k) in payload.comparable_path_quantified" :key="k" class="sfr-comp-row">
                <b>{{ k }}：</b>
                <span v-if="typeof v === 'string'">{{ v }}</span>
                <span v-else-if="Array.isArray(v)">{{ v.join('；') }}</span>
                <pre v-else class="sfr-comp-pre">{{ JSON.stringify(v, null, 2) }}</pre>
              </div>
            </div>

            <!-- 同业锚定 peer_anchor -->
            <div v-if="payload.peer_anchor" class="sfr-val-card">
              <h3 class="sfr-h3">🔗 同业锚定</h3>
              <table class="sfr-matrix-table">
                <thead><tr><th>对标公司</th><th>锚定参考</th></tr></thead>
                <tbody>
                  <tr v-for="(v, k) in peerAnchorRows" :key="k">
                    <td class="sfr-matrix-key">{{ k }}</td>
                    <td>{{ v }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-if="payload.peer_anchor.note" class="sfr-matrix-finding">📌 {{ payload.peer_anchor.note }}</p>
            </div>
          </section>

          <!-- §4 产品拆解 -->
          <section v-if="payload.product_subdivision_deep || payload.product_decomposition" id="sec-product" class="sfr-section">
            <h2 class="sfr-h2">🏭 产品业务拆解</h2>
            <template v-if="payload.product_subdivision_deep">
              <div v-for="(info, segment) in payload.product_subdivision_deep" :key="segment" class="sfr-prod-card">
                <div class="sfr-prod-name">{{ segment }}</div>
                <div class="sfr-prod-grid">
                  <div v-for="(val, field) in info" :key="field" class="sfr-prod-field">
                    <span class="sfr-prod-label">{{ field }}</span>
                    <span class="sfr-prod-val">{{ val }}</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- 产品分部利润表 product_decomposition（自下而上加总验证） -->
            <div v-if="payload.product_decomposition" class="sfr-decomp">
              <h3 class="sfr-h3">🧮 产品分部利润表（自下而上加总验证）</h3>
              <p v-if="payload.product_decomposition.method" class="sfr-decomp-meta">
                {{ payload.product_decomposition.method }}
                <span v-if="payload.product_decomposition.as_of">· {{ payload.product_decomposition.as_of }}</span>
              </p>
              <table v-if="payload.product_decomposition.lines?.length" class="sfr-matrix-table">
                <thead>
                  <tr><th>产品线</th><th>营收(亿)</th><th>占比</th><th>毛利率</th><th>净利率</th><th>净利贡献(亿)</th><th>备注</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(ln, i) in payload.product_decomposition.lines" :key="i">
                    <td class="sfr-matrix-key">{{ ln.line }}</td>
                    <td>{{ ln.revenue_2027E_yi ?? ln.revenue_yi ?? '-' }}</td>
                    <td>{{ ln.revenue_share_pct != null ? ln.revenue_share_pct + '%' : '-' }}</td>
                    <td>{{ ln.gross_margin_pct != null ? ln.gross_margin_pct + '%' : '-' }}</td>
                    <td>{{ ln.net_margin_pct != null ? ln.net_margin_pct + '%' : '-' }}</td>
                    <td class="sfr-matrix-price">{{ ln.net_contribution_yi ?? '-' }}</td>
                    <td class="sfr-decomp-comment">{{ ln.comment }}</td>
                  </tr>
                </tbody>
              </table>
              <div class="sfr-decomp-totals">
                <span v-if="payload.product_decomposition.total_revenue_2027E_yi">总营收 <b>{{ payload.product_decomposition.total_revenue_2027E_yi }}</b> 亿</span>
                <span v-if="payload.product_decomposition.total_net_2027E_yi_calculated">加总净利 <b>{{ payload.product_decomposition.total_net_2027E_yi_calculated }}</b> 亿</span>
                <span v-if="payload.product_decomposition.total_net_2027E_yi_with_subsidy">含补贴 <b>{{ payload.product_decomposition.total_net_2027E_yi_with_subsidy }}</b> 亿</span>
              </div>
              <p v-if="payload.product_decomposition.comment" class="sfr-matrix-finding">⚠️ {{ payload.product_decomposition.comment }}</p>
              <p v-if="payload.product_decomposition.implication_for_director" class="sfr-decomp-impl">
                <b>🎩 对总监的含义：</b>{{ payload.product_decomposition.implication_for_director }}
              </p>
            </div>
          </section>

          <!-- §5 五力分析 -->
          <section v-if="payload.five_forces" id="sec-fiveforces" class="sfr-section">
            <h2 class="sfr-h2">🏰 波特五力 + 护城河</h2>
            <div class="sfr-ff-card">
              <p v-if="payload.five_forces.moat_rating" class="sfr-ff-moat">
                护城河评级：<b>{{ payload.five_forces.moat_rating }}</b>
              </p>
              <p v-if="payload.five_forces.weakest_link" class="sfr-ff-weak">
                最弱一环：{{ payload.five_forces.weakest_link }}
              </p>
              <table v-if="payload.five_forces.five_forces_summary" class="sfr-ff-table">
                <tr v-for="(v, k) in payload.five_forces.five_forces_summary" :key="k">
                  <td class="sfr-ff-name">{{ forceLabel(String(k)) }}</td>
                  <td>{{ v }}</td>
                </tr>
              </table>
            </div>
          </section>

          <!-- §5.5 上游供应链递归深挖（供方议价力上溯：本股成本风险 + 更优上游标的） -->
          <section v-if="upstreamDrill.length" id="sec-upstream" class="sfr-section">
            <h2 class="sfr-h2">⛏️ 上游供应链深挖（供需链：本股成本风险 + 未被 price-in 的上游机会）</h2>
            <p class="sfr-appendix-desc">本股最关键的受限投入往上游逐层钻——既是成本端隐患，那个供需最紧且市场未发现的环节也可能是更优的上游卡位标的。</p>
            <div v-for="(dc, i) in upstreamDrill" :key="i" class="sfr-drill">
              <div class="sfr-drill-flow">
                <span class="sfr-drill-start">{{ dc.start }}</span>
                <template v-for="(node, j) in (dc.chain || [])" :key="j">
                  <span class="sfr-drill-arrow">→</span>
                  <span class="sfr-drill-node">L{{ node.depth ?? j + 1 }} {{ node.node }}</span>
                </template>
              </div>
              <p v-if="dc.deepest_alpha" class="sfr-drill-alpha">🎯 最深环节：{{ dc.deepest_alpha }}</p>
              <table v-if="(dc.chain || []).length" class="sfr-matrix-table" style="margin-top:8px">
                <thead><tr><th>层</th><th>上游环节</th><th>供需缺口</th><th>扩产周期</th><th>玩家/集中度</th><th>涨价力</th><th>发现度</th><th>受益标的</th></tr></thead>
                <tbody>
                  <tr v-for="(node, j) in dc.chain" :key="j">
                    <td>L{{ node.depth ?? j + 1 }}</td>
                    <td class="sfr-matrix-key">{{ node.node }}</td>
                    <td>{{ node.supply_demand_gap }}</td>
                    <td>{{ node.expansion_cycle }}</td>
                    <td>{{ node.global_players }}</td>
                    <td>{{ node.pricing_power }}</td>
                    <td>{{ node.discovery_level }}</td>
                    <td>{{ [...(node.beneficiaries_a||[]), ...(node.beneficiaries_qdii||[])].join('、') || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- §6 前瞻推演 6维 -->
          <section v-if="payload.forward_view_6dim" id="sec-forward" class="sfr-section">
            <h2 class="sfr-h2">🔭 前瞻推演（6维）</h2>
            <div class="sfr-fwd-grid">
              <div v-for="(v, k) in payload.forward_view_6dim" :key="k" class="sfr-fwd-item">
                <div class="sfr-fwd-label">{{ fwdLabel(String(k)) }}</div>
                <div class="sfr-fwd-val">{{ typeof v === 'string' ? v : JSON.stringify(v) }}</div>
              </div>
            </div>
          </section>

          <!-- §7 多空辩论 -->
          <section v-if="debatePairs.length || payload.bear_data_correction" id="sec-debate" class="sfr-section">
            <h2 class="sfr-h2">⚔️ 多空辩论<span v-if="debatePairs.length">（{{ debatePairs.length }} 轮）</span></h2>
            <div v-for="(pair, i) in debatePairs" :key="i" class="sfr-debate-round">
              <div class="sfr-debate-tag">第 {{ pair.round }} 轮{{ pair.round === debatePairs.length ? ' · 终局' : '' }}</div>
              <div class="sfr-debate-duel">
                <div class="sfr-debate-bull">
                  <div class="sfr-debate-side-tag bull">🐂 多头</div>
                  <p>{{ pair.bull }}</p>
                </div>
                <div class="sfr-debate-bear">
                  <div class="sfr-debate-side-tag bear">🐻 空头</div>
                  <p>{{ pair.bear }}</p>
                </div>
              </div>
            </div>
            <!-- 空头数据纠错（事实核查，避免被错误论据误导） -->
            <div v-if="payload.bear_data_correction" class="sfr-bear-correction">
              <div class="sfr-bear-correction-head">🔍 空头论据事实核查</div>
              <p>{{ payload.bear_data_correction }}</p>
            </div>
          </section>

          <!-- §8 三方风险辩论 -->
          <section v-if="payload.risk_consensus_from_3way" id="sec-risk" class="sfr-section">
            <h2 class="sfr-h2">⚖️ 三方风险辩论</h2>
            <div class="sfr-risk-grid">
              <div class="sfr-risk-item sfr-risk-agg">
                <div class="sfr-risk-role">🔥 激进派</div>
                <p>{{ payload.risk_consensus_from_3way.aggressive }}</p>
              </div>
              <div class="sfr-risk-item sfr-risk-safe">
                <div class="sfr-risk-role">🛡️ 保守派</div>
                <p>{{ payload.risk_consensus_from_3way.safe }}</p>
              </div>
              <div class="sfr-risk-item sfr-risk-neutral">
                <div class="sfr-risk-role">⚖️ 中立派</div>
                <p>{{ payload.risk_consensus_from_3way.neutral }}</p>
              </div>
              <div class="sfr-risk-item sfr-risk-decision">
                <div class="sfr-risk-role">🎩 总监决策</div>
                <p>{{ payload.risk_consensus_from_3way.director_decision }}</p>
              </div>
            </div>
          </section>

          <!-- §9 锚定自查 -->
          <section v-if="payload.anchoring_check" id="sec-anchor" class="sfr-section">
            <h2 class="sfr-h2">🧭 锚定 vs 预期差自查</h2>
            <div class="sfr-anchor-card">
              <p v-if="payload.anchoring_check.honest_answer">
                <b>诚实回答：</b>{{ payload.anchoring_check.honest_answer }}
              </p>
              <p v-if="payload.anchoring_check.value_trap_risk" class="sfr-anchor-risk">
                <b>价值陷阱风险：</b>{{ payload.anchoring_check.value_trap_risk }}
              </p>
              <p v-if="payload.anchoring_check.corrected_framing" class="sfr-anchor-fix">
                <b>✅ 已修正框架：</b>{{ payload.anchoring_check.corrected_framing }}
              </p>
            </div>
          </section>

          <!-- §10 价值创造验证 -->
          <section v-if="payload.value_creation_verified" id="sec-value" class="sfr-section">
            <h2 class="sfr-h2">🏭 价值创造验证</h2>
            <div class="sfr-vc-grid">
              <div v-for="(v, k) in payload.value_creation_verified" :key="k" class="sfr-vc-item">
                <div class="sfr-vc-label">{{ k }}</div>
                <div class="sfr-vc-val">
                  <template v-if="typeof v === 'string' || typeof v === 'number'">{{ v }}</template>
                  <template v-else-if="v && typeof v === 'object'">
                    <pre class="sfr-vc-pre">{{ JSON.stringify(v, null, 2) }}</pre>
                  </template>
                </div>
              </div>
            </div>
          </section>

          <!-- §11 评审过程 -->
          <section v-if="payload.critic_evaluation" id="sec-critic" class="sfr-section">
            <h2 class="sfr-h2">🎓 Critic 评审过程</h2>
            <div class="sfr-critic-card">
              <div class="sfr-critic-scores">
                <span v-if="payload.critic_evaluation.critic_v1_score">
                  V1: {{ payload.critic_evaluation.critic_v1_score }}分 ({{ payload.critic_evaluation.critic_v1_verdict }})
                </span>
                <span>→</span>
                <span class="sfr-critic-final">
                  最终: {{ payload.critic_evaluation.final_score }}分 ({{ payload.critic_evaluation.final_verdict }})
                </span>
              </div>
              <p v-if="payload.critic_evaluation.summary" class="sfr-critic-summary">
                {{ payload.critic_evaluation.summary }}
              </p>
              <div v-if="payload.critic_evaluation['4_views']" class="sfr-critic-views">
                <h4>四视角评审</h4>
                <div v-for="(view, name) in payload.critic_evaluation['4_views']" :key="name" class="sfr-critic-view">
                  <b>{{ name }}：</b>
                  <span>{{ typeof view === 'string' ? view : JSON.stringify(view) }}</span>
                </div>
              </div>
            </div>
          </section>

          <!-- §12 价值创造 -->
          <section v-if="payload.value_creation" id="sec-value-creation" class="sfr-section">
            <h2 class="sfr-h2">💎 价值创造分析</h2>
            <div class="sfr-vc-grid">
              <div v-for="(v, k) in payload.value_creation" :key="k" class="sfr-vc-item">
                <div class="sfr-vc-label">{{ k }}</div>
                <div class="sfr-vc-val">
                  <template v-if="isScalar(v)">{{ v }}</template>
                  <JsonTree v-else :value="v" />
                </div>
              </div>
            </div>
          </section>

          <!-- §13 生意质量与定性 -->
          <section v-if="hasQualitative" id="sec-qualitative" class="sfr-section">
            <h2 class="sfr-h2">🏢 生意质量与定性判断</h2>
            <div class="sfr-qual-grid">
              <div v-if="payload.business_quality" class="sfr-qual-item">
                <div class="sfr-qual-label">生意质量</div>
                <p>{{ payload.business_quality }}</p>
              </div>
              <div v-if="payload.position_nature" class="sfr-qual-item">
                <div class="sfr-qual-label">投资 or 交易</div>
                <p>{{ payload.position_nature }}</p>
              </div>
              <div v-if="payload.expectation_gap" class="sfr-qual-item">
                <div class="sfr-qual-label">预期差</div>
                <p>{{ scalarText(payload.expectation_gap) }}</p>
              </div>
              <div v-if="payload.chokepoint_score" class="sfr-qual-item">
                <div class="sfr-qual-label">卡位评分</div>
                <p>{{ scalarText(payload.chokepoint_score) }}</p>
              </div>
              <div v-if="payload.discovery_level || payload.discovery" class="sfr-qual-item">
                <div class="sfr-qual-label">市场发现度</div>
                <p>{{ scalarText(payload.discovery_level || payload.discovery) }}</p>
              </div>
              <div v-if="payload.cycle_positioning && isScalar(payload.cycle_positioning)" class="sfr-qual-item">
                <div class="sfr-qual-label">周期定位</div>
                <p>{{ scalarText(payload.cycle_positioning) }}</p>
              </div>
            </div>
            <!-- 周期定位（结构化：阶段/信号/H2动态/策略含义） -->
            <div v-if="payload.cycle_positioning && !isScalar(payload.cycle_positioning)" class="sfr-cycle-card">
              <h3 class="sfr-h3">🔄 周期定位</h3>
              <p v-if="payload.cycle_positioning.phase"><b>所处阶段：</b>{{ payload.cycle_positioning.phase }}</p>
              <p v-if="payload.cycle_positioning.key_signal"><b>关键信号：</b>{{ payload.cycle_positioning.key_signal }}</p>
              <p v-if="payload.cycle_positioning.h2_dynamics"><b>下半年动态：</b>{{ payload.cycle_positioning.h2_dynamics }}</p>
              <p v-if="payload.cycle_positioning['策略含义']" class="sfr-cycle-strategy"><b>📌 策略含义：</b>{{ payload.cycle_positioning['策略含义'] }}</p>
            </div>
            <!-- 产业链卡位 -->
            <div v-if="payload.chain_positioning" class="sfr-chain-card">
              <h3 class="sfr-h3">🎯 产业链卡位</h3>
              <p v-if="payload.chain_positioning.industry">
                {{ payload.chain_positioning.industry }} → {{ payload.chain_positioning.chokepoint }} → 本股 #{{ payload.chain_positioning.my_rank ?? '?' }}
              </p>
              <table v-if="payload.chain_positioning.industry_top?.length" class="sfr-matrix-table">
                <thead><tr><th>#</th><th>标的</th><th>评级</th><th>目标价</th><th>理由</th></tr></thead>
                <tbody>
                  <tr v-for="(r, i) in payload.chain_positioning.industry_top" :key="i" :class="{ 'sfr-chain-self': r.is_self }">
                    <td>{{ r.rank }}</td><td><b>{{ r.recommended }}</b></td><td>{{ r.rating }}</td>
                    <td>{{ r.target_price_live != null ? `¥${r.target_price_live}` : '-' }}</td><td>{{ r.why }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- §14 风险与止损纪律 -->
          <section v-if="hasRisks" id="sec-risks" class="sfr-section">
            <h2 class="sfr-h2">⚠️ 风险清单与止损纪律</h2>
            <div v-if="payload.worst_case || payload.downside" class="sfr-risk-worst">
              <p v-if="payload.worst_case"><b>🧠 逆向最坏情况：</b>{{ scalarText(payload.worst_case) }}</p>
              <p v-if="payload.downside"><b>🌊 赔率与下行：</b>{{ scalarText(payload.downside) }}</p>
            </div>
            <div v-if="payload.risks?.length" class="sfr-risk-list">
              <div class="sfr-list-head">主要风险（{{ payload.risks.length }} 项）</div>
              <ol><li v-for="(r, i) in payload.risks" :key="i">{{ scalarText(r) }}</li></ol>
            </div>
            <!-- ST/退市风险量化（高危红线） -->
            <div v-if="payload.st_risk_quantified" class="sfr-st-risk">
              <div class="sfr-st-risk-head">🚨 ST / 退市风险量化</div>
              <p v-if="payload.st_risk_quantified.rule"><b>规则：</b>{{ payload.st_risk_quantified.rule }}</p>
              <p v-if="payload.st_risk_quantified.threshold"><b>清仓阈值：</b>{{ payload.st_risk_quantified.threshold }}</p>
              <JsonTree v-if="!payload.st_risk_quantified.rule && !payload.st_risk_quantified.threshold" :value="payload.st_risk_quantified" />
            </div>
            <div v-if="payload.tail_risk_joint_scenario_modeling || payload.tail_risk" class="sfr-risk-list">
              <div class="sfr-list-head">尾部风险联合情景</div>
              <JsonTree :value="payload.tail_risk_joint_scenario_modeling || payload.tail_risk" />
            </div>
            <!-- 证伪触发器（信号 → 含义 双列表格） -->
            <div v-if="falsificationRows.length" class="sfr-risk-list">
              <div class="sfr-list-head">🎯 证伪触发器（信号 → 应对）</div>
              <table class="sfr-matrix-table">
                <thead><tr><th>触发信号</th><th>应对含义</th></tr></thead>
                <tbody>
                  <tr v-for="(t, i) in falsificationRows" :key="i">
                    <td>{{ t.signal }}</td>
                    <td :class="triggerCls(t.implication)">{{ t.implication }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else-if="payload.falsification_triggers" class="sfr-risk-list">
              <div class="sfr-list-head">证伪触发器</div>
              <JsonTree :value="payload.falsification_triggers" />
            </div>
            <div v-if="payload.sell_discipline?.length" class="sfr-sell-list">
              <div class="sfr-list-head">止损纪律全集（{{ payload.sell_discipline.length }} 条）</div>
              <ol><li v-for="(s, i) in payload.sell_discipline" :key="i">{{ scalarText(s) }}</li></ol>
            </div>
          </section>

          <!-- §15 分析师与舆情 -->
          <section v-if="hasAnalysts" id="sec-analysts" class="sfr-section">
            <h2 class="sfr-h2">👔 分析师与舆情</h2>
            <div v-if="payload.analysts" class="sfr-analyst-block">
              <div v-for="(txt, name) in payload.analysts" :key="name" class="sfr-analyst-item">
                <div class="sfr-analyst-name">{{ analystLabel(String(name)) }}</div>
                <div class="sfr-analyst-text">
                  <template v-if="isScalar(txt)">{{ txt }}</template>
                  <JsonTree v-else :value="txt" />
                </div>
              </div>
            </div>
            <div v-if="payload.sentiment_view || payload.sentiment_full" class="sfr-analyst-block">
              <div class="sfr-analyst-item">
                <div class="sfr-analyst-name">📰 舆情分析</div>
                <p v-if="payload.sentiment_view" class="sfr-analyst-text">{{ payload.sentiment_view }}</p>
                <JsonTree v-if="payload.sentiment_full" :value="payload.sentiment_full" />
              </div>
            </div>
          </section>

          <!-- §16 数据采集证据 -->
          <section v-if="payload.evidence?.length" id="sec-evidence" class="sfr-section">
            <h2 class="sfr-h2">📥 数据采集证据（{{ payload.evidence.length }} 条）</h2>
            <ul class="sfr-evidence-list">
              <li v-for="(e, i) in payload.evidence" :key="i">
                <el-tag :type="evidenceTag(e.status)" size="small" effect="plain">{{ e.status || '?' }}</el-tag>
                {{ e.claim }}
                <span v-if="e.source" class="sfr-evidence-src">— {{ e.source }}</span>
              </li>
            </ul>
          </section>

          <!-- §17 历史准确率 -->
          <section v-if="payload.historical_alpha" id="sec-history" class="sfr-section">
            <h2 class="sfr-h2">📈 历史判断准确率（结果闭环）</h2>
            <div class="sfr-reflect-card">
              <p v-if="payload.historical_alpha.hit"><b>命中情况：</b>{{ hitLabel }}</p>
              <p v-if="payload.historical_alpha.alpha_note">{{ payload.historical_alpha.alpha_note }}</p>
              <JsonTree :value="payload.historical_alpha" />
            </div>
          </section>

          <!-- §18 反思 -->
          <section v-if="payload.reflection || memoryList.length || payload.v9_to_v10_revisions?.length" id="sec-reflection" class="sfr-section">
            <h2 class="sfr-h2">🔄 版本反思与记忆</h2>
            <div v-if="payload.reflection" class="sfr-reflect-card">
              <p v-if="payload.reflection.what_changed"><b>本次变化：</b>{{ payload.reflection.what_changed }}</p>
              <p v-if="payload.reflection.why_changed"><b>为何改：</b>{{ payload.reflection.why_changed }}</p>
              <p v-if="payload.reflection.self_check"><b>自检：</b>{{ payload.reflection.self_check }}</p>
            </div>
            <!-- 已引用记忆（经验/教训/模式） -->
            <div v-if="memoryList.length" class="sfr-memory">
              <div class="sfr-list-head">🧠 已引用记忆（{{ memoryList.length }} 条经验/教训/模式）</div>
              <ul class="sfr-memory-list">
                <li v-for="(m, i) in memoryList" :key="i">{{ m }}</li>
              </ul>
            </div>
            <!-- 版本修订记录 -->
            <div v-if="payload.v9_to_v10_revisions?.length" class="sfr-memory">
              <div class="sfr-list-head">📝 版本修订记录</div>
              <ol class="sfr-revisions">
                <li v-for="(r, i) in payload.v9_to_v10_revisions" :key="i">{{ r }}</li>
              </ol>
            </div>
          </section>

          <!-- §19 完整数据附录（兜底：所有未被上方章节消费的字段，零丢失） -->
          <section v-if="leftoverEntries.length" id="sec-appendix" class="sfr-section">
            <h2 class="sfr-h2">📦 完整数据附录</h2>
            <p class="sfr-appendix-desc">以下为未在上方专题章节展示的全部原始字段，确保分析产出零信息丢失。</p>
            <el-collapse>
              <el-collapse-item v-for="[k, v] in leftoverEntries" :key="k" :name="k">
                <template #title><span class="sfr-appendix-key">{{ k }}</span></template>
                <JsonTree :value="v" />
              </el-collapse-item>
            </el-collapse>
          </section>

        </main>
      </div>
    </template>

    <div v-else class="sfr-empty">
      <el-empty description="未找到该个股完整分析报告" />
      <el-button type="primary" @click="router.back()">返回</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { portfolioV4Api, type StockDetail } from '@/api/portfolioV4'
import JsonTree from './JsonTree.vue'

// codeProp：嵌入 V4Overview tab 时由父级传入；独立路由页则取 route.params
const props = defineProps<{ codeProp?: string }>()
const route = useRoute()
const router = useRouter()
const code = computed(() => props.codeProp || (route.params.code as string))
const detail = ref<StockDetail | null>(null)
const rawEnvelope = ref<any>(null)
const loading = ref(false)

const payload = computed(() => {
  if (rawEnvelope.value?.payload) return rawEnvelope.value.payload
  const d: any = detail.value || {}
  return {
    ...d,
    verdict: d.verdict || d.verdict_v2 || null,
    sensitivity_matrix_3x3: d.sensitivity_matrix_3x3 || d.sensitivity_matrix || null,
    product_subdivision_deep: d.product_subdivision_deep || d.product_subdivision || null,
    forward_view_6dim: d.forward_view_6dim || d.forward_view || null,
    risk_consensus_from_3way: d.risk_consensus_from_3way || d.risk_debate_summary || null,
    comparable_path_quantified: d.comparable_path_quantified || null,
    value_creation_verified: d.value_creation_verified || d.value_creation || null,
  }
})

async function load(c: string) {
  if (!c) return
  loading.value = true
  try {
    const res: any = await portfolioV4Api.getStockDetail(c)
    let d: any = res
    if (d && typeof d === 'object') {
      if (d.data && typeof d.data === 'object') d = d.data
    }
    if (d && d.payload) {
      rawEnvelope.value = d
      detail.value = d.payload
    } else if (d && d.code) {
      rawEnvelope.value = null
      detail.value = d
    } else {
      detail.value = null
    }
  } catch (e) {
    console.error('[StockFullReport] load failed', c, e)
    detail.value = null
  } finally {
    loading.value = false
  }
}

// TOC sections
const tocSections = computed(() => {
  const secs = [
    { id: 'sec-verdict', icon: '📌', label: '核心结论' },
    { id: 'sec-action', icon: '💼', label: '操作计划' },
    { id: 'sec-valuation', icon: '💰', label: '估值体系' },
  ]
  if (payload.value.product_subdivision_deep || payload.value.product_decomposition) secs.push({ id: 'sec-product', icon: '🏭', label: '产品拆解' })
  if (payload.value.five_forces) secs.push({ id: 'sec-fiveforces', icon: '🏰', label: '五力分析' })
  if (upstreamDrill.value.length) secs.push({ id: 'sec-upstream', icon: '⛏️', label: '上游深挖' })
  if (payload.value.forward_view_6dim) secs.push({ id: 'sec-forward', icon: '🔭', label: '前瞻推演' })
  if (debatePairs.value.length || payload.value.bear_data_correction) secs.push({ id: 'sec-debate', icon: '⚔️', label: '多空辩论' })
  if (payload.value.risk_consensus_from_3way) secs.push({ id: 'sec-risk', icon: '⚖️', label: '风险辩论' })
  if (payload.value.anchoring_check) secs.push({ id: 'sec-anchor', icon: '🧭', label: '锚定自查' })
  if (payload.value.value_creation_verified) secs.push({ id: 'sec-value', icon: '🏭', label: '价值创造(验证)' })
  if (payload.value.critic_evaluation) secs.push({ id: 'sec-critic', icon: '🎓', label: '评审过程' })
  if (payload.value.value_creation) secs.push({ id: 'sec-value-creation', icon: '💎', label: '价值创造' })
  if (hasQualitative.value) secs.push({ id: 'sec-qualitative', icon: '🏢', label: '生意质量' })
  if (hasRisks.value) secs.push({ id: 'sec-risks', icon: '⚠️', label: '风险与止损' })
  if (hasAnalysts.value) secs.push({ id: 'sec-analysts', icon: '👔', label: '分析师/舆情' })
  if (payload.value.evidence?.length) secs.push({ id: 'sec-evidence', icon: '📥', label: '数据证据' })
  if (payload.value.historical_alpha) secs.push({ id: 'sec-history', icon: '📈', label: '历史准确率' })
  if (payload.value.reflection || memoryList.value.length || payload.value.v9_to_v10_revisions?.length) secs.push({ id: 'sec-reflection', icon: '🔄', label: '反思与记忆' })
  if (leftoverEntries.value.length) secs.push({ id: 'sec-appendix', icon: '📦', label: '完整数据附录' })
  return secs
})

// Scrollspy
const activeSection = ref('')
let observer: IntersectionObserver | null = null

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeSection.value = entry.target.id
        }
      }
    },
    { rootMargin: '-80px 0px -60% 0px', threshold: 0.1 }
  )
})

onUnmounted(() => { observer?.disconnect() })

watch(loading, (v) => {
  if (!v) {
    setTimeout(() => {
      document.querySelectorAll('.sfr-section').forEach((el) => {
        observer?.observe(el)
      })
    }, 100)
  }
})

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  activeSection.value = id
}

// Debate pairs
// 上游供应链深挖：payload 顶层 或 five_forces 内（供方议价力分析师产出）
const upstreamDrill = computed<any[]>(() => {
  const p: any = payload.value || {}
  return p.upstream_drill || p.five_forces?.upstream_drill || []
})

const debatePairs = computed(() => {
  const rounds = payload.value.debate_rounds || []
  const map: Record<number, { round: number; bull?: string; bear?: string }> = {}
  for (const r of rounds) {
    const rd = r.round || 0
    if (!map[rd]) map[rd] = { round: rd }
    if (r.side === 'bull' && r.thesis) map[rd].bull = r.thesis
    else if (typeof r.bull === 'string') map[rd].bull = r.bull
    else if (r.bull?.thesis) map[rd].bull = r.bull.thesis
    if (r.side === 'bear' && r.thesis) map[rd].bear = r.thesis
    else if (typeof r.bear === 'string') map[rd].bear = r.bear
    else if (r.bear?.thesis) map[rd].bear = r.bear.thesis
  }
  return Object.values(map).filter(p => p.bull || p.bear).sort((a, b) => a.round - b.round)
})

// Helpers
const stopPrice = computed(() => {
  const sp = payload.value.action_plan?.stop_loss
  if (!sp) return null
  const str = typeof sp === 'string' ? sp : JSON.stringify(sp)
  const m = str.match(/[¥$]?\s*(\d{2,6}(?:\.\d+)?)/)
  return m ? parseFloat(m[1]) : null
})

const stanceColorCls = computed(() => {
  const s = payload.value.verdict?.stance || ''
  if (/减|卖|回避|清仓/.test(s)) return 'neg'
  if (/加|买|建仓|增持/.test(s)) return 'pos'
  return 'neutral'
})

const ratingType = computed(() => {
  const r = detail.value?.rating || ''
  if (/买入|增持/.test(r)) return 'success'
  if (/减持|卖出/.test(r)) return 'danger'
  return 'info'
})

function fmtRange(r?: number[]) { return r && r.length === 2 ? `¥${r[0]} - ¥${r[1]}` : '-' }
function fmtTarget(t: any): string {
  if (t == null) return '区间法'
  if (typeof t === 'number') return `¥${t}`
  return /^[¥$]/.test(String(t)) ? String(t) : `¥${t}`
}
function forceLabel(k: string): string {
  const map: Record<string, string> = { entry: '🚧 进入威胁', substitute: '🔄 替代威胁', buyer: '🛒 买方议价', supplier: '📦 供方议价', rivalry: '⚔️ 同业竞争' }
  return map[k] || k
}
function fwdLabel(k: string): string {
  const map: Record<string, string> = {
    market_regime: '📈 市场风格',
    liquidity: '💧 流动性',
    cycle_position: '🔄 行业周期',
    beta_correlation: '⚡ β相关性',
    beta_correlation_detail: '⚡ β详情',
    comparable_anchor: '📊 对标锚点',
    comparable_dynamic: '📊 对标动态',
    pricing_power: '🛒 定价能力',
    pricing_power_dynamic: '🛒 定价能力详情',
  }
  return map[k] || k
}
// 三维评分框架（好公司/好价格/好未来）：值形如 "△(ROE11.3一般...)"，拆评级符号 + 备注
function dim3Label(k: string): string {
  const map: Record<string, string> = { '好公司': '🏢 好公司', '好价格': '💰 好价格', '好未来': '🔮 好未来' }
  return map[k] || k
}
function dim3Rate(v: string): string {
  const m = String(v).match(/^\s*([○◎●△×✓✗√!]+|[A-D][+-]?)/)
  return m ? m[1] : String(v).slice(0, 2)
}
function dim3Note(v: string): string {
  return String(v).replace(/^\s*([○◎●△×✓✗√!]+|[A-D][+-]?)\s*[（(]?/, '').replace(/[）)]\s*$/, '')
}
function dimRateCls(v: string): string {
  const r = dim3Rate(v)
  if (/[●◎√✓A]/.test(r)) return 'dim-good'
  if (/[×✗D!]/.test(r)) return 'dim-bad'
  return 'dim-mid'  // △ 等中性
}
function triggerCls(impl?: string): string {
  if (!impl) return ''
  if (/加仓|上调|增持|确认|验证/.test(impl)) return 'sfr-trigger-bull'
  if (/减仓|下调|减至|清仓|减持|触发/.test(impl)) return 'sfr-trigger-bear'
  return ''
}
function analystLabel(k: string): string {
  const map: Record<string, string> = {
    financial: '📊 财务分析师',
    competitive: '🏰 竞争分析师',
    valuation: '💰 估值分析师',
    sentiment: '📰 舆情分析师',
  }
  return map[k] || k
}
function evidenceTag(s?: string): any {
  if (s === 'verified') return 'success'
  if (s === 'estimated') return 'warning'
  return 'info'
}
function isScalar(v: any): boolean {
  return v == null || ['string', 'number', 'boolean'].includes(typeof v)
}
function scalarText(v: any): string {
  if (v == null) return '-'
  if (isScalar(v)) return String(v)
  if (Array.isArray(v)) return v.map(scalarText).join('；')
  // dict → 取常见摘要字段
  const o: any = v
  return o.summary || o.core_logic || o.thesis || o.value || JSON.stringify(o)
}

const hitLabel = computed(() => {
  const h = payload.value.historical_alpha?.hit || ''
  return ({ hit: '✅ 命中', miss: '❌ 未命中', flat: '➖ 持平', tracking: '🔍 追踪中' } as Record<string, string>)[h] || h || '-'
})

const hasQualitative = computed(() => {
  const p = payload.value
  return !!(p.business_quality || p.position_nature || p.expectation_gap || p.chokepoint_score
    || p.discovery_level || p.discovery || p.cycle_positioning || p.chain_positioning)
})
const hasRisks = computed(() => {
  const p = payload.value
  return !!(p.risks?.length || p.sell_discipline?.length || p.worst_case || p.downside
    || p.tail_risk_joint_scenario_modeling || p.tail_risk || p.falsification_triggers)
})
const hasAnalysts = computed(() => {
  const p = payload.value
  return !!(p.analysts || p.sentiment_view || p.sentiment_full)
})

// peer_anchor: 排除 note 字段后的对标公司行
const peerAnchorRows = computed(() => {
  const pa = payload.value.peer_anchor
  if (!pa || typeof pa !== 'object') return {}
  const out: Record<string, any> = {}
  for (const k of Object.keys(pa)) {
    if (k === 'note') continue
    out[k] = pa[k]
  }
  return out
})

// falsification_triggers: 规整为 {signal, implication} 行（兼容字符串数组）
const falsificationRows = computed<Array<{ signal: string; implication?: string }>>(() => {
  const ft = payload.value.falsification_triggers
  if (!Array.isArray(ft)) return []
  const out: Array<{ signal: string; implication?: string }> = []
  for (const t of ft) {
    if (t && typeof t === 'object' && t.signal) {
      out.push({ signal: t.signal, implication: t.implication })
    }
  }
  return out
})

// memory_used: 顶层优先，否则取 reflection.memory_used
const memoryList = computed(() => {
  const p = payload.value
  const m = p.memory_used || p.reflection?.memory_used || []
  return Array.isArray(m) ? m : []
})

// 完整数据附录：所有未被上方专题章节消费的字段，递归全展示，保证零丢失
const CONSUMED_KEYS = new Set<string>([
  // header / kpi
  'code', 'name', 'industry', 'market', 'rating', 'target_price', 'entry_price_range',
  'price_at_judgment', 'confidence', 'stock_unit', 'schema_version', 'instrument_type',
  'version', 'version_v2', 'data_status', 'data_status_overall', 'analysis_mode',
  // §核心结论
  'verdict', 'verdict_v2', 'verdict_oneliner', 'thesis',
  // §操作
  'action_plan',
  // §估值
  'valuation_basis', 'sensitivity_matrix_3x3', 'sensitivity_matrix', 'sensitivity_matrix_v2',
  'comparable_path_quantified', 'valuation_cross_check', '_valuation_cross_check', 'dcf_intrinsic',
  // §产品
  'product_subdivision_deep', 'product_subdivision', 'product_subdivision_stress_test', 'product_decomposition',
  // §五力 §前瞻 §辩论 §风险辩论 §锚定
  'five_forces', 'five_forces_summary', 'upstream_drill', 'forward_view_6dim', 'forward_view',
  'debate_rounds', 'debate_synthesis', 'risk_consensus_from_3way', 'risk_debate_summary',
  'risk_debate_full', 'risk_debate_decision', 'anchoring_check',
  // §价值创造(验证) §评审 §价值创造
  'value_creation_verified', 'critic_evaluation', 'critic_review', 'credibility', 'value_creation',
  // §生意质量
  'business_quality', 'position_nature', 'expectation_gap', 'chokepoint_score',
  'discovery_level', 'discovery', 'cycle_positioning', 'chain_positioning', 'industry_weight_pct',
  // §风险与止损
  'risks', 'sell_discipline', 'worst_case', 'downside',
  'tail_risk_joint_scenario_modeling', 'tail_risk', 'falsification_triggers',
  // §分析师/舆情 §证据 §历史 §反思
  'analysts', 'sentiment_view', 'sentiment_full', 'evidence', 'historical_alpha', 'reflection',
  // 本轮精排的高价值字段
  'three_dimension', 'peer_anchor', 'st_risk_quantified', 'bear_data_correction',
  'memory_used', 'v9_to_v10_revisions',
])

const leftoverEntries = computed(() => {
  const p = payload.value || {}
  const out: Array<[string, any]> = []
  for (const k of Object.keys(p)) {
    if (CONSUMED_KEYS.has(k)) continue
    const v = (p as any)[k]
    if (v == null || (Array.isArray(v) && v.length === 0)) continue
    out.push([k, v])
  }
  return out
})

watch(code, (c) => { if (c) load(c) }, { immediate: true })
</script>

<style scoped>
.sfr { min-height: 100vh; background: #f5f7fa; }
.sfr-loading { padding: 60px 40px; max-width: 900px; margin: 0 auto; }

/* Hero */
.sfr-hero { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; padding: 32px 40px 24px; }
.sfr-hero-main { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.sfr-hero-title { font-size: 28px; font-weight: 800; margin: 0; }
.sfr-hero-code { font-size: 16px; font-weight: 400; opacity: 0.6; margin-left: 8px; }
.sfr-hero-meta { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.sfr-hero-score { background: rgba(255,255,255,0.15); padding: 4px 14px; border-radius: 16px; font-size: 13px; font-weight: 600; }
.sfr-hero-kpi { display: flex; gap: 24px; margin-top: 20px; flex-wrap: wrap; }
.sfr-kpi-item { display: flex; flex-direction: column; align-items: center; background: rgba(255,255,255,0.08); padding: 12px 20px; border-radius: 10px; min-width: 100px; }
.sfr-kpi-label { font-size: 12px; opacity: 0.7; margin-bottom: 4px; }
.sfr-kpi-val { font-size: 18px; font-weight: 700; }
.sfr-kpi-green { color: #52c41a; }
.sfr-kpi-red { color: #ff4d4f; }
.sfr-hero-gen { margin-top: 16px; font-size: 12px; opacity: 0.5; display: flex; align-items: center; gap: 16px; }

/* Body layout */
.sfr-body { display: flex; max-width: 1400px; margin: 0 auto; padding: 24px 20px; gap: 24px; }

/* TOC */
.sfr-toc { width: 200px; flex-shrink: 0; position: sticky; top: 20px; align-self: flex-start; }
.sfr-toc nav { background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.sfr-toc-title { font-size: 13px; font-weight: 700; color: #909399; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
.sfr-toc-link { display: block; padding: 7px 10px; margin: 2px 0; border-radius: 6px; font-size: 13px; color: #606266; text-decoration: none; transition: all 0.2s; }
.sfr-toc-link:hover { background: #f5f7fa; color: #303133; }
.sfr-toc-link.active { background: #ecf5ff; color: #409eff; font-weight: 600; }

/* Main */
.sfr-main { flex: 1; min-width: 0; }
.sfr-section { background: #fff; border-radius: 12px; padding: 24px 28px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); scroll-margin-top: 20px; }
.sfr-h2 { font-size: 18px; font-weight: 700; color: #1d2129; margin: 0 0 16px 0; padding-bottom: 10px; border-bottom: 2px solid #f0f0f0; }
.sfr-h3 { font-size: 15px; font-weight: 600; color: #303133; margin: 16px 0 10px 0; }

/* §1 Verdict */
.sfr-verdict-card { background: #fafbfc; border-radius: 8px; padding: 16px; margin-bottom: 14px; }
.sfr-verdict-stance { font-size: 17px; font-weight: 700; line-height: 1.6; margin-bottom: 10px; }
.sfr-verdict-stance.pos { color: #389e0d; }
.sfr-verdict-stance.neg { color: #cf1322; }
.sfr-verdict-stance.neutral { color: #d46b08; }
.sfr-verdict-summary { font-size: 14px; color: #4e5969; line-height: 1.8; margin: 0 0 8px; }
.sfr-verdict-conf { font-size: 13px; color: #8c8c8c; line-height: 1.6; }
.sfr-thesis { font-size: 14px; color: #4e5969; line-height: 1.8; padding: 12px 14px; background: #f5f7fa; border-radius: 6px; border-left: 3px solid #409eff; }

/* §2 Action */
.sfr-action-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
.sfr-action-item { background: #fafbfc; border-radius: 8px; padding: 14px; border: 1px solid #ebeef5; }
.sfr-action-item ul, .sfr-action-item ol { padding-left: 20px; margin: 6px 0; font-size: 13px; line-height: 1.8; }
.sfr-action-item p { font-size: 13.5px; line-height: 1.7; margin: 4px 0; }
.sfr-action-label { display: block; font-size: 12px; font-weight: 700; color: #909399; margin-bottom: 6px; text-transform: uppercase; }
.sfr-action-immediate { border-left: 3px solid #409eff; }
.sfr-action-stop { border-left: 3px solid #ff4d4f; }

/* §3 Valuation */
.sfr-val-card { background: #fafbfc; border-radius: 8px; padding: 16px; margin-bottom: 14px; border: 1px solid #ebeef5; }
.sfr-val-card p { font-size: 13.5px; line-height: 1.7; margin: 6px 0; color: #4e5969; }
.sfr-rdcf { margin-top: 12px; padding: 10px 12px; background: #f0f4ff; border-radius: 6px; }
.sfr-rdcf h4 { font-size: 13px; font-weight: 700; color: #5b6dde; margin: 0 0 8px; }
.sfr-rdcf-row { font-size: 13px; line-height: 1.7; margin: 4px 0; }
.sfr-scenarios { margin-top: 12px; }
.sfr-scenarios h4 { font-size: 13px; font-weight: 700; color: #d46b08; margin: 0 0 8px; }
.sfr-scn-row { display: flex; gap: 10px; font-size: 13px; margin: 4px 0; line-height: 1.7; }
.sfr-scn-name { font-weight: 600; min-width: 60px; color: #303133; }
.sfr-scn-val { color: #4e5969; }

/* Sensitivity matrix */
.sfr-matrix-axes { font-size: 13px; color: #606266; margin-bottom: 10px; }
.sfr-matrix-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.sfr-matrix-table th { background: #f0f2f5; padding: 8px 10px; text-align: left; font-weight: 600; color: #606266; border-bottom: 2px solid #e4e7ed; }
.sfr-matrix-table td { padding: 8px 10px; border-bottom: 1px solid #f0f2f5; }
.sfr-matrix-key { font-weight: 600; color: #303133; white-space: nowrap; }
.sfr-matrix-price { font-weight: 700; color: #409eff; }
.sfr-matrix-avg { font-size: 13px; margin-top: 10px; padding: 8px; background: #ecf5ff; border-radius: 4px; color: #303133; }
.sfr-matrix-finding { font-size: 13px; margin-top: 8px; padding: 8px; background: #fff7e6; border-radius: 4px; color: #874d00; border-left: 3px solid #faad14; }

/* Comparable */
.sfr-comp-row { font-size: 13px; line-height: 1.7; margin: 6px 0; color: #4e5969; }
.sfr-comp-pre { font-size: 11.5px; background: #f5f7fa; padding: 8px; border-radius: 4px; overflow-x: auto; max-height: 200px; }

/* §4 Product */
.sfr-prod-card { background: #fafbfc; border-radius: 8px; padding: 14px; margin-bottom: 10px; border: 1px solid #ebeef5; }
.sfr-prod-name { font-size: 14px; font-weight: 700; color: #303133; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px dashed #e4e7ed; }
.sfr-prod-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; }
.sfr-prod-field { display: flex; flex-direction: column; }
.sfr-prod-label { font-size: 11.5px; color: #909399; }
.sfr-prod-val { font-size: 13px; color: #303133; font-weight: 500; }

/* §5 Five forces */
.sfr-ff-card { padding: 12px; }
.sfr-ff-moat { font-size: 15px; margin-bottom: 8px; }
.sfr-ff-weak { font-size: 13px; color: #cf1322; background: #fff1f0; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; }
.sfr-ff-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.sfr-ff-table td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.sfr-ff-name { width: 140px; font-weight: 600; color: #303133; background: #fafafa; }

/* §5.5 上游供应链深挖 */
.sfr-drill { margin-bottom: 16px; padding: 12px 14px; background: #fafbfc; border: 1px solid #ebeef5; border-radius: 8px; }
.sfr-drill-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 8px; }
.sfr-drill-start { font-size: 13px; font-weight: 700; color: #303133; background: #eef2ff; padding: 3px 10px; border-radius: 12px; }
.sfr-drill-arrow { color: #c0c4cc; font-weight: 700; }
.sfr-drill-node { font-size: 12.5px; font-weight: 600; padding: 3px 10px; border-radius: 12px; background: #f0f2f5; color: #606266; }
.sfr-drill-alpha { font-size: 13px; color: #874d00; background: #fff7e6; padding: 8px 12px; border-radius: 6px; border-left: 3px solid #faad14; margin: 6px 0; line-height: 1.6; }

/* §6 Forward */
.sfr-fwd-grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
.sfr-fwd-item { background: #f5f7fa; border-radius: 8px; padding: 12px 14px; border-left: 3px solid #2f4f8f; }
.sfr-fwd-label { font-size: 12px; font-weight: 700; color: #2f4f8f; margin-bottom: 4px; }
.sfr-fwd-val { font-size: 13px; color: #4e5969; line-height: 1.7; }

/* §7 Debate */
.sfr-debate-round { margin-bottom: 14px; padding: 12px; background: #fafbfc; border-radius: 8px; }
.sfr-debate-tag { font-size: 13px; font-weight: 700; color: #303133; margin-bottom: 10px; }
.sfr-debate-duel { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.sfr-debate-bull { background: #f6ffed; border-radius: 8px; padding: 12px; }
.sfr-debate-bear { background: #fff1f0; border-radius: 8px; padding: 12px; }
.sfr-debate-side-tag { font-size: 12px; font-weight: 700; margin-bottom: 6px; }
.sfr-debate-side-tag.bull { color: #389e0d; }
.sfr-debate-side-tag.bear { color: #cf1322; }
.sfr-debate-bull p, .sfr-debate-bear p { font-size: 13px; line-height: 1.7; color: #4e5969; margin: 0; }

/* §8 Risk debate */
.sfr-risk-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.sfr-risk-item { border-radius: 8px; padding: 14px; border: 1px solid #ebeef5; }
.sfr-risk-item p { font-size: 13px; line-height: 1.7; margin: 6px 0; color: #4e5969; }
.sfr-risk-role { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.sfr-risk-agg { border-left: 3px solid #ff4d4f; background: #fff8f8; }
.sfr-risk-safe { border-left: 3px solid #52c41a; background: #f8fff8; }
.sfr-risk-neutral { border-left: 3px solid #faad14; background: #fffdf5; }
.sfr-risk-decision { border-left: 3px solid #722ed1; background: #faf5ff; }

/* §9 Anchor */
.sfr-anchor-card { padding: 12px; }
.sfr-anchor-card p { font-size: 13.5px; line-height: 1.7; margin: 8px 0; color: #4e5969; }
.sfr-anchor-risk { background: #fff1f0; padding: 10px 12px; border-radius: 6px; color: #a8071a; }
.sfr-anchor-fix { background: #f6ffed; padding: 10px 12px; border-radius: 6px; color: #2f6627; }

/* §10 Value creation */
.sfr-vc-grid { display: grid; grid-template-columns: 1fr; gap: 10px; }
.sfr-vc-item { background: #fafbfc; border-radius: 6px; padding: 10px 14px; border: 1px solid #ebeef5; }
.sfr-vc-label { font-size: 12px; font-weight: 700; color: #909399; margin-bottom: 4px; }
.sfr-vc-val { font-size: 13px; color: #303133; line-height: 1.6; }
.sfr-vc-pre { font-size: 11.5px; background: #f5f7fa; padding: 8px; border-radius: 4px; margin: 0; overflow-x: auto; max-height: 200px; white-space: pre-wrap; }

/* §11 Critic */
.sfr-critic-card { padding: 12px; }
.sfr-critic-scores { font-size: 14px; margin-bottom: 10px; display: flex; gap: 8px; align-items: center; }
.sfr-critic-final { font-weight: 700; color: #389e0d; }
.sfr-critic-summary { font-size: 13px; color: #4e5969; line-height: 1.7; background: #f5f7fa; padding: 10px; border-radius: 6px; }
.sfr-critic-views { margin-top: 12px; }
.sfr-critic-views h4 { font-size: 13px; font-weight: 700; color: #303133; margin-bottom: 8px; }
.sfr-critic-view { font-size: 12.5px; line-height: 1.7; margin: 4px 0; color: #606266; }

/* §12 Reflection */
.sfr-reflect-card { padding: 12px; }
.sfr-reflect-card p { font-size: 13.5px; line-height: 1.7; margin: 6px 0; color: #4e5969; }

/* §13 Qualitative */
.sfr-qual-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.sfr-qual-item { background: #fafbfc; border-radius: 8px; padding: 12px 14px; border: 1px solid #ebeef5; }
.sfr-qual-label { font-size: 12px; font-weight: 700; color: #909399; margin-bottom: 6px; }
.sfr-qual-item p { font-size: 13px; line-height: 1.7; color: #4e5969; margin: 0; }
.sfr-chain-card { margin-top: 14px; padding: 12px; background: #f5f7ff; border-radius: 8px; }
.sfr-chain-card p { font-size: 13px; color: #4e5969; margin: 6px 0; }
.sfr-chain-self { background: #f0f9eb; }

/* §14 Risks */
.sfr-risk-worst { background: #fff7e6; border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; }
.sfr-risk-worst p { font-size: 13.5px; line-height: 1.7; margin: 6px 0; color: #874d00; }
.sfr-risk-list, .sfr-sell-list { margin: 12px 0; }
.sfr-list-head { font-size: 13px; font-weight: 700; color: #303133; margin-bottom: 8px; }
.sfr-risk-list ol, .sfr-sell-list ol { padding-left: 22px; line-height: 1.9; font-size: 13px; color: #4e5969; }
.sfr-sell-list { background: #fff1f0; border-radius: 8px; padding: 12px 14px; }

/* §15 Analysts */
.sfr-analyst-block { margin: 10px 0; }
.sfr-analyst-item { background: #fafbfc; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; border: 1px solid #ebeef5; }
.sfr-analyst-name { font-size: 13px; font-weight: 700; color: #303133; margin-bottom: 8px; }
.sfr-analyst-text { font-size: 13px; line-height: 1.8; color: #4e5969; white-space: pre-wrap; }

/* §16 Evidence */
.sfr-evidence-list { list-style: none; padding: 0; font-size: 12.5px; line-height: 1.9; }
.sfr-evidence-list li { padding: 6px 0; border-bottom: 1px dashed #f0f2f5; }
.sfr-evidence-src { color: #909399; font-size: 11.5px; margin-left: 6px; }

/* §19 Appendix */
.sfr-appendix-desc { font-size: 13px; color: #909399; margin-bottom: 12px; line-height: 1.6; }
.sfr-appendix-key { font-weight: 600; color: #5b6dde; font-size: 13.5px; }

/* 三维评分框架 */
.sfr-3d { margin-top: 16px; }
.sfr-3d-title { font-size: 14px; font-weight: 700; color: #303133; margin-bottom: 10px; }
.sfr-3d-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.sfr-3d-cell { border-radius: 10px; padding: 14px; text-align: center; border: 2px solid #ebeef5; }
.sfr-3d-cell.dim-good { background: #f6ffed; border-color: #b7eb8f; }
.sfr-3d-cell.dim-mid { background: #fffbe6; border-color: #ffe58f; }
.sfr-3d-cell.dim-bad { background: #fff1f0; border-color: #ffccc7; }
.sfr-3d-dim { font-size: 13px; font-weight: 700; color: #303133; margin-bottom: 8px; }
.sfr-3d-rate { font-size: 28px; font-weight: 800; line-height: 1; margin-bottom: 8px; }
.dim-good .sfr-3d-rate { color: #389e0d; }
.dim-mid .sfr-3d-rate { color: #d48806; }
.dim-bad .sfr-3d-rate { color: #cf1322; }
.sfr-3d-note { font-size: 12px; color: #606266; line-height: 1.5; }

/* 产品分部利润表 */
.sfr-decomp { margin-top: 14px; }
.sfr-decomp-meta { font-size: 12.5px; color: #909399; margin-bottom: 10px; }
.sfr-decomp-comment { color: #606266; font-size: 12px; max-width: 280px; }
.sfr-decomp-totals { display: flex; gap: 20px; flex-wrap: wrap; margin: 10px 0; font-size: 13px; color: #4e5969; }
.sfr-decomp-totals b { color: #409eff; }
.sfr-decomp-impl { font-size: 13px; margin-top: 8px; padding: 10px 12px; background: #f5f7ff; border-radius: 6px; color: #303133; line-height: 1.7; border-left: 3px solid #5b6dde; }

/* 同业锚定 note 复用 matrix-finding；周期定位卡片 */
.sfr-cycle-card { margin-top: 14px; padding: 14px; background: #f0f7ff; border-radius: 8px; border-left: 3px solid #409eff; }
.sfr-cycle-card p { font-size: 13px; line-height: 1.7; margin: 6px 0; color: #4e5969; }
.sfr-cycle-strategy { background: #fff; padding: 8px 10px; border-radius: 6px; color: #303133 !important; }

/* 空头数据纠错 */
.sfr-bear-correction { margin-top: 12px; padding: 12px 14px; background: #f0f9eb; border-radius: 8px; border-left: 3px solid #67c23a; }
.sfr-bear-correction-head { font-size: 13px; font-weight: 700; color: #2f6627; margin-bottom: 6px; }
.sfr-bear-correction p { font-size: 13px; line-height: 1.8; color: #4e5969; margin: 0; }

/* ST 风险 */
.sfr-st-risk { margin: 12px 0; padding: 14px; background: #fff1f0; border: 2px solid #ffccc7; border-radius: 8px; }
.sfr-st-risk-head { font-size: 14px; font-weight: 700; color: #cf1322; margin-bottom: 8px; }
.sfr-st-risk p { font-size: 13px; line-height: 1.7; margin: 6px 0; color: #a8071a; }

/* 证伪触发器表格 trigger 着色 */
.sfr-trigger-bull { color: #389e0d; }
.sfr-trigger-bear { color: #cf1322; }

/* 记忆与版本修订 */
.sfr-memory { margin: 14px 0; }
.sfr-memory-list, .sfr-revisions { padding-left: 22px; line-height: 1.9; font-size: 13px; color: #4e5969; }
.sfr-memory-list li { margin: 6px 0; padding: 6px 10px; background: #faf5ff; border-radius: 6px; border-left: 2px solid #722ed1; list-style: none; }
.sfr-memory-list { padding-left: 0; }
.sfr-revisions li { margin: 4px 0; }

/* Empty */
.sfr-empty { text-align: center; padding: 60px; }

/* Responsive */
@media (max-width: 900px) {
  .sfr-toc { display: none; }
  .sfr-body { padding: 12px; }
  .sfr-hero { padding: 20px; }
  .sfr-hero-kpi { gap: 10px; }
  .sfr-kpi-item { padding: 8px 12px; min-width: 80px; }
  .sfr-kpi-val { font-size: 14px; }
  .sfr-debate-duel { grid-template-columns: 1fr; }
  .sfr-risk-grid { grid-template-columns: 1fr; }
  .sfr-section { padding: 16px; }
}

/* Print */
@media print {
  .sfr-toc { display: none; }
  .sfr-hero { background: #fff; color: #000; }
  .sfr-section { break-inside: avoid; box-shadow: none; border: 1px solid #ddd; }
}
</style>
