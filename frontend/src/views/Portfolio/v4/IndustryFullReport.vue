<template>
  <div class="ifr">
    <div v-if="loading" class="ifr-loading">
      <el-skeleton :rows="12" animated />
    </div>

    <template v-else-if="detail && detail.industry">
      <!-- Hero -->
      <header class="ifr-hero">
        <div class="ifr-hero-main">
          <h1 class="ifr-hero-title">
            {{ detail.industry }}
            <span class="ifr-hero-sub">行业完整研究报告</span>
          </h1>
          <div class="ifr-hero-meta">
            <el-tag v-if="verdict.stance" :type="stanceType" effect="dark" size="large">{{ verdict.stance }}</el-tag>
            <span v-if="credScore != null" class="ifr-hero-score">评审 {{ credScore }}分 {{ cred.final_verdict }}</span>
          </div>
        </div>
        <div class="ifr-hero-kpi">
          <div v-if="verdict.vitality_level != null" class="ifr-kpi">
            <span class="ifr-kpi-label">产业活力</span>
            <span class="ifr-kpi-val ifr-kpi-green">{{ verdict.vitality_level }}/10</span>
          </div>
          <div v-if="ifm.tam_now_usd_b" class="ifr-kpi">
            <span class="ifr-kpi-label">当前 TAM</span>
            <span class="ifr-kpi-val">${{ ifm.tam_now_usd_b }}B</span>
          </div>
          <div v-if="ifm.tam_2030E_usd_b" class="ifr-kpi">
            <span class="ifr-kpi-label">2030E TAM</span>
            <span class="ifr-kpi-val ifr-kpi-green">${{ ifm.tam_2030E_usd_b }}B</span>
          </div>
          <div v-if="ifm.cagr_pct != null" class="ifr-kpi">
            <span class="ifr-kpi-label">CAGR</span>
            <span class="ifr-kpi-val">{{ ifm.cagr_pct }}%</span>
          </div>
          <div v-if="detail.investment_map?.length" class="ifr-kpi">
            <span class="ifr-kpi-label">投资标的</span>
            <span class="ifr-kpi-val">{{ detail.investment_map.length }} 个</span>
          </div>
        </div>
        <div class="ifr-hero-gen">
          生成于 {{ detail.industry_unit?.generated_at?.slice(0, 10) || '-' }} · v{{ detail.industry_unit?.version ?? '-' }}
          <el-button size="small" text type="primary" @click="router.back()">← 返回</el-button>
        </div>
      </header>

      <div class="ifr-body">
        <!-- TOC -->
        <aside class="ifr-toc">
          <nav>
            <div class="ifr-toc-title">目录</div>
            <a v-for="s in tocSections" :key="s.id" :href="'#' + s.id"
               :class="['ifr-toc-link', { active: activeSection === s.id }]"
               @click.prevent="scrollTo(s.id)">{{ s.icon }} {{ s.label }}</a>
          </nav>
        </aside>

        <main class="ifr-main">
          <!-- §1 裁决 -->
          <section id="sec-verdict" class="ifr-section">
            <h2 class="ifr-h2">📌 行业裁决</h2>
            <div class="ifr-verdict-card">
              <div class="ifr-verdict-stance" :class="stanceCls">{{ verdict.stance }}</div>
              <p v-if="verdict.direction" class="ifr-verdict-dir"><b>方向：</b>{{ verdict.direction }}</p>
              <p v-if="verdict.situation" class="ifr-verdict-text">{{ verdict.situation }}</p>
            </div>
            <div class="ifr-verdict-grid">
              <div v-if="verdict.track_quality" class="ifr-vg-item">
                <div class="ifr-vg-label">🏆 赛道质量</div><p>{{ verdict.track_quality }}</p>
              </div>
              <div v-if="verdict.cycle_position" class="ifr-vg-item">
                <div class="ifr-vg-label">🔄 周期位置</div><p>{{ verdict.cycle_position }}</p>
              </div>
              <div v-if="verdict.worst_case" class="ifr-vg-item ifr-vg-warn">
                <div class="ifr-vg-label">🧠 最坏情况</div><p>{{ verdict.worst_case }}</p>
              </div>
              <div v-if="verdict.downgrade_trigger" class="ifr-vg-item ifr-vg-warn">
                <div class="ifr-vg-label">⚠️ 降级触发</div><p>{{ verdict.downgrade_trigger }}</p>
              </div>
              <div v-if="verdict.chokepoint_conclusion" class="ifr-vg-item ifr-vg-full">
                <div class="ifr-vg-label">🎯 瓶颈结论</div><p>{{ verdict.chokepoint_conclusion }}</p>
              </div>
            </div>
            <div v-if="verdict.risks?.length" class="ifr-risks">
              <div class="ifr-list-head">主要风险（{{ verdict.risks.length }} 项）</div>
              <ol><li v-for="(r, i) in verdict.risks" :key="i">{{ r }}</li></ol>
            </div>
          </section>

          <!-- §1.5 产业链全景（横向铺全并列细分领域，按层分组平铺，瓶颈高亮） -->
          <section v-if="landscape.length" id="sec-landscape" class="ifr-section">
            <h2 class="ifr-h2">🗺️ 产业链全景（{{ landscape.length }} 个细分领域 · 🔴=瓶颈）</h2>
            <p class="ifr-appendix-desc">横向穷举本行业所有并列细分领域，红框=构成瓶颈（值得深挖），灰框=非瓶颈环节。</p>
            <div v-for="(grp, layer) in landscapeByLayer" :key="layer" class="ifr-ls-layer">
              <div class="ifr-ls-layer-name">{{ layer }}</div>
              <div class="ifr-ls-grid">
                <div v-for="(seg, i) in grp" :key="i" class="ifr-ls-card" :class="{ 'ifr-ls-bottleneck': seg.is_bottleneck }">
                  <div class="ifr-ls-seg">{{ seg.is_bottleneck ? '🔴 ' : '' }}{{ seg.segment }}</div>
                  <div class="ifr-ls-role">{{ seg.role_in_industry }}</div>
                  <div v-if="seg.bottleneck_reason" class="ifr-ls-reason">{{ seg.bottleneck_reason }}</div>
                  <div v-if="seg.representative_players?.length" class="ifr-ls-players">{{ seg.representative_players.join(' · ') }}</div>
                </div>
              </div>
            </div>
          </section>

          <!-- §2 产业链瓶颈地图 -->
          <section v-if="detail.chokepoint_map?.length" id="sec-chokepoint" class="ifr-section">
            <h2 class="ifr-h2">🔗 产业链瓶颈地图（{{ detail.chokepoint_map.length }} 环节）</h2>
            <div v-if="detail.top_chokepoints?.length" class="ifr-top-choke">
              <div class="ifr-list-head">🏔️ Top 瓶颈（四维最强）</div>
              <ol><li v-for="(t, i) in detail.top_chokepoints" :key="i">{{ t }}</li></ol>
            </div>
            <table class="ifr-table">
              <thead>
                <tr><th>层级</th><th>环节</th><th>不可替代</th><th>供给集中</th><th>产能刚性</th><th>价值卡位</th><th>发现度</th><th>风险</th></tr>
              </thead>
              <tbody>
                <tr v-for="(n, i) in chokepointMap" :key="i" :class="discoveryRowCls(n.discovery_level)">
                  <td>{{ n.layer }}</td>
                  <td class="ifr-td-node">{{ n.node }}</td>
                  <td :class="dimCls(n.irreplaceability)">{{ n.irreplaceability }}</td>
                  <td :class="dimCls(n.supply_concentration)">{{ n.supply_concentration }}</td>
                  <td :class="dimCls(n.capacity_rigidity)">{{ n.capacity_rigidity }}</td>
                  <td :class="dimCls(n.value_capture)">{{ n.value_capture }}</td>
                  <td><span class="ifr-disc" :class="discCls(n.discovery_level)">{{ n.discovery_level }}</span></td>
                  <td class="ifr-td-risk">{{ n.risk_level }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <!-- §2.5 瓶颈递归上溯深挖（表层 → 逐层上游 → 最深未发现 alpha） -->
          <section v-if="deepChains.length" id="sec-drill" class="ifr-section">
            <h2 class="ifr-h2">⛏️ 瓶颈上溯深挖（供需链：越上游越紧 = 越可能未被 price-in）</h2>
            <p class="ifr-appendix-desc">价格=供需。表层瓶颈往上游逐层钻，找供需最紧张且市场尚未发现的那一环——超额收益所在。</p>
            <div v-for="(dc, i) in deepChains" :key="i" class="ifr-drill">
              <div class="ifr-drill-flow">
                <span class="ifr-drill-start">{{ dc.start }}</span>
                <template v-for="(node, j) in (dc.chain || [])" :key="j">
                  <span class="ifr-drill-arrow">→</span>
                  <span class="ifr-drill-node" :class="discCls(node.discovery_level)">
                    L{{ node.depth ?? j + 1 }} {{ node.node }}
                  </span>
                </template>
              </div>
              <p v-if="dc.deepest_alpha" class="ifr-drill-alpha">🎯 最深 alpha：{{ dc.deepest_alpha }}</p>
              <table v-if="(dc.chain || []).length" class="ifr-table" style="margin-top:8px">
                <thead><tr><th>层</th><th>上游环节</th><th>供需缺口</th><th>扩产周期</th><th>玩家/集中度</th><th>涨价力</th><th>发现度</th><th>受益标的</th></tr></thead>
                <tbody>
                  <tr v-for="(node, j) in dc.chain" :key="j">
                    <td>L{{ node.depth ?? j + 1 }}</td>
                    <td class="ifr-td-node">{{ node.node }}</td>
                    <td class="ifr-td-risk">{{ node.supply_demand_gap }}</td>
                    <td>{{ node.expansion_cycle }}</td>
                    <td>{{ node.global_players }}</td>
                    <td>{{ node.pricing_power }}</td>
                    <td><span class="ifr-disc" :class="discCls(node.discovery_level)">{{ node.discovery_level }}</span></td>
                    <td>{{ [...(node.beneficiaries_a||[]), ...(node.beneficiaries_qdii||[])].join('、') || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- §3 投资地图 -->
          <section v-if="detail.investment_map?.length" id="sec-invmap" class="ifr-section">
            <h2 class="ifr-h2">🎯 投资地图（瓶颈环节 → 推荐标的）</h2>
            <div v-for="(item, i) in investmentMap" :key="i" class="ifr-inv-card" :class="discBorderCls(item.discovery_level)">
              <div class="ifr-inv-head">
                <span class="ifr-inv-rank">#{{ item.position_priority }}</span>
                <router-link v-if="item.code && /^\d{6}$/.test(item.code)" :to="`/portfolio/v4/stock/${item.code}`" class="ifr-inv-name ifr-inv-link">
                  {{ item.beneficiary }} <span class="ifr-inv-code">{{ item.code }}</span> →
                </router-link>
                <span v-else class="ifr-inv-name">{{ item.beneficiary }} <span class="ifr-inv-code">{{ item.code }}</span></span>
                <span class="ifr-disc" :class="discCls(item.discovery_level)">{{ item.discovery_level }}</span>
              </div>
              <div class="ifr-inv-choke">📍 {{ item.chokepoint_node }}</div>
              <p class="ifr-inv-reason">{{ item.reason }}</p>
            </div>
          </section>

          <!-- §3.5 X 一线舆情 (sentiment stage) -->
          <section v-if="hasSentiment" id="sec-sentiment" class="ifr-section">
            <h2 class="ifr-h2">📡 X 一线舆情（{{ senti.coverage?.accounts_analyzed || 0 }} 账号 · {{ senti.coverage?.posts_referenced || 0 }} 推文）
              <span v-if="senti.sentiment_score" class="ifr-senti-score">情绪温度 {{ senti.sentiment_score }}</span>
            </h2>
            <p v-if="senti.sentiment_summary" class="ifr-senti-summary">{{ senti.sentiment_summary }}</p>

            <!-- 方向共识 -->
            <div v-if="senti.direction_consensus?.length" class="ifr-senti-block">
              <div class="ifr-list-head">🧭 方向共识</div>
              <div v-for="(c, i) in senti.direction_consensus" :key="i" class="ifr-senti-card">
                <div class="ifr-senti-sig">
                  <span class="ifr-senti-strength" :class="`ifr-st-${c.strength}`">{{ c.strength }}</span>
                  {{ c.signal }}
                </div>
                <div class="ifr-senti-kols">{{ (c.supporting_kols || []).join(' · ') }}</div>
                <p v-if="c.post_evidence" class="ifr-senti-ev">{{ c.post_evidence }}</p>
              </div>
            </div>

            <!-- 分歧点 -->
            <div v-if="senti.disagreements?.length" class="ifr-senti-block">
              <div class="ifr-list-head">⚔️ KOL 分歧</div>
              <div v-for="(d, i) in senti.disagreements" :key="i" class="ifr-senti-card ifr-senti-disagree">
                <div class="ifr-senti-topic">{{ d.topic }}</div>
                <div class="ifr-senti-sides">
                  <div class="ifr-senti-bull"><b>多/A：</b>{{ d.bull_side?.view }} <span class="ifr-senti-kols">{{ (d.bull_side?.kols||[]).join(' ') }}</span></div>
                  <div class="ifr-senti-bear"><b>空/B：</b>{{ d.bear_side?.view }} <span class="ifr-senti-kols">{{ (d.bear_side?.kols||[]).join(' ') }}</span></div>
                </div>
                <p v-if="d.our_read" class="ifr-senti-read">💡 {{ d.our_read }}</p>
              </div>
            </div>

            <!-- 温度图谱 -->
            <div v-if="senti.heat_map" class="ifr-senti-block">
              <div class="ifr-list-head">🌡️ 发现度温度图谱</div>
              <div class="ifr-heat-grid">
                <div class="ifr-heat-col ifr-heat-hot">
                  <div class="ifr-heat-h">🔴 已过热/price-in</div>
                  <ul><li v-for="(x, i) in senti.heat_map.overheated_已price_in" :key="i">{{ x }}</li></ul>
                </div>
                <div class="ifr-heat-col ifr-heat-mid">
                  <div class="ifr-heat-h">🟡 发现中</div>
                  <ul><li v-for="(x, i) in senti.heat_map.discovering_半发现" :key="i">{{ x }}</li></ul>
                </div>
                <div class="ifr-heat-col ifr-heat-cold">
                  <div class="ifr-heat-h">🟢 未发现</div>
                  <ul><li v-for="(x, i) in senti.heat_map.undiscovered_未发现" :key="i">{{ x }}</li></ul>
                </div>
              </div>
            </div>

            <!-- 催化日历 -->
            <div v-if="senti.catalyst_calendar?.length" class="ifr-senti-block">
              <div class="ifr-list-head">📅 X 提及催化日历</div>
              <div v-for="(c, i) in senti.catalyst_calendar" :key="i" class="ifr-cal-item">
                <div class="ifr-cal-when">{{ c.date }}</div>
                <div class="ifr-cal-body">
                  <div class="ifr-cal-event">{{ c.event }} <span class="ifr-senti-kols">{{ c.source_kol }}</span></div>
                  <p class="ifr-cal-impact">{{ c.impact }}</p>
                </div>
              </div>
            </div>
          </section>

          <!-- §4 未来市场 7 把尺 -->
          <section v-if="hasFutureMarket" id="sec-future" class="ifr-section">
            <h2 class="ifr-h2">📐 未来市场（7 把辩证尺）</h2>
            <div class="ifr-fm-grid">
              <div v-if="ifm.penetration_stage" class="ifr-fm-item ifr-fm-full">
                <div class="ifr-fm-label">渗透率阶段</div><p>{{ ifm.penetration_stage }}</p>
              </div>
              <div v-if="ifm.leaders_concentration" class="ifr-fm-item ifr-fm-full">
                <div class="ifr-fm-label">龙头集中度</div><p>{{ ifm.leaders_concentration }}</p>
              </div>
              <div v-if="ifm.leading_indicators" class="ifr-fm-item ifr-fm-full">
                <div class="ifr-fm-label">先行指标</div><p>{{ ifm.leading_indicators }}</p>
              </div>
              <div v-if="ifm.bottleneck_migration" class="ifr-fm-item ifr-fm-full">
                <div class="ifr-fm-label">瓶颈迁移路径</div><p>{{ ifm.bottleneck_migration }}</p>
              </div>
            </div>
            <div v-if="ifm.key_drivers_5yr?.length" class="ifr-drivers">
              <div class="ifr-list-head">🚀 5 年核心驱动力</div>
              <ol><li v-for="(d, i) in ifm.key_drivers_5yr" :key="i">{{ d }}</li></ol>
            </div>
            <p v-if="ifm.forward_peg_note" class="ifr-fm-note">⚠️ {{ ifm.forward_peg_note }}</p>
          </section>

          <!-- §5 前瞻推演 -->
          <section v-if="hasForward" id="sec-forward" class="ifr-section">
            <h2 class="ifr-h2">🔭 前瞻推演</h2>
            <div v-if="fv.near_term_calendar?.length" class="ifr-cal">
              <div class="ifr-list-head">📅 近端事件日历</div>
              <div v-for="(e, i) in fv.near_term_calendar" :key="i" class="ifr-cal-item">
                <div class="ifr-cal-when">{{ e.timeline }}</div>
                <div class="ifr-cal-body">
                  <div class="ifr-cal-event">{{ e.event }}</div>
                  <p class="ifr-cal-impact">{{ e.impact }}</p>
                </div>
              </div>
            </div>
            <p v-if="fv.mid_term_path" class="ifr-midpath"><b>📈 中期路径：</b>{{ fv.mid_term_path }}</p>
            <div v-if="fv.path_scenarios?.length" class="ifr-scn-grid">
              <div v-for="(s, i) in fv.path_scenarios" :key="i" class="ifr-scn" :class="scnCls(s.scenario)">
                <div class="ifr-scn-name">{{ s.scenario }}</div>
                <p v-if="s.triggers"><b>触发：</b>{{ s.triggers }}</p>
                <p v-if="s.outcome"><b>结果：</b>{{ s.outcome }}</p>
                <p v-if="s.portfolio_action" class="ifr-scn-action"><b>📌 应对：</b>{{ s.portfolio_action }}</p>
              </div>
            </div>
          </section>

          <!-- §6 多空辩论 -->
          <section v-if="debateRounds.length" id="sec-debate" class="ifr-section">
            <h2 class="ifr-h2">⚔️ 多空辩论（{{ debateRounds.length }} 轮）</h2>
            <div v-for="(r, i) in debateRounds" :key="i" class="ifr-debate-round">
              <div class="ifr-debate-tag">第 {{ r.round }} 轮{{ r.round === debateRounds.length ? ' · 终局' : '' }}</div>
              <div class="ifr-duel">
                <div class="ifr-bull">
                  <div class="ifr-side-tag bull">🐂 多头</div>
                  <p v-if="r.bullObj?.thesis" class="ifr-side-thesis">{{ r.bullObj.thesis }}</p>
                  <ul v-if="r.bullObj?.bull_points?.length" class="ifr-points">
                    <li v-for="(pt, j) in r.bullObj.bull_points" :key="j">{{ ptText(pt) }}</li>
                  </ul>
                  <p v-if="r.bullObj?.suggested_stance" class="ifr-side-stance">立场：{{ r.bullObj.suggested_stance }}</p>
                  <p v-if="!r.bullObj && r.bullText" class="ifr-side-thesis">{{ r.bullText }}</p>
                </div>
                <div class="ifr-bear">
                  <div class="ifr-side-tag bear">🐻 空头</div>
                  <p v-if="r.bearObj?.challenge" class="ifr-side-thesis">{{ r.bearObj.challenge }}</p>
                  <ul v-if="r.bearObj?.bear_points?.length" class="ifr-points">
                    <li v-for="(pt, j) in r.bearObj.bear_points" :key="j">{{ ptText(pt) }}</li>
                  </ul>
                  <p v-if="r.bearObj?.key_risks?.length" class="ifr-side-risks">关键风险：{{ (r.bearObj.key_risks as any[]).map(ptText).join('；') }}</p>
                  <p v-if="r.bearObj?.suggested_stance" class="ifr-side-stance">立场：{{ r.bearObj.suggested_stance }}</p>
                  <p v-if="!r.bearObj && r.bearText" class="ifr-side-thesis">{{ r.bearText }}</p>
                </div>
              </div>
            </div>
          </section>

          <!-- §7 关联个股 -->
          <section v-if="detail.stocks?.length || detail.stock_weights?.length" id="sec-stocks" class="ifr-section">
            <h2 class="ifr-h2">📊 关联个股与配比</h2>
            <table v-if="detail.stocks?.length" class="ifr-table">
              <thead><tr><th>代码</th><th>名称</th><th>评级</th><th>目标价</th><th>状态</th></tr></thead>
              <tbody>
                <tr v-for="s in detail.stocks" :key="s.code || ''">
                  <td>
                    <router-link v-if="s.code && /^\d{6}$/.test(s.code)" :to="`/portfolio/v4/stock/${s.code}`" class="ifr-inv-link">{{ s.code }} →</router-link>
                    <span v-else>{{ s.code }}</span>
                  </td>
                  <td>{{ s.name }}</td>
                  <td>{{ s.rating || '-' }}</td>
                  <td>{{ s.target_price ?? '-' }}</td>
                  <td><span class="ifr-disc">{{ s.status_label || s.status }}</span></td>
                </tr>
              </tbody>
            </table>
            <table v-if="detail.stock_weights?.length" class="ifr-table" style="margin-top:14px">
              <thead><tr><th>代码</th><th>目标权重</th><th>买点区间</th><th>理由</th></tr></thead>
              <tbody>
                <tr v-for="(w, i) in detail.stock_weights" :key="i">
                  <td>{{ w.code }}</td><td>{{ w.target_weight }}%</td>
                  <td>{{ Array.isArray(w.entry_price_range) ? w.entry_price_range.join('-') : (w.entry_price_range ?? '-') }}</td>
                  <td>{{ w.reasoning }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <!-- §8 可信度与评审 -->
          <section v-if="hasCred" id="sec-cred" class="ifr-section">
            <h2 class="ifr-h2">🎓 可信度与评审</h2>
            <div class="ifr-cred-card">
              <div class="ifr-cred-scores">
                <span class="ifr-cred-final" :class="{ 'ifr-cred-unresolved': cred.unresolved || cred.final_verdict === 'NEEDS_CHANGES' }">
                  {{ cred.final_verdict || '-' }}<span v-if="credScore != null"> · {{ credScore }}分</span>
                </span>
                <span v-if="cred.reviewer">评审人：{{ cred.reviewer }}</span>
                <span v-if="cred.critic_iterations">迭代 {{ cred.critic_iterations }} 轮</span>
                <span v-if="cred.verified_data_ratio">verified 占比：{{ cred.verified_data_ratio }}</span>
              </div>
              <p v-if="cred.unresolved" class="ifr-cred-warn">⚠️ 经多轮修订仍未达专业评审标准，结论待复核，谨慎参考。</p>
              <p v-if="cred.rationale" class="ifr-cred-rationale">{{ cred.rationale }}</p>
              <div v-if="critChallenges.length" class="ifr-gaps">
                <div class="ifr-list-head">🔍 评审委员会关键挑战 / 改进意见</div>
                <ol><li v-for="(g, i) in critChallenges" :key="i">{{ g }}</li></ol>
              </div>
              <div v-if="cred.self_identified_gaps?.length" class="ifr-gaps">
                <div class="ifr-list-head">🔍 自识别局限</div>
                <ol><li v-for="(g, i) in cred.self_identified_gaps" :key="i">{{ g }}</li></ol>
              </div>
            </div>
            <p v-if="detail.data_quality" class="ifr-dq"><b>数据质量：</b>{{ detail.data_quality }}</p>
          </section>

          <!-- §9 证据链 -->
          <section v-if="detail.evidence?.length" id="sec-evidence" class="ifr-section">
            <h2 class="ifr-h2">📥 证据链（{{ detail.evidence.length }} 条）</h2>
            <div class="ifr-evi-stat">
              <el-tag type="success" effect="plain">verified {{ eviStat.verified }}</el-tag>
              <el-tag type="warning" effect="plain">estimated {{ eviStat.estimated }}</el-tag>
              <el-tag type="info" effect="plain">missing {{ eviStat.missing }}</el-tag>
            </div>
            <ul class="ifr-evi-list">
              <li v-for="(e, i) in detail.evidence" :key="i">
                <el-tag :type="eviTag(e.status)" size="small" effect="plain">{{ e.status }}</el-tag>
                {{ e.claim }}
                <span v-if="e.source" class="ifr-evi-src">— {{ e.source }}</span>
              </li>
            </ul>
          </section>

          <!-- §10 完整数据附录 -->
          <section v-if="leftoverEntries.length" id="sec-appendix" class="ifr-section">
            <h2 class="ifr-h2">📦 完整数据附录</h2>
            <p class="ifr-appendix-desc">未在上方专题章节展示的全部原始字段，确保零信息丢失。</p>
            <el-collapse>
              <el-collapse-item v-for="[k, v] in leftoverEntries" :key="k" :name="k">
                <template #title><span class="ifr-appendix-key">{{ k }}</span></template>
                <JsonTree :value="v" />
              </el-collapse-item>
            </el-collapse>
          </section>
        </main>
      </div>
    </template>

    <div v-else class="ifr-empty">
      <el-empty description="未找到该行业完整分析报告" />
      <el-button type="primary" @click="router.back()">返回</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { portfolioV4Api, type IndustryDetail } from '@/api/portfolioV4'
import JsonTree from './JsonTree.vue'

// industryProp：嵌入 V4Overview tab 时父级传入；独立路由页取 route.params
const props = defineProps<{ industryProp?: string }>()
const route = useRoute()
const router = useRouter()
const name = computed(() => props.industryProp || (route.params.name as string))
const detail = ref<IndustryDetail | null>(null)
const loading = ref(false)

async function load(n: string) {
  if (!n) return
  loading.value = true
  try {
    const res: any = await portfolioV4Api.getIndustryDetail(n)
    let d: any = res
    if (d && typeof d === 'object' && d.data && typeof d.data === 'object') d = d.data
    detail.value = d && d.industry ? d : null
  } catch (e) {
    console.error('[IndustryFullReport] load failed', n, e)
    detail.value = null
  } finally {
    loading.value = false
  }
}

const verdict = computed<any>(() => detail.value?.verdict || {})
const ifm = computed<any>(() => detail.value?.industry_future_market || {})
const fv = computed<any>(() => detail.value?.forward_view || {})
const cred = computed<any>(() => detail.value?.credibility || {})
// 兼容字段名: workflow 写 critic_score, 旧/critic agent 用 score
const credScore = computed<number | null>(() => {
  const c = cred.value
  const v = c.critic_score ?? c.score
  return v != null ? v : null
})
const critChallenges = computed<string[]>(() => {
  const c = cred.value
  const arr = c.challenges || c.improvements || c.fatal_flaws || []
  return Array.isArray(arr) ? arr : []
})
// 实际 payload 字段比 TS 接口更丰富（chokepoint_node/beneficiary/discovery_level/risk_level 等），用 any 透传
const chokepointMap = computed<any[]>(() => (detail.value?.chokepoint_map as any[]) || [])
const investmentMap = computed<any[]>(() => (detail.value?.investment_map as any[]) || [])
const deepChains = computed<any[]>(() => (detail.value?.deep_chokepoint_chains as any[]) || [])
const landscape = computed<any[]>(() => (detail.value?.landscape as any[]) || [])
// 按 layer 分组平铺（瓶颈层优先展示），保留出现顺序
const landscapeByLayer = computed<Record<string, any[]>>(() => {
  const groups: Record<string, any[]> = {}
  for (const seg of landscape.value) {
    const layer = seg.layer || '其它'
    if (!groups[layer]) groups[layer] = []
    groups[layer].push(seg)
  }
  return groups
})

const senti = computed<any>(() => detail.value?.sentiment || {})
const hasSentiment = computed(() => {
  const s = senti.value
  return !!(s.sentiment_summary || s.direction_consensus?.length || s.heat_map)
})
const hasFutureMarket = computed(() => Object.keys(ifm.value).length > 0)
const hasForward = computed(() => {
  const f = fv.value
  return !!(f.near_term_calendar?.length || f.mid_term_path || f.path_scenarios?.length)
})
const hasCred = computed(() => Object.keys(cred.value).length > 0 || !!detail.value?.data_quality)

// 辩论：bull/bear 可能是解析后的对象，也可能是回退的字符串
const debateRounds = computed(() => {
  const rounds = detail.value?.debate_rounds || []
  return rounds.map((r: any) => ({
    round: r.round,
    bullObj: r.bull && typeof r.bull === 'object' ? r.bull : null,
    bullText: typeof r.bull === 'string' ? r.bull : null,
    bearObj: r.bear && typeof r.bear === 'object' ? r.bear : null,
    bearText: typeof r.bear === 'string' ? r.bear : null,
  }))
})

const eviStat = computed(() => {
  const ev = detail.value?.evidence || []
  return {
    verified: ev.filter((e: any) => e.status === 'verified').length,
    estimated: ev.filter((e: any) => e.status === 'estimated').length,
    missing: ev.filter((e: any) => e.status === 'missing').length,
  }
})

// TOC
const tocSections = computed(() => {
  const secs = [{ id: 'sec-verdict', icon: '📌', label: '行业裁决' }]
  if (landscape.value.length) secs.push({ id: 'sec-landscape', icon: '🗺️', label: '产业链全景' })
  if (detail.value?.chokepoint_map?.length) secs.push({ id: 'sec-chokepoint', icon: '🔗', label: '瓶颈地图' })
  if (deepChains.value.length) secs.push({ id: 'sec-drill', icon: '⛏️', label: '瓶颈上溯深挖' })
  if (detail.value?.investment_map?.length) secs.push({ id: 'sec-invmap', icon: '🎯', label: '投资地图' })
  if (hasSentiment.value) secs.push({ id: 'sec-sentiment', icon: '📡', label: 'X 一线舆情' })
  if (hasFutureMarket.value) secs.push({ id: 'sec-future', icon: '📐', label: '未来市场' })
  if (hasForward.value) secs.push({ id: 'sec-forward', icon: '🔭', label: '前瞻推演' })
  if (debateRounds.value.length) secs.push({ id: 'sec-debate', icon: '⚔️', label: '多空辩论' })
  if (detail.value?.stocks?.length || detail.value?.stock_weights?.length) secs.push({ id: 'sec-stocks', icon: '📊', label: '关联个股' })
  if (hasCred.value) secs.push({ id: 'sec-cred', icon: '🎓', label: '可信度评审' })
  if (detail.value?.evidence?.length) secs.push({ id: 'sec-evidence', icon: '📥', label: '证据链' })
  if (leftoverEntries.value.length) secs.push({ id: 'sec-appendix', icon: '📦', label: '完整数据附录' })
  return secs
})

// Scrollspy
const activeSection = ref('')
let observer: IntersectionObserver | null = null
onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => { for (const e of entries) if (e.isIntersecting) activeSection.value = e.target.id },
    { rootMargin: '-80px 0px -60% 0px', threshold: 0.1 }
  )
})
onUnmounted(() => observer?.disconnect())
watch(loading, (v) => {
  if (!v) setTimeout(() => { document.querySelectorAll('.ifr-section').forEach(el => observer?.observe(el)) }, 100)
})
function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  activeSection.value = id
}

// 完整数据附录：未被专题章节消费的字段
const CONSUMED = new Set<string>([
  'industry', 'industry_unit', 'verdict', 'debate_rounds', 'chokepoint_map', 'top_chokepoints',
  'deep_chokepoint_chains', 'landscape',
  'investment_map', 'sentiment', 'industry_future_market', 'forward_view', 'evidence', 'data_quality', 'data_status',
  'credibility', 'reflection', 'stocks', 'stock_weights', 'intra_alloc_unit', 'analysts',
  'value_creation_industry', 'fund_recommendation', 'indirect_holdings',
])
const leftoverEntries = computed(() => {
  const d: any = detail.value || {}
  const out: Array<[string, any]> = []
  for (const k of Object.keys(d)) {
    if (CONSUMED.has(k)) continue
    const v = d[k]
    if (v == null || (Array.isArray(v) && v.length === 0)) continue
    out.push([k, v])
  }
  return out
})

// Helpers
const stanceType = computed(() => stanceTypeFor(verdict.value.stance))
const stanceCls = computed(() => {
  const s = verdict.value.stance || ''
  if (/超配|看多|增持/.test(s)) return 'pos'
  if (/低配|看空|回避|减持/.test(s)) return 'neg'
  return 'neutral'
})
function stanceTypeFor(s?: string): any {
  if (!s) return 'info'
  if (/超配|看多|增持/.test(s)) return 'success'
  if (/低配|看空|回避|减持/.test(s)) return 'danger'
  return 'warning'
}
function ptText(pt: any): string {
  if (pt == null) return ''
  if (typeof pt === 'string') return pt
  return pt.point || pt.risk || pt.claim || JSON.stringify(pt)
}
function dimCls(v?: string): string {
  if (!v) return ''
  if (/极高/.test(v)) return 'ifr-dim-vh'
  if (/高/.test(v)) return 'ifr-dim-h'
  if (/中/.test(v)) return 'ifr-dim-m'
  return 'ifr-dim-l'
}
function discCls(v?: string): string {
  if (/未发现/.test(v || '')) return 'disc-undisc'
  if (/半发现/.test(v || '')) return 'disc-half'
  if (/已拥挤|已发现/.test(v || '')) return 'disc-crowd'
  return ''
}
function discoveryRowCls(v?: string): string {
  if (/未发现/.test(v || '')) return 'ifr-row-undisc'
  if (/半发现/.test(v || '')) return 'ifr-row-half'
  return ''
}
function discBorderCls(v?: string): string {
  if (/未发现/.test(v || '')) return 'ifr-border-undisc'
  if (/半发现/.test(v || '')) return 'ifr-border-half'
  return 'ifr-border-crowd'
}
function scnCls(s?: string): string {
  if (/牛市|乐观/.test(s || '')) return 'scn-bull'
  if (/熊市|悲观/.test(s || '')) return 'scn-bear'
  return 'scn-base'
}
function eviTag(s?: string): any {
  if (s === 'verified') return 'success'
  if (s === 'estimated') return 'warning'
  return 'info'
}

watch(name, (n) => { if (n) load(n) }, { immediate: true })
</script>

<style scoped>
.ifr { min-height: 100vh; background: #f5f7fa; }
.ifr-loading { padding: 60px 40px; max-width: 900px; margin: 0 auto; }

/* Hero */
.ifr-hero { background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); color: #fff; padding: 32px 40px 24px; }
.ifr-hero-main { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.ifr-hero-title { font-size: 26px; font-weight: 800; margin: 0; }
.ifr-hero-sub { font-size: 14px; font-weight: 400; opacity: 0.6; margin-left: 10px; }
.ifr-hero-meta { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.ifr-hero-score { background: rgba(255,255,255,0.15); padding: 4px 14px; border-radius: 16px; font-size: 13px; font-weight: 600; }
.ifr-hero-kpi { display: flex; gap: 20px; margin-top: 20px; flex-wrap: wrap; }
.ifr-kpi { display: flex; flex-direction: column; align-items: center; background: rgba(255,255,255,0.08); padding: 12px 20px; border-radius: 10px; min-width: 96px; }
.ifr-kpi-label { font-size: 12px; opacity: 0.7; margin-bottom: 4px; }
.ifr-kpi-val { font-size: 18px; font-weight: 700; }
.ifr-kpi-green { color: #52c41a; }
.ifr-hero-gen { margin-top: 16px; font-size: 12px; opacity: 0.5; display: flex; align-items: center; gap: 16px; }

/* Body */
.ifr-body { display: flex; max-width: 1400px; margin: 0 auto; padding: 24px 20px; gap: 24px; }
.ifr-toc { width: 190px; flex-shrink: 0; position: sticky; top: 20px; align-self: flex-start; }
.ifr-toc nav { background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.ifr-toc-title { font-size: 13px; font-weight: 700; color: #909399; margin-bottom: 12px; letter-spacing: 1px; }
.ifr-toc-link { display: block; padding: 7px 10px; margin: 2px 0; border-radius: 6px; font-size: 13px; color: #606266; text-decoration: none; transition: all 0.2s; }
.ifr-toc-link:hover { background: #f5f7fa; color: #303133; }
.ifr-toc-link.active { background: #e6f4ff; color: #2c5364; font-weight: 600; }

.ifr-main { flex: 1; min-width: 0; }
.ifr-section { background: #fff; border-radius: 12px; padding: 24px 28px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); scroll-margin-top: 20px; }
.ifr-h2 { font-size: 18px; font-weight: 700; color: #1d2129; margin: 0 0 16px; padding-bottom: 10px; border-bottom: 2px solid #f0f0f0; }
.ifr-list-head { font-size: 13px; font-weight: 700; color: #303133; margin: 12px 0 8px; }

/* §1 Verdict */
.ifr-verdict-card { background: #fafbfc; border-radius: 8px; padding: 16px; margin-bottom: 14px; }
.ifr-verdict-stance { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.ifr-verdict-stance.pos { color: #389e0d; }
.ifr-verdict-stance.neg { color: #cf1322; }
.ifr-verdict-stance.neutral { color: #d46b08; }
.ifr-verdict-dir { font-size: 14px; color: #303133; margin: 6px 0; }
.ifr-verdict-text { font-size: 13.5px; color: #4e5969; line-height: 1.8; margin: 6px 0 0; }
.ifr-verdict-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.ifr-vg-item { background: #fafbfc; border-radius: 8px; padding: 12px 14px; border: 1px solid #ebeef5; }
.ifr-vg-item.ifr-vg-full { grid-column: 1 / -1; }
.ifr-vg-item.ifr-vg-warn { background: #fff7e6; border-color: #ffe7ba; }
.ifr-vg-label { font-size: 12px; font-weight: 700; color: #909399; margin-bottom: 6px; }
.ifr-vg-item p { font-size: 13px; line-height: 1.7; color: #4e5969; margin: 0; }
.ifr-risks { margin-top: 14px; }
.ifr-risks ol { padding-left: 22px; line-height: 1.9; font-size: 13px; color: #4e5969; }

/* Tables */
.ifr-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.ifr-table th { background: #f0f2f5; padding: 8px 10px; text-align: left; font-weight: 600; color: #606266; border-bottom: 2px solid #e4e7ed; white-space: nowrap; }
.ifr-table td { padding: 8px 10px; border-bottom: 1px solid #f0f2f5; vertical-align: top; }
.ifr-td-node { font-weight: 600; color: #303133; }
.ifr-td-risk { color: #874d00; font-size: 12px; max-width: 200px; }
.ifr-dim-vh { color: #cf1322; font-weight: 700; }
.ifr-dim-h { color: #d46b08; font-weight: 600; }
.ifr-dim-m { color: #d48806; }
.ifr-dim-l { color: #8c8c8c; }
.ifr-row-undisc { background: #f6ffed; }
.ifr-row-half { background: #fffbe6; }

/* discovery tag */
.ifr-disc { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; background: #f0f0f0; color: #606266; }
.disc-undisc { background: #f6ffed; color: #389e0d; }
.disc-half { background: #fffbe6; color: #d48806; }
.disc-crowd { background: #fff1f0; color: #cf1322; }
.ifr-top-choke { margin-bottom: 14px; }
.ifr-top-choke ol { padding-left: 22px; line-height: 1.9; font-size: 13px; color: #4e5969; }

/* §3 InvMap */
.ifr-inv-card { border-radius: 8px; padding: 14px; margin-bottom: 10px; background: #fafbfc; border-left: 4px solid #ddd; }
.ifr-border-undisc { border-left-color: #52c41a; background: #f6ffed; }
.ifr-border-half { border-left-color: #faad14; background: #fffbe6; }
.ifr-border-crowd { border-left-color: #cf1322; }
.ifr-inv-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
.ifr-inv-rank { background: #2c5364; color: #fff; border-radius: 12px; padding: 1px 10px; font-size: 12px; font-weight: 700; }
.ifr-inv-name { font-size: 15px; font-weight: 700; color: #303133; }
.ifr-inv-link { color: #2c5364; text-decoration: none; }
.ifr-inv-link:hover { text-decoration: underline; }
.ifr-inv-code { font-size: 12px; color: #909399; font-weight: 400; }
.ifr-inv-choke { font-size: 12.5px; color: #5b6dde; margin-bottom: 6px; }
.ifr-inv-reason { font-size: 13px; line-height: 1.7; color: #4e5969; margin: 0; }

/* §4 Future market */
.ifr-fm-grid { display: grid; grid-template-columns: 1fr; gap: 10px; }
.ifr-fm-item { background: #fafbfc; border-radius: 8px; padding: 12px 14px; border-left: 3px solid #2c5364; }
.ifr-fm-label { font-size: 12px; font-weight: 700; color: #2c5364; margin-bottom: 4px; }
.ifr-fm-item p { font-size: 13px; line-height: 1.7; color: #4e5969; margin: 0; }
.ifr-drivers { margin-top: 14px; }
.ifr-drivers ol { padding-left: 22px; line-height: 1.9; font-size: 13px; color: #4e5969; }
.ifr-fm-note { font-size: 12.5px; color: #874d00; background: #fff7e6; padding: 8px 12px; border-radius: 6px; margin-top: 10px; }

/* §3.5 X 一线舆情 */
.ifr-senti-score { font-size: 12px; font-weight: 600; color: #c0392b; background: #fdecea; padding: 2px 10px; border-radius: 10px; margin-left: 10px; }
.ifr-senti-summary { font-size: 13.5px; line-height: 1.85; color: #303133; background: #f5f9ff; border-left: 3px solid #409eff; padding: 12px 14px; border-radius: 0 8px 8px 0; margin: 0 0 16px; }
.ifr-senti-block { margin-top: 16px; }
.ifr-senti-card { border: 1px solid #ebeef5; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; background: #fff; }
.ifr-senti-sig { font-size: 13.5px; font-weight: 600; color: #303133; line-height: 1.6; }
.ifr-senti-strength { display: inline-block; padding: 1px 7px; border-radius: 8px; font-size: 11px; font-weight: 700; margin-right: 6px; }
.ifr-st-强 { background: #fef0f0; color: #f56c6c; }
.ifr-st-中 { background: #fdf6ec; color: #e6a23c; }
.ifr-st-弱 { background: #f4f4f5; color: #909399; }
.ifr-senti-kols { font-size: 12px; color: #409eff; font-weight: 500; }
.ifr-senti-ev { font-size: 12.5px; color: #606266; line-height: 1.7; margin: 6px 0 0; }
.ifr-senti-disagree { border-left: 3px solid #e6a23c; }
.ifr-senti-topic { font-size: 13.5px; font-weight: 700; color: #874d00; margin-bottom: 8px; }
.ifr-senti-sides { display: flex; flex-direction: column; gap: 6px; font-size: 12.5px; line-height: 1.6; color: #4e5969; }
.ifr-senti-bull { background: #f0f9eb; padding: 6px 10px; border-radius: 6px; }
.ifr-senti-bear { background: #fef0f0; padding: 6px 10px; border-radius: 6px; }
.ifr-senti-read { font-size: 12.5px; color: #2c5364; background: #f5f7fa; padding: 7px 10px; border-radius: 6px; margin: 8px 0 0; line-height: 1.6; }
.ifr-heat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.ifr-heat-col { border-radius: 8px; padding: 12px; }
.ifr-heat-hot { background: #fef0f0; border: 1px solid #fde2e2; }
.ifr-heat-mid { background: #fdf6ec; border: 1px solid #faecd8; }
.ifr-heat-cold { background: #f0f9eb; border: 1px solid #e1f3d8; }
.ifr-heat-h { font-size: 13px; font-weight: 700; margin-bottom: 8px; }
.ifr-heat-col ul { padding-left: 18px; margin: 0; }
.ifr-heat-col li { font-size: 12px; line-height: 1.7; color: #4e5969; margin-bottom: 4px; }

/* §5 Forward */
.ifr-cal-item { display: flex; gap: 14px; padding: 10px 0; border-bottom: 1px dashed #f0f0f0; }
.ifr-cal-when { flex-shrink: 0; width: 90px; font-size: 12.5px; font-weight: 700; color: #2c5364; }
.ifr-cal-event { font-size: 13.5px; font-weight: 600; color: #303133; }
.ifr-cal-impact { font-size: 12.5px; color: #606266; line-height: 1.6; margin: 4px 0 0; }
.ifr-midpath { font-size: 13.5px; line-height: 1.8; color: #4e5969; background: #f5f7fa; padding: 12px 14px; border-radius: 8px; margin: 14px 0; }
.ifr-scn-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.ifr-scn { border-radius: 8px; padding: 14px; border: 1px solid #ebeef5; }
.ifr-scn p { font-size: 12.5px; line-height: 1.6; margin: 4px 0; color: #4e5969; }
.ifr-scn-name { font-size: 13px; font-weight: 700; margin-bottom: 8px; color: #303133; }
.ifr-scn-action { background: rgba(255,255,255,0.7); padding: 6px 8px; border-radius: 4px; }
.scn-bull { background: #f6ffed; border-color: #b7eb8f; }
.scn-bear { background: #fff1f0; border-color: #ffccc7; }
.scn-base { background: #fffbe6; border-color: #ffe58f; }

/* §6 Debate */
.ifr-debate-round { margin-bottom: 14px; padding: 12px; background: #fafbfc; border-radius: 8px; }
.ifr-debate-tag { font-size: 13px; font-weight: 700; color: #303133; margin-bottom: 10px; }
.ifr-duel { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.ifr-bull { background: #f6ffed; border-radius: 8px; padding: 12px; }
.ifr-bear { background: #fff1f0; border-radius: 8px; padding: 12px; }
.ifr-side-tag { font-size: 12px; font-weight: 700; margin-bottom: 6px; }
.ifr-side-tag.bull { color: #389e0d; }
.ifr-side-tag.bear { color: #cf1322; }
.ifr-side-thesis { font-size: 13px; line-height: 1.7; color: #303133; margin: 4px 0; font-weight: 500; }
.ifr-points { padding-left: 18px; margin: 6px 0; }
.ifr-points li { font-size: 12.5px; line-height: 1.6; color: #4e5969; margin: 3px 0; }
.ifr-side-risks { font-size: 12px; color: #a8071a; line-height: 1.6; margin: 4px 0; }
.ifr-side-stance { font-size: 12px; color: #606266; font-style: italic; margin: 6px 0 0; }

/* §8 Cred */
.ifr-cred-card { background: #fafbfc; border-radius: 8px; padding: 14px; }
.ifr-cred-scores { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: #606266; margin-bottom: 10px; }
.ifr-cred-final { font-weight: 700; color: #389e0d; }
.ifr-cred-final.ifr-cred-unresolved { color: #cf1322; }
.ifr-cred-warn { font-size: 13px; color: #a8071a; background: #fff1f0; padding: 8px 12px; border-radius: 6px; margin: 8px 0; line-height: 1.6; }
.ifr-cred-rationale { font-size: 13px; line-height: 1.7; color: #4e5969; margin: 0; }
.ifr-gaps { margin-top: 12px; }
.ifr-gaps ol { padding-left: 22px; line-height: 1.8; font-size: 12.5px; color: #874d00; }
.ifr-dq { font-size: 12.5px; color: #606266; line-height: 1.7; margin-top: 12px; padding: 10px 12px; background: #f5f7fa; border-radius: 6px; }

/* §9 Evidence */
.ifr-evi-stat { display: flex; gap: 8px; margin-bottom: 12px; }
.ifr-evi-list { list-style: none; padding: 0; font-size: 12.5px; line-height: 1.9; }
.ifr-evi-list li { padding: 6px 0; border-bottom: 1px dashed #f0f2f5; }
.ifr-evi-src { color: #909399; font-size: 11.5px; margin-left: 6px; }

/* §10 Appendix */
.ifr-appendix-desc { font-size: 13px; color: #909399; margin-bottom: 12px; }
.ifr-appendix-key { font-weight: 600; color: #2c5364; font-size: 13.5px; }

/* §1.5 产业链全景（按层平铺，仿全景图） */
.ifr-ls-layer { margin-bottom: 16px; }
.ifr-ls-layer-name { font-size: 13px; font-weight: 700; color: #2c5364; margin-bottom: 8px; padding-left: 4px; border-left: 3px solid #2c5364; }
.ifr-ls-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.ifr-ls-card { background: #fafbfc; border: 1px solid #ebeef5; border-radius: 8px; padding: 10px 12px; }
.ifr-ls-card.ifr-ls-bottleneck { background: #fff7f6; border: 1.5px solid #f5a3a0; }
.ifr-ls-seg { font-size: 13.5px; font-weight: 700; color: #303133; margin-bottom: 4px; }
.ifr-ls-role { font-size: 12px; color: #606266; line-height: 1.5; }
.ifr-ls-reason { font-size: 11.5px; color: #a8071a; line-height: 1.5; margin-top: 4px; }
.ifr-ls-players { font-size: 11.5px; color: #2c5364; margin-top: 6px; line-height: 1.5; }

/* §2.5 瓶颈上溯深挖 */
.ifr-drill { margin-bottom: 18px; padding: 12px 14px; background: #fafbfc; border: 1px solid #ebeef5; border-radius: 8px; }
.ifr-drill-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 8px; }
.ifr-drill-start { font-size: 13px; font-weight: 700; color: #303133; background: #eef2ff; padding: 3px 10px; border-radius: 12px; }
.ifr-drill-arrow { color: #c0c4cc; font-weight: 700; }
.ifr-drill-node { font-size: 12.5px; font-weight: 600; padding: 3px 10px; border-radius: 12px; background: #f0f2f5; color: #606266; }
.ifr-drill-node.disc-undisc { background: #f6ffed; color: #389e0d; }
.ifr-drill-node.disc-half { background: #fffbe6; color: #d48806; }
.ifr-drill-node.disc-crowd { background: #fff1f0; color: #cf1322; }
.ifr-drill-alpha { font-size: 13px; color: #874d00; background: #fff7e6; padding: 8px 12px; border-radius: 6px; border-left: 3px solid #faad14; margin: 6px 0; line-height: 1.6; }

.ifr-empty { text-align: center; padding: 60px; }

@media (max-width: 900px) {
  .ifr-toc { display: none; }
  .ifr-body { padding: 12px; }
  .ifr-hero { padding: 20px; }
  .ifr-duel { grid-template-columns: 1fr; }
  .ifr-section { padding: 16px; }
  .ifr-table { font-size: 11.5px; }
}
@media print {
  .ifr-toc { display: none; }
  .ifr-hero { background: #fff; color: #000; }
  .ifr-section { break-inside: avoid; box-shadow: none; border: 1px solid #ddd; }
}
</style>
