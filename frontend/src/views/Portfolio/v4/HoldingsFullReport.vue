<template>
  <div class="rpt">
    <div v-if="loading" class="rpt-loading"><el-skeleton :rows="10" animated /></div>

    <template v-else-if="review">
      <header class="rpt-hero" style="--rpt-hero: linear-gradient(135deg, #232526 0%, #414345 100%)">
        <div class="rpt-hero-main">
          <h1 class="rpt-hero-title">
            我的持仓 <span class="rpt-hero-sub">组合完整体检</span>
          </h1>
          <div class="rpt-hero-meta">
            <span v-if="confidencePct != null" class="rpt-hero-score">组合置信度 {{ confidencePct }}%</span>
            <span v-if="review.as_of" class="rpt-hero-score">截至 {{ review.as_of }}</span>
          </div>
        </div>
        <div class="rpt-hero-kpi">
          <div class="rpt-kpi">
            <span class="rpt-kpi-label">组合总市值</span>
            <span class="rpt-kpi-val">{{ fmtWan(s.total_value) }}</span>
          </div>
          <div class="rpt-kpi">
            <span class="rpt-kpi-label">个股 / 基金</span>
            <span class="rpt-kpi-val">{{ s.total_stocks }} / {{ s.total_funds }}</span>
          </div>
          <div class="rpt-kpi">
            <span class="rpt-kpi-label">已分析</span>
            <span class="rpt-kpi-val rpt-kpi-green">{{ s.analyzed_count }}</span>
          </div>
          <div v-if="s.pending_actions" class="rpt-kpi">
            <span class="rpt-kpi-label">待处理动作</span>
            <span class="rpt-kpi-val rpt-kpi-red">{{ s.pending_actions }}</span>
          </div>
          <div v-if="review.equity_quota_v4 != null" class="rpt-kpi">
            <span class="rpt-kpi-label">权益额度</span>
            <span class="rpt-kpi-val">{{ review.equity_quota_v4 }}%</span>
          </div>
        </div>
        <div class="rpt-hero-gen">
          自上而下：大类 → 行业 → 个股，每层可点击钻取完整分析
        </div>
      </header>

      <div class="rpt-body">
        <aside class="rpt-toc">
          <nav>
            <div class="rpt-toc-title">目录</div>
            <a v-for="sec in tocSections" :key="sec.id" :href="'#' + sec.id"
               :class="['rpt-toc-link', { active: activeSection === sec.id }]"
               @click.prevent="scrollTo(sec.id)">{{ sec.icon }} {{ sec.label }}</a>
          </nav>
        </aside>

        <main class="rpt-main">
          <!-- §1 关键动作 + 风险 -->
          <section v-if="keyActions.length || keyRisks.length" id="sec-summary" class="rpt-section">
            <h2 class="rpt-h2">🎯 组合关键动作与风险</h2>
            <div v-if="keyActions.length" class="rpt-actions">
              <div class="rpt-actions-head">✅ 关键动作（按优先级）</div>
              <ol><li v-for="(a, i) in keyActions" :key="i">{{ a }}</li></ol>
            </div>
            <div v-if="keyRisks.length" class="rpt-risks" style="margin-top:14px">
              <div class="rpt-risks-head">⚠️ 组合级风险（{{ keyRisks.length }} 项）</div>
              <ol><li v-for="(r, i) in keyRisks" :key="i">{{ r }}</li></ol>
            </div>
          </section>

          <!-- §2 大类配比树 -->
          <section v-if="assetTree.length" id="sec-tree" class="rpt-section">
            <h2 class="rpt-h2">🗂️ 大类配比（当前 vs 目标）</h2>
            <p class="rpt-appendix-desc">点击大类名查看完整分析；展开看下属行业与持仓。</p>
            <div v-for="node in assetTree" :key="node.key" class="rpt-tree-node">
              <div class="rpt-tree-head">
                <div class="rpt-tree-name">
                  <router-link v-if="node.has_class_analysis" :to="`/portfolio/v4/asset/${node.key}`" class="rpt-link">{{ node.label }} →</router-link>
                  <span v-else>{{ node.label }}</span>
                </div>
                <div class="rpt-tree-bar-wrap">
                  <div class="rpt-tree-bar">
                    <div class="rpt-tree-bar-cur" :style="{ width: barW(node.current_pct) }"></div>
                    <div v-if="node.target_pct != null" class="rpt-tree-bar-tgt" :style="{ left: barW(node.target_pct) }"></div>
                  </div>
                  <span class="rpt-tree-pct">
                    {{ fmtPct(node.current_pct) }}
                    <span v-if="node.target_pct != null" class="rpt-tree-tgt-txt">→ {{ fmtPct(node.target_pct) }}</span>
                  </span>
                </div>
                <el-tag v-if="node.action" size="small" :type="actionType(node.action)" effect="plain">{{ actionLabel(node.action) }}</el-tag>
              </div>
              <!-- 配比理由（当前/目标/gap/宏观/资金流/政策/风险）—— 8 大类皆有，曾全丢 -->
              <div v-if="hasReason(node.reasoning)" class="rpt-tree-reason">
                <span v-for="(v, k) in reasonPairs(node.reasoning)" :key="k" class="rpt-reason-item">
                  <b>{{ reasonLabel(k) }}：</b>{{ v }}
                </span>
              </div>
              <!-- 下属行业 -->
              <div v-if="node.industries?.length" class="rpt-tree-children">
                <span v-for="(ind, i) in node.industries" :key="i" class="rpt-tree-ind">
                  <router-link v-if="ind.has_industry_analysis" :to="`/portfolio/v4/industry/${encodeURIComponent(ind.name)}`" class="rpt-link">{{ ind.name }}</router-link>
                  <span v-else>{{ ind.name }}</span>
                  <em>{{ fmtWan(ind.total_value) }}</em>
                </span>
              </div>
            </div>
          </section>

          <!-- §3 行业目标配比 -->
          <section v-if="review.industry_allocations?.length" id="sec-indalloc" class="rpt-section">
            <h2 class="rpt-h2">🏭 行业目标配比（权益内）</h2>
            <table class="rpt-table">
              <thead><tr><th>行业</th><th>目标权重</th><th>立场</th><th>理由</th></tr></thead>
              <tbody>
                <tr v-for="(ind, i) in sortedIndAlloc" :key="i">
                  <td><router-link :to="`/portfolio/v4/industry/${encodeURIComponent(ind.industry)}`" class="rpt-link rpt-td-strong">{{ ind.industry }} →</router-link></td>
                  <td class="rpt-td-strong">{{ ind.target_weight }}%</td>
                  <td><el-tag size="small" :type="indStanceType(ind.stance || ind.direction)" effect="plain">{{ ind.stance || ind.direction || '-' }}</el-tag></td>
                  <td class="rpt-ind-reason">{{ ind.reasoning }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <!-- §4 资金流向 -->
          <section v-if="hasFlow" id="sec-flow" class="rpt-section">
            <h2 class="rpt-h2">💰 资金流向（这笔钱怎么动）</h2>
            <div class="rpt-flow-grid">
              <div class="rpt-flow-col">
                <div class="rpt-list-head">📤 资金来源（减仓释放）</div>
                <ul class="rpt-flow-list">
                  <li v-for="(f, i) in flow.sources" :key="i">
                    <span>{{ f.desc }}</span><b class="rpt-flow-out">{{ fmtWan(f.amount) }}</b>
                  </li>
                </ul>
              </div>
              <div class="rpt-flow-col">
                <div class="rpt-list-head">📥 资金去向（加仓投入）</div>
                <ul class="rpt-flow-list">
                  <li v-for="(f, i) in flow.uses" :key="i">
                    <span>{{ f.desc }}</span><b class="rpt-flow-in">{{ fmtWan(f.amount) }}</b>
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <!-- §5 基金分组 -->
          <section v-if="review.fund_groups?.length" id="sec-funds" class="rpt-section">
            <h2 class="rpt-h2">📦 基金分组（主题去重）</h2>
            <div v-for="(g, i) in review.fund_groups" :key="i" class="rpt-fund-card">
              <div class="rpt-fund-head">
                <b>{{ g.theme }}</b>
                <span class="rpt-fund-meta">{{ g.fund_count }} 只 · {{ fmtWan(g.total_mv) }}</span>
                <el-tag v-if="g.action" size="small" effect="plain">{{ g.action }}</el-tag>
              </div>
              <div class="rpt-fund-cols">
                <div v-if="g.keep?.length" class="rpt-fund-keep">
                  <span class="rpt-fund-tag keep">保留</span>
                  <span v-for="(f, j) in g.keep" :key="j" class="rpt-fund-chip">{{ f.name }} <em>{{ fmtWan(f.mv) }}</em></span>
                </div>
                <div v-if="g.sell?.length" class="rpt-fund-sell">
                  <span class="rpt-fund-tag sell">调出</span>
                  <span v-for="(f, j) in g.sell" :key="j" class="rpt-fund-chip">{{ f.name }} <em>{{ fmtWan(f.mv) }}</em></span>
                </div>
              </div>
            </div>
          </section>

          <!-- §6 风格/地域 -->
          <section v-if="hasStyle" id="sec-style" class="rpt-section">
            <h2 class="rpt-h2">🌐 风格 / 地域分布</h2>
            <div class="rpt-grid">
              <div v-for="(v, k) in s.style_region" :key="k" class="rpt-cell">
                <div class="rpt-cell-label">{{ k }}</div>
                <p class="rpt-td-strong">{{ fmtWan(v) }}（{{ stylePct(v) }}%）</p>
              </div>
            </div>
            <p v-if="s.config_note" class="rpt-appendix-desc" style="margin-top:12px">{{ s.config_note }}</p>
          </section>

          <!-- §7 附录 -->
          <section v-if="leftoverEntries.length" id="sec-appendix" class="rpt-section">
            <h2 class="rpt-h2">📦 完整数据附录</h2>
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
      <el-empty :description="error || '未找到持仓体检数据'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { portfolioV4Api, type HoldingsReview } from '@/api/portfolioV4'
import JsonTree from './JsonTree.vue'
import './report-shared.css'

const review = ref<HoldingsReview | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const resp: any = await portfolioV4Api.getHoldingsReview()
    let d: any = resp
    if (d && d.data && typeof d.data === 'object') d = d.data
    review.value = d && d.summary ? d : null
    if (!review.value) error.value = resp?.message || '加载失败'
  } catch (e: any) {
    error.value = e?.message || String(e)
    review.value = null
  } finally {
    loading.value = false
  }
}

const s = computed<any>(() => review.value?.summary || {})
const assetTree = computed<any[]>(() => review.value?.asset_tree || [])
const flow = computed<any>(() => review.value?.capital_flow || { sources: [], uses: [] })
const hasFlow = computed(() => (flow.value.sources?.length || 0) + (flow.value.uses?.length || 0) > 0)
const keyActions = computed<string[]>(() => (review.value as any)?.portfolio_key_actions || [])
const keyRisks = computed<string[]>(() => (review.value as any)?.portfolio_key_risks || [])
const confidencePct = computed(() => {
  const c = (review.value as any)?.portfolio_confidence
  return c != null ? Math.round(c * 100) : null
})
const hasStyle = computed(() => s.value.style_region && Object.keys(s.value.style_region).length > 0)
const sortedIndAlloc = computed(() =>
  [...((review.value as any)?.industry_allocations || [])].sort((a: any, b: any) => (b.target_weight || 0) - (a.target_weight || 0))
)

// 格式化
function fmtWan(v?: number): string {
  if (v == null) return '-'
  const wan = v / 10000
  if (Math.abs(wan) >= 1) return wan.toFixed(1) + '万'
  return v.toFixed(0) + '元'
}
function fmtPct(v?: number): string { return v != null ? v.toFixed(1) + '%' : '-' }
function barW(v?: number): string { return Math.min(100, Math.max(0, v || 0)) + '%' }
function stylePct(v: number): string {
  const tot = Object.values(s.value.style_region || {}).reduce((a: number, b: any) => a + (b || 0), 0) as number
  return tot ? ((v / tot) * 100).toFixed(0) : '0'
}
const ACTION_LABEL: Record<string, string> = { add: '加配', reduce: '减配', hold: '维持', zero: '清零' }
function actionLabel(a?: string): string { return ACTION_LABEL[a || ''] || a || '' }
function actionType(a?: string): any {
  if (a === 'add') return 'success'
  if (a === 'reduce' || a === 'zero') return 'danger'
  return 'info'
}
function indStanceType(st?: string): any {
  if (/go|bull|增持|看多/.test(st || '')) return 'success'
  if (/nogo|bear|减|回避/.test(st || '')) return 'danger'
  return 'info'
}
// 配比理由：只展示文字型解释字段（current_pct/target_pct 已在进度条体现，不重复）
const REASON_LABEL: Record<string, string> = {
  gap: '缺口', macro: '宏观', flow: '资金流', policy: '政策', risk: '风险',
}
function reasonPairs(r: any): Record<string, any> {
  if (!r || typeof r !== 'object') return {}
  const out: Record<string, any> = {}
  for (const k of Object.keys(r)) {
    if (k === 'current_pct' || k === 'target_pct') continue
    const v = r[k]
    if (v == null || v === '') continue
    out[k] = v
  }
  return out
}
function hasReason(r: any): boolean { return Object.keys(reasonPairs(r)).length > 0 }
function reasonLabel(k: string): string { return REASON_LABEL[k] || k }

// TOC
const tocSections = computed(() => {
  const secs: Array<{ id: string; icon: string; label: string }> = []
  if (keyActions.value.length || keyRisks.value.length) secs.push({ id: 'sec-summary', icon: '🎯', label: '关键动作/风险' })
  if (assetTree.value.length) secs.push({ id: 'sec-tree', icon: '🗂️', label: '大类配比' })
  if (sortedIndAlloc.value.length) secs.push({ id: 'sec-indalloc', icon: '🏭', label: '行业配比' })
  if (hasFlow.value) secs.push({ id: 'sec-flow', icon: '💰', label: '资金流向' })
  if (review.value?.fund_groups?.length) secs.push({ id: 'sec-funds', icon: '📦', label: '基金分组' })
  if (hasStyle.value) secs.push({ id: 'sec-style', icon: '🌐', label: '风格地域' })
  if (leftoverEntries.value.length) secs.push({ id: 'sec-appendix', icon: '📦', label: '完整数据附录' })
  return secs
})

// 附录兜底
const CONSUMED = new Set<string>([
  'as_of', 'summary', 'asset_tree', 'capital_flow', 'fund_groups', 'industry_allocations',
  'portfolio_key_actions', 'portfolio_key_risks', 'portfolio_confidence',
  'equity_quota_v4', 'asset_class_targets', 'indirect_holdings',
])
const leftoverEntries = computed(() => {
  const d: any = review.value || {}
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
  load()
})
onUnmounted(() => observer?.disconnect())
watch(loading, (v) => { if (!v) setTimeout(() => document.querySelectorAll('.rpt-section').forEach(el => observer?.observe(el)), 100) })
function scrollTo(id: string) { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); activeSection.value = id }
</script>

<style scoped>
.rpt-ind-reason { color: #606266; font-size: 12px; max-width: 360px; line-height: 1.6; }

/* 大类树 */
.rpt-tree-node { padding: 12px 0; border-bottom: 1px solid #f0f2f5; }
.rpt-tree-head { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.rpt-tree-name { width: 110px; font-size: 14px; font-weight: 600; color: #303133; flex-shrink: 0; }
.rpt-tree-bar-wrap { flex: 1; min-width: 200px; display: flex; align-items: center; gap: 10px; }
.rpt-tree-bar { position: relative; flex: 1; height: 14px; background: #f0f2f5; border-radius: 7px; overflow: visible; }
.rpt-tree-bar-cur { height: 100%; background: linear-gradient(90deg, #409eff, #66b1ff); border-radius: 7px; }
.rpt-tree-bar-tgt { position: absolute; top: -3px; width: 2px; height: 20px; background: #f56c6c; }
.rpt-tree-pct { font-size: 12.5px; color: #606266; white-space: nowrap; min-width: 110px; }
.rpt-tree-tgt-txt { color: #f56c6c; font-weight: 600; }
.rpt-tree-reason { margin-top: 8px; padding-left: 110px; display: flex; flex-wrap: wrap; gap: 12px; }
.rpt-reason-item { font-size: 12px; color: #606266; line-height: 1.6; }
.rpt-reason-item b { color: #909399; }
.rpt-tree-children { margin-top: 8px; padding-left: 110px; display: flex; flex-wrap: wrap; gap: 8px; }
.rpt-tree-ind { font-size: 12px; background: #f5f7fa; padding: 3px 10px; border-radius: 12px; color: #606266; }
.rpt-tree-ind em { color: #909399; font-style: normal; margin-left: 4px; }

/* 资金流向 */
.rpt-flow-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.rpt-flow-list { list-style: none; padding: 0; margin: 0; }
.rpt-flow-list li { display: flex; justify-content: space-between; gap: 10px; font-size: 13px; padding: 8px 0; border-bottom: 1px dashed #f0f2f5; color: #4e5969; line-height: 1.6; }
.rpt-flow-out { color: #cf1322; white-space: nowrap; }
.rpt-flow-in { color: #389e0d; white-space: nowrap; }

/* 基金分组 */
.rpt-fund-card { background: #fafbfc; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; }
.rpt-fund-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.rpt-fund-head b { font-size: 14px; color: #303133; }
.rpt-fund-meta { font-size: 12px; color: #909399; }
.rpt-fund-cols { display: flex; flex-direction: column; gap: 6px; }
.rpt-fund-keep, .rpt-fund-sell { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.rpt-fund-tag { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px; }
.rpt-fund-tag.keep { background: #f6ffed; color: #389e0d; }
.rpt-fund-tag.sell { background: #fff1f0; color: #cf1322; }
.rpt-fund-chip { font-size: 12px; background: #fff; border: 1px solid #ebeef5; padding: 2px 8px; border-radius: 4px; color: #606266; }
.rpt-fund-chip em { font-style: normal; color: #909399; margin-left: 4px; }

@media (max-width: 900px) {
  .rpt-flow-grid { grid-template-columns: 1fr; }
  .rpt-tree-children { padding-left: 0; }
  .rpt-tree-name { width: auto; }
}
</style>
