<template>
  <div class="stock-detail-tab">
    <div v-if="loading" class="sdt-loading"><el-skeleton :rows="6" animated /></div>
    <template v-else-if="detail">

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
            <b class="sdt-action-val">{{ detail.target_price != null ? `¥${detail.target_price}` : '区间法' }}</b>
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
          <li v-if="whyWorst"><span class="sdt-why-tag sdt-tag-worst">⚠️ 最坏</span>{{ whyWorst }}</li>
          <li v-if="whyExpGap"><span class="sdt-why-tag sdt-tag-gap">🎲 预期差</span>{{ whyExpGap }}</li>
        </ul>
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
        <p class="sdt-support-desc">展示系统从「数据采集 → 3 分析师 → 多空辩论 → director 拍板 → critic 评审」的完整推理过程，让你看到结论是怎么来的</p>
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
                👔 Step 2 · 三分析师并列分析
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
            <details class="sdt-substep">
              <summary>💰 c · 估值分析师（三锚推导）</summary>
              <p v-if="detail.valuation_basis" class="sdt-thesis-valuation">{{ detail.valuation_basis }}</p>
              <p v-if="detail.analysts?.valuation">{{ detail.analysts.valuation }}</p>
              <p v-if="!detail.valuation_basis && !detail.analysts?.valuation" class="sdt-empty">（valuation_basis 未提供）</p>
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

          <!-- Step 4 director 拍板 -->
          <el-collapse-item name="step4">
            <template #title><span class="sdt-step-title">🎩 Step 4 · director 拍板（综合所有产出）</span></template>
            <p class="sdt-step-desc">director 消费 3 分析师 + 多空辩论 + chokepoint, 给反骑墙立场 + reflection + forward_view 三情景</p>
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
              <summary>🔭 forward_view · 三情景 + 触发监控</summary>
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
            </details>
            <!-- reflection 完整版 -->
            <details class="sdt-substep" v-if="detail.reflection">
              <summary>🔄 reflection · 较上次完整自检</summary>
              <p v-if="detail.reflection.prev_stance"><b>上次立场：</b>{{ detail.reflection.prev_stance }}</p>
              <p v-if="detail.reflection.what_changed"><b>本次变化：</b>{{ detail.reflection.what_changed }}</p>
              <p v-if="detail.reflection.why_changed"><b>为何改：</b>{{ detail.reflection.why_changed }}</p>
              <p v-if="detail.reflection.self_check"><b>自检：</b>{{ detail.reflection.self_check }}</p>
            </details>
          </el-collapse-item>

          <!-- Step 5 critic 评审 -->
          <el-collapse-item v-if="detail.credibility" name="step5">
            <template #title>
              <span class="sdt-step-title">
                🎓 Step 5 · critic 评审（4 视角质量闸门）
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
          </el-collapse-item>

          <!-- Step 6 历史准确率 完整 -->
          <el-collapse-item v-if="detail.historical_alpha" name="step6">
            <template #title>
              <span class="sdt-step-title">
                📈 Step 6 · 历史判断准确率（结果闭环）
                <el-tag size="small" :type="hitType" class="sdt-step-tag">{{ hitLabel }}</el-tag>
              </span>
            </template>
            <p>{{ detail.historical_alpha.alpha_note }}</p>
            <p class="sdt-alpha-meta">数据状态: {{ detail.historical_alpha.data_status }} | 评估日: {{ detail.historical_alpha.evaluated_at }}</p>
          </el-collapse-item>

          <!-- Step 7 风险 + 止损全集 -->
          <el-collapse-item name="step7">
            <template #title>
              <span class="sdt-step-title">
                ⚠️ Step 7 · 风险清单 + 止损纪律全集
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
    const res = await portfolioV4Api.getStockDetail(code)
    detail.value = (res as any).data ?? null
  } catch { detail.value = null } finally { loading.value = false }
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
// 止损线
const stopPrice = computed(() => {
  const range = detail.value?.entry_price_range || []
  if (range.length === 2 && typeof range[0] === 'number') return range[0]
  const s1 = (detail.value?.sell_discipline || [])[0] || ''
  const m = s1.match(/(\d{2,5}(?:\.\d+)?)\s*元/)
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
const whyChain = computed(() => {
  const cp = detail.value?.chain_positioning
  if (!cp) return ''
  return `${cp.industry} → ${cp.chokepoint} → 排 #${cp.my_rank}（${cp.my_why ? cp.my_why.slice(0, 50) + '…' : ''}）`
})
const whyMoat = computed(() => {
  const f = detail.value?.five_forces
  if (!f) return ''
  const rating = f.moat_rating || '?'
  const dur = f.moat_durability ? f.moat_durability.split('；')[0].slice(0, 30) : ''
  const weak = (f.cross_force_dynamics?.weakest_link || '').split('—')[0].slice(0, 40)
  return `护城河 ${rating}（${dur}） · 最弱一环：${weak}`
})
const whyValuation = computed(() => {
  const v = detail.value?.valuation_basis || ''
  // 提取第一句
  return v ? v.split(/[;。]/)[0].slice(0, 100) : ''
})
const whyWorst = computed(() => {
  const w = detail.value?.worst_case || detail.value?.downside || ''
  return w ? w.slice(0, 100) : ''
})
const whyExpGap = computed(() => {
  const g = detail.value?.expectation_gap || ''
  return g ? g.slice(0, 100) : ''
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
    if (r.side === 'bull' && r.thesis) map[rd].bull = r.thesis
    else if (r.side === 'bear' && r.thesis) map[rd].bear = r.thesis
    else if (typeof r.bull === 'string') map[rd].bull = r.bull
    else if (typeof r.bear === 'string') map[rd].bear = r.bear
    else if (r.bull?.thesis) map[rd].bull = r.bull.thesis
    else if (r.bear?.thesis) map[rd].bear = r.bear.thesis
  }
  return Object.values(map).filter(p => p.bull || p.bear).sort((a, b) => a.round - b.round)
})

function fmtRange(r?: number[]) { return r && r.length === 2 ? `¥${r[0]} - ¥${r[1]}` : '-' }
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
</style>
