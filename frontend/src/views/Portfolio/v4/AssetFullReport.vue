<template>
  <div class="rpt">
    <div v-if="loading" class="rpt-loading"><el-skeleton :rows="10" animated /></div>

    <template v-else-if="detail">
      <header class="rpt-hero" :style="heroStyle">
        <div class="rpt-hero-main">
          <h1 class="rpt-hero-title">
            {{ detail.label || detail.asset_class }}
            <span class="rpt-hero-sub">大类完整分析</span>
          </h1>
          <div class="rpt-hero-meta">
            <el-tag v-if="stanceLabel" :type="stanceType" effect="dark" size="large">{{ stanceLabel }}</el-tag>
            <span class="rpt-hero-score">{{ detail.is_equity ? '权益（可下钻行业→个股）' : '非权益（执行方案）' }}</span>
          </div>
        </div>
        <div class="rpt-hero-kpi">
          <div v-if="curWeight != null" class="rpt-kpi">
            <span class="rpt-kpi-label">当前配比</span>
            <span class="rpt-kpi-val">{{ curWeight }}%</span>
          </div>
          <div v-if="tgtWeight != null" class="rpt-kpi">
            <span class="rpt-kpi-label">目标配比</span>
            <span class="rpt-kpi-val rpt-kpi-green">{{ tgtWeight }}%</span>
          </div>
          <div v-if="confidencePct != null" class="rpt-kpi">
            <span class="rpt-kpi-label">置信度</span>
            <span class="rpt-kpi-val">{{ confidencePct }}%</span>
          </div>
          <div v-if="detail.is_equity && detail.industries?.length" class="rpt-kpi">
            <span class="rpt-kpi-label">下属行业</span>
            <span class="rpt-kpi-val">{{ detail.industries.length }}</span>
          </div>
        </div>
        <div class="rpt-hero-gen">
          生成于 {{ detail.asset_unit?.generated_at?.slice(0, 10) || '-' }} · v{{ detail.asset_unit?.version ?? '-' }}
          <el-button size="small" text type="primary" @click="back">← 返回</el-button>
        </div>
      </header>

      <div class="rpt-body">
        <aside class="rpt-toc">
          <nav>
            <div class="rpt-toc-title">目录</div>
            <a v-for="s in tocSections" :key="s.id" :href="'#' + s.id"
               :class="['rpt-toc-link', { active: activeSection === s.id }]"
               @click.prevent="scrollTo(s.id)">{{ s.icon }} {{ s.label }}</a>
          </nav>
        </aside>

        <main class="rpt-main">
          <!-- §1 裁决 -->
          <section id="sec-verdict" class="rpt-section">
            <h2 class="rpt-h2">📌 大类裁决</h2>
            <div class="rpt-verdict-card">
              <div v-if="stanceLabel" class="rpt-verdict-stance" :class="stanceCls">{{ stanceLabel }}</div>
              <div v-if="verdict.summary" class="rpt-line"><span class="rpt-line-label">📌 结论</span><p>{{ verdict.summary }}</p></div>
              <div v-if="verdict.situation" class="rpt-line"><span class="rpt-line-label">景气形势</span><p>{{ verdict.situation }}</p></div>
              <div v-if="verdict.direction" class="rpt-line"><span class="rpt-line-label">方向空间</span><p>{{ verdict.direction }}</p></div>
              <div v-if="verdict.trend" class="rpt-line"><span class="rpt-line-label">趋势</span><p>{{ verdict.trend }}</p></div>
            </div>
            <div v-if="verdict.risks?.length" class="rpt-risks">
              <div class="rpt-risks-head">⚠️ 主要风险（{{ verdict.risks.length }} 项）</div>
              <ol><li v-for="(r, i) in verdict.risks" :key="i">{{ scalarText(r) }}</li></ol>
            </div>
          </section>

          <!-- §2 权益分支：行业配比 -->
          <section v-if="detail.is_equity && detail.industries?.length" id="sec-industries" class="rpt-section">
            <h2 class="rpt-h2">🏭 行业配比（{{ detail.industries.length }} 个）</h2>
            <p class="rpt-appendix-desc">点击行业名查看该行业完整产业链分析。</p>
            <table class="rpt-table">
              <thead><tr><th>行业</th><th>目标权重</th><th>立场</th><th>方向</th><th>理由</th></tr></thead>
              <tbody>
                <tr v-for="(ind, i) in sortedIndustries" :key="i">
                  <td>
                    <router-link :to="`/portfolio/v4/industry/${encodeURIComponent(ind.industry)}`" class="rpt-link rpt-td-strong">{{ ind.industry }} →</router-link>
                  </td>
                  <td class="rpt-td-strong">{{ ind.target_weight }}%</td>
                  <td><el-tag size="small" :type="indStanceType(ind.stance || ind.direction)" effect="plain">{{ ind.stance || ind.direction || '-' }}</el-tag></td>
                  <td>{{ ind.direction || '-' }}</td>
                  <td class="rpt-ind-reason">{{ ind.reasoning }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <!-- §3 非权益分支：执行方案 plan -->
          <section v-if="!detail.is_equity && plan" id="sec-plan" class="rpt-section">
            <h2 class="rpt-h2">📋 执行方案</h2>
            <div v-if="plan.summary" class="rpt-line"><span class="rpt-line-label">方案摘要</span><p>{{ plan.summary }}</p></div>
            <div class="rpt-grid">
              <div v-if="plan.stance" class="rpt-cell"><div class="rpt-cell-label">立场</div><p>{{ plan.stance }}</p></div>
              <div v-if="plan.structure_target" class="rpt-cell"><div class="rpt-cell-label">结构目标</div><p>{{ plan.structure_target }}</p></div>
              <div v-if="plan.valuation_basis" class="rpt-cell full"><div class="rpt-cell-label">估值依据</div><p>{{ scalarText(plan.valuation_basis) }}</p></div>
              <div v-if="plan.duration_view" class="rpt-cell full"><div class="rpt-cell-label">久期观点</div><p>{{ plan.duration_view }}</p></div>
            </div>
            <!-- 持仓结构 / 工具组合 -->
            <div v-if="planInstruments.length" class="rpt-instr">
              <div class="rpt-list-head">🧩 工具组合 / 持仓结构</div>
              <table class="rpt-table">
                <thead><tr><th>工具</th><th>载体</th><th>建议占比</th><th>可交易</th><th>说明</th></tr></thead>
                <tbody>
                  <tr v-for="(it, i) in planInstruments" :key="i">
                    <td class="rpt-td-strong">{{ it.instrument }}</td>
                    <td>{{ it.vehicle || '-' }}</td>
                    <td>{{ it.suggest_pct != null ? it.suggest_pct + '%' : '-' }}</td>
                    <td>{{ it.tradable === false ? '否' : '是' }}</td>
                    <td>{{ it.reasoning }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <!-- action_plan（dict 或 string） -->
            <div v-if="plan.action_plan" class="rpt-actions" style="margin-top:14px">
              <div class="rpt-actions-head">✅ 行动计划</div>
              <p v-if="typeof plan.action_plan === 'string'" style="margin:0;font-size:13px;line-height:1.8;color:#4e5969">{{ plan.action_plan }}</p>
              <ul v-else style="margin:0;padding-left:20px">
                <li v-for="(v, k) in plan.action_plan" :key="k" style="font-size:13px;line-height:1.8;color:#4e5969"><b>{{ k }}：</b>{{ v }}</li>
              </ul>
            </div>
            <div v-if="plan.risk_flags?.length" class="rpt-risks" style="margin-top:14px">
              <div class="rpt-risks-head">⚠️ 风险提示</div>
              <ol><li v-for="(r, i) in plan.risk_flags" :key="i">{{ r }}</li></ol>
            </div>

            <!-- 可信度 / critic 评审（非权益 plan 内嵌，之前会丢） -->
            <div v-if="planCred || planCritic" class="rpt-cell full" style="margin-top:14px">
              <div class="rpt-cell-label">🎓 可信度与评审</div>
              <p v-if="planCred?.final_verdict || planCred?.score">
                {{ planCred?.final_verdict || '' }} {{ planCred?.score != null ? planCred.score + '分' : '' }}
                <span v-if="planCred?.reviewer"> · {{ planCred.reviewer }}</span>
              </p>
              <p v-if="planCred?.rationale" style="color:#606266">{{ planCred.rationale }}</p>
              <p v-if="planCritic?.final_verdict || planCritic?.final_score">
                critic：{{ planCritic?.final_verdict || '' }} {{ planCritic?.final_score != null ? planCritic.final_score + '分' : '' }}
              </p>
            </div>

            <!-- plan 内其余字段兜底（敏感性/可比/四维闸门/合规等，零丢失） -->
            <div v-if="planLeftover.length" style="margin-top:14px">
              <div class="rpt-list-head">📦 方案补充数据</div>
              <el-collapse>
                <el-collapse-item v-for="[k, v] in planLeftover" :key="k" :name="k">
                  <template #title><span class="rpt-appendix-key">{{ k }}</span></template>
                  <JsonTree :value="v" />
                </el-collapse-item>
              </el-collapse>
            </div>
          </section>

          <!-- §4 前瞻（若 verdict 带 forward_view） -->
          <section v-if="hasForward" id="sec-forward" class="rpt-section">
            <h2 class="rpt-h2">🔭 前瞻视野</h2>
            <JsonTree :value="forward" />
          </section>

          <!-- §5 反思 -->
          <section v-if="hasReflection" id="sec-reflection" class="rpt-section">
            <h2 class="rpt-h2">🔄 版本反思</h2>
            <div class="rpt-verdict-card">
              <div v-for="(v, k) in reflection" :key="k" class="rpt-line">
                <span class="rpt-line-label">{{ k }}</span><p>{{ scalarText(v) }}</p>
              </div>
            </div>
          </section>

          <!-- §6 附录 -->
          <section v-if="leftoverEntries.length" id="sec-appendix" class="rpt-section">
            <h2 class="rpt-h2">📦 完整数据附录</h2>
            <p class="rpt-appendix-desc">未在上方章节展示的全部原始字段，零信息丢失。</p>
            <el-collapse>
              <el-collapse-item v-for="[k, v] in leftoverEntries" :key="k" :name="k">
                <template #title><span class="rpt-appendix-key">{{ k }}</span></template>
                <JsonTree :value="v" />
              </el-collapse-item>
            </el-collapse>
          </section>
        </main>
      </div>
    </template>

    <div v-else class="rpt-empty">
      <el-empty :description="error || '未找到该大类分析'" />
      <el-button type="primary" @click="back">返回</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { portfolioV4Api, type AssetDetail } from '@/api/portfolioV4'
import { classLabel } from './assetClasses'
import JsonTree from './JsonTree.vue'
import './report-shared.css'

// assetClassProp：嵌入 V4Overview tab 时父级传入；独立路由页取 route.params
const props = defineProps<{ assetClassProp?: string }>()
const route = useRoute()
const router = useRouter()
const assetClass = computed(() => props.assetClassProp || (route.params.assetClass as string))
const detail = ref<AssetDetail | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load(ac: string) {
  if (!ac) return
  loading.value = true
  error.value = null
  detail.value = null
  try {
    const resp: any = await portfolioV4Api.getAssetDetail(ac)
    let d: any = resp
    if (d && d.data && typeof d.data === 'object') d = d.data
    detail.value = d && d.asset_class ? d : null
    if (!detail.value) error.value = resp?.message || '加载失败'
  } catch (e: any) {
    error.value = e?.message || String(e)
    detail.value = null
  } finally {
    loading.value = false
  }
}

const verdict = computed<any>(() => detail.value?.verdict || {})
const plan = computed<any>(() => detail.value?.plan || null)
const forward = computed<any>(() => verdict.value.forward_view || (plan.value?.forward_view_6dim) || null)
const reflection = computed<any>(() => verdict.value.reflection || {})
const hasForward = computed(() => forward.value && Object.keys(forward.value).length > 0)
const hasReflection = computed(() => reflection.value && Object.keys(reflection.value).length > 0)

const curWeight = computed(() => detail.value?.plan?.current_weight ?? null)
const tgtWeight = computed(() => detail.value?.plan?.target_weight ?? null)
const confidencePct = computed(() => {
  const c = verdict.value.confidence ?? plan.value?.confidence
  return c != null ? Math.round(c * 100) : null
})

const sortedIndustries = computed(() =>
  [...(detail.value?.industries || [])].sort((a: any, b: any) => (b.target_weight || 0) - (a.target_weight || 0))
)

const planInstruments = computed<any[]>(() => {
  const p = plan.value
  if (!p) return []
  return (p.holding_structure || p.instrument_mix || []) as any[]
})
const planCred = computed<any>(() => plan.value?.credibility || null)
const planCritic = computed<any>(() => plan.value?.critic_evaluation || null)

// plan 内已被专题章节消费的字段；其余进「方案补充数据」附录，杜绝嵌套丢失
const PLAN_CONSUMED = new Set<string>([
  'asset_class', 'summary', 'stance', 'structure_target', 'valuation_basis', 'duration_view',
  'holding_structure', 'instrument_mix', 'action_plan', 'risk_flags', 'forward_view_6dim',
  'current_weight', 'target_weight', 'confidence', 'credibility', 'critic_evaluation',
  'note', 'holding_only_note',
])
const planLeftover = computed(() => {
  const p: any = plan.value || {}
  const out: Array<[string, any]> = []
  for (const k of Object.keys(p)) {
    if (PLAN_CONSUMED.has(k)) continue
    const v = p[k]
    if (v == null || (Array.isArray(v) && v.length === 0)) continue
    out.push([k, v])
  }
  return out
})

// hero 配色：权益蓝、非权益青
const heroStyle = computed(() => ({
  '--rpt-hero': detail.value?.is_equity
    ? 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)'
    : 'linear-gradient(135deg, #134e5e 0%, #1c3d5a 100%)',
}))

// 立场
const STANCE_LABEL: Record<string, string> = {
  go: '看好 (Go)', nogo: '回避', bullish: '看多', bearish: '看空', neutral: '中性',
  slight_add: '小幅加配', add: '加配', reduce: '减配', hold: '维持',
}
const stanceLabel = computed(() => {
  const s = verdict.value.stance || plan.value?.stance || ''
  return STANCE_LABEL[s] || s
})
const stanceType = computed<any>(() => {
  const s = verdict.value.stance || plan.value?.stance || ''
  if (/go$|bullish|add/.test(s) && !/nogo/.test(s)) return 'success'
  if (/nogo|bearish|reduce/.test(s)) return 'danger'
  return 'warning'
})
const stanceCls = computed(() => {
  const s = verdict.value.stance || plan.value?.stance || ''
  if (/go$|bullish|add/.test(s) && !/nogo/.test(s)) return 'pos'
  if (/nogo|bearish|reduce/.test(s)) return 'neg'
  return 'neutral'
})
function indStanceType(s?: string): any {
  if (/go|bull|增持|看多/.test(s || '')) return 'success'
  if (/nogo|bear|减|回避/.test(s || '')) return 'danger'
  return 'info'
}

function scalarText(v: any): string {
  if (v == null) return '-'
  if (['string', 'number', 'boolean'].includes(typeof v)) return String(v)
  if (Array.isArray(v)) return v.map(scalarText).join('；')
  return v.summary || v.core_logic || v.value || JSON.stringify(v)
}

// TOC
const tocSections = computed(() => {
  const secs = [{ id: 'sec-verdict', icon: '📌', label: '大类裁决' }]
  if (detail.value?.is_equity && detail.value?.industries?.length) secs.push({ id: 'sec-industries', icon: '🏭', label: '行业配比' })
  if (!detail.value?.is_equity && plan.value) secs.push({ id: 'sec-plan', icon: '📋', label: '执行方案' })
  if (hasForward.value) secs.push({ id: 'sec-forward', icon: '🔭', label: '前瞻视野' })
  if (hasReflection.value) secs.push({ id: 'sec-reflection', icon: '🔄', label: '版本反思' })
  if (leftoverEntries.value.length) secs.push({ id: 'sec-appendix', icon: '📦', label: '完整数据附录' })
  return secs
})

// 附录兜底
const CONSUMED = new Set<string>([
  'asset_class', 'label', 'is_equity', 'max_drill_depth', 'asset_unit', 'verdict',
  'industries', 'equity_industries_unit', 'plan', 'plan_unit', 'tradable',
  'holding_only_exposure', 'analysts', 'debate_rounds',
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

// scrollspy
const activeSection = ref('')
let observer: IntersectionObserver | null = null
onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => { for (const e of entries) if (e.isIntersecting) activeSection.value = e.target.id },
    { rootMargin: '-80px 0px -60% 0px', threshold: 0.1 }
  )
})
onUnmounted(() => observer?.disconnect())
watch(loading, (v) => { if (!v) setTimeout(() => document.querySelectorAll('.rpt-section').forEach(el => observer?.observe(el)), 100) })
function scrollTo(id: string) { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); activeSection.value = id }
function back() { router.back() }

// label 兜底
watch(detail, (d) => { if (d && !d.label) (d as any).label = classLabel(d.asset_class) })

watch(assetClass, (ac) => { if (ac) load(ac) }, { immediate: true })
</script>

<style scoped>
.rpt-ind-reason { color: #606266; font-size: 12px; max-width: 360px; line-height: 1.6; }
.rpt-instr { margin-top: 16px; }
</style>
