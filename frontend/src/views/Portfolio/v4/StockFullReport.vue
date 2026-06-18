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
          </section>

          <!-- §4 产品拆解 -->
          <section v-if="payload.product_subdivision_deep" id="sec-product" class="sfr-section">
            <h2 class="sfr-h2">🏭 产品业务拆解</h2>
            <div v-for="(info, segment) in payload.product_subdivision_deep" :key="segment" class="sfr-prod-card">
              <div class="sfr-prod-name">{{ segment }}</div>
              <div class="sfr-prod-grid">
                <div v-for="(val, field) in info" :key="field" class="sfr-prod-field">
                  <span class="sfr-prod-label">{{ field }}</span>
                  <span class="sfr-prod-val">{{ val }}</span>
                </div>
              </div>
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
          <section v-if="debatePairs.length" id="sec-debate" class="sfr-section">
            <h2 class="sfr-h2">⚔️ 多空辩论（{{ debatePairs.length }} 轮）</h2>
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

          <!-- §12 反思 -->
          <section v-if="payload.reflection" id="sec-reflection" class="sfr-section">
            <h2 class="sfr-h2">🔄 版本反思</h2>
            <div class="sfr-reflect-card">
              <p v-if="payload.reflection.what_changed"><b>本次变化：</b>{{ payload.reflection.what_changed }}</p>
              <p v-if="payload.reflection.memory_used?.length"><b>使用记忆：</b>{{ payload.reflection.memory_used.join('；') }}</p>
            </div>
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

const route = useRoute()
const router = useRouter()
const code = computed(() => route.params.code as string)
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
  if (payload.value.product_subdivision_deep) secs.push({ id: 'sec-product', icon: '🏭', label: '产品拆解' })
  if (payload.value.five_forces) secs.push({ id: 'sec-fiveforces', icon: '🏰', label: '五力分析' })
  if (payload.value.forward_view_6dim) secs.push({ id: 'sec-forward', icon: '🔭', label: '前瞻推演' })
  if (debatePairs.value.length) secs.push({ id: 'sec-debate', icon: '⚔️', label: '多空辩论' })
  if (payload.value.risk_consensus_from_3way) secs.push({ id: 'sec-risk', icon: '⚖️', label: '风险辩论' })
  if (payload.value.anchoring_check) secs.push({ id: 'sec-anchor', icon: '🧭', label: '锚定自查' })
  if (payload.value.value_creation_verified) secs.push({ id: 'sec-value', icon: '🏭', label: '价值创造' })
  if (payload.value.critic_evaluation) secs.push({ id: 'sec-critic', icon: '🎓', label: '评审过程' })
  if (payload.value.reflection) secs.push({ id: 'sec-reflection', icon: '🔄', label: '版本反思' })
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
