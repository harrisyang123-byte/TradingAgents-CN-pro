<template>
  <div class="portfolio-overview page-content">
    <!-- 顶部统计 -->
    <div v-if="overview" style="display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap;">
      <div class="card" style="flex:1; min-width:140px;">
        <div class="card-body" style="text-align:center; padding:14px;">
          <div style="font-size:22px; font-weight:700; color:#409eff;">{{ overview.total_industries || 0 }}</div>
          <div style="font-size:12px; color:#909399; margin-top:4px;">总行业数</div>
        </div>
      </div>
      <div class="card" style="flex:1; min-width:140px;">
        <div class="card-body" style="text-align:center; padding:14px;">
          <div style="font-size:22px; font-weight:700; color:#67c23a;">{{ overview.covered_count || 0 }}</div>
          <div style="font-size:12px; color:#909399; margin-top:4px;">已覆盖</div>
        </div>
      </div>
      <div class="card" style="flex:1; min-width:140px;">
        <div class="card-body" style="text-align:center; padding:14px;">
          <div style="font-size:22px; font-weight:700; color:#e6a23c;">{{ overview.stale_count || 0 }}</div>
          <div style="font-size:12px; color:#909399; margin-top:4px;">待更新</div>
        </div>
      </div>
      <div class="card" style="flex:1; min-width:140px;">
        <div class="card-body" style="text-align:center; padding:14px;">
          <div style="font-size:22px; font-weight:700;">{{ overview.data_score ? (overview.data_score * 100).toFixed(0) + '%' : '--' }}</div>
          <div style="font-size:12px; color:#909399; margin-top:4px;">数据质量</div>
        </div>
      </div>
    </div>

    <!-- 行业矩阵 -->
    <div class="card">
      <div class="card-header">
        <span>行业配置矩阵</span>
        <button style="font-size:12px; padding:4px 12px; border:1px solid #dcdfe6; border-radius:4px; cursor:pointer; background:#fff;" @click="loadOverview(true)" :disabled="loading">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
      <div class="card-body" style="padding:0;">
        <div v-if="loading" style="text-align:center; padding:40px; color:#909399;">加载中...</div>
        <div v-else-if="!overview || !filteredMatrix.length" class="empty-state">
          <div class="empty-title">暂无行业数据</div>
          <div class="empty-desc">请先运行组合顾问分析</div>
        </div>
        <table v-else class="industry-table">
          <thead>
            <tr>
              <th>行业</th>
              <th>市场</th>
              <th>景气</th>
              <th>现持仓%</th>
              <th>目标%</th>
              <th>操作</th>
              <th>调仓金额</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in filteredMatrix" :key="row.industry">
            <tr
              class="industry-row"
              :class="[row.go_nogo === 'GO' ? 'row-go' : (row.go_nogo === 'NOGO' ? 'row-nogo' : ''), expandedRow === row.industry ? 'row-expanded' : '']"
              @click="toggleRowExpand(row)"
            >
              <td>
                <span class="ind-name">{{ row.industry }}</span>
                <span v-if="row.source" class="ind-source-tag" :class="'src-' + row.source">{{ sourceLabel(row.source) }}</span>
              </td>
              <td style="color:#606266; font-size:12px;">{{ row.market || '--' }}</td>
              <td>
                <span v-if="row.vitality_level" class="v-tag" :class="'v-' + row.vitality_level">{{ row.vitality_level }}</span>
                <span v-else class="text-muted">--</span>
              </td>
              <td>
                <div class="weight-transition">
                  <span>{{ (row.holdings_weight || 0).toFixed(1) }}%</span>
                  <span class="arrow">→</span>
                  <span class="target">{{ (row.target_weight || 0).toFixed(1) }}%</span>
                </div>
              </td>
              <td style="color:#909399; font-size:12px;">
                <span v-if="row.delta > 0" style="color:#67c23a;">+{{ row.delta.toFixed(1) }}%</span>
                <span v-else-if="row.delta < 0" style="color:#f56c6c;">{{ row.delta.toFixed(1) }}%</span>
                <span v-else>0%</span>
              </td>
              <td>
                <span v-if="row.industry === '现金'" class="go-badge go-badge-hold">现金</span>
                <span v-else-if="row.target_weight === 0 && row.holdings_weight > 0" class="go-badge go-badge-nogo">清仓</span>
                <span v-else-if="row.delta > 0" class="go-badge go-badge-go">{{ row.go_nogo === 'GO' ? 'GO ' : '' }}加仓</span>
                <span v-else-if="row.delta < 0" class="go-badge go-badge-nogo">{{ row.go_nogo === 'NOGO' ? 'NOGO ' : '' }}减仓</span>
                <span v-else class="go-badge go-badge-hold">持有</span>
              </td>
              <td style="font-size:13px;">
                <span v-if="row.delta !== 0">{{ formatMoney(actionAmount(row)) }}</span>
                <span v-else class="text-muted">--</span>
              </td>
            </tr>
            <tr v-if="expandedRow === row.industry && row.reasoning" class="reasoning-row">
              <td colspan="7" class="reasoning-cell">{{ row.reasoning }}</td>
            </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 分析师辩论历程 -->
    <div v-if="latestAdvice" class="card mt-4 debate-card">
      <div class="card-header debate-header" @click="debateCollapsed = !debateCollapsed" style="cursor:pointer;">
        <span>分析师辩论历程</span>
        <span class="collapse-arrow" :class="debateCollapsed ? '' : 'open'">▸</span>
      </div>
      <div v-if="!debateCollapsed">
        <div class="debate-tabs">
          <button v-for="tab in debateTabs" :key="tab.key" class="debate-tab" :class="activeDebateTab === tab.key ? 'active' : ''" @click="activeDebateTab = tab.key">{{ tab.label }}</button>
        </div>
        <div class="debate-content">
          <pre v-if="activeDebateTab === 'market'">{{ latestAdvice.market_debate_history || '暂无市场研判记录' }}</pre>
          <pre v-else-if="activeDebateTab === 'stock'">{{ latestAdvice.stock_debate_history || '暂无个股辩论记录' }}</pre>
          <pre v-else>{{ latestAdvice.debate_history || '暂无综合裁决记录' }}</pre>
        </div>
      </div>
    </div>

    <!-- 历史建议 -->
    <div class="card mt-4">
      <div class="card-header">历史分析记录</div>
      <div v-if="!adviceHistory.length" class="empty-state">
        <div class="empty-title">暂无历史记录</div>
        <div class="empty-desc">分析完成后将在此显示</div>
      </div>
      <div v-else>
        <div
          v-for="adv in adviceHistory"
          :key="adv.advice_id"
          class="history-card"
          :class="latestAdvice && latestAdvice.advice_id === adv.advice_id ? 'history-card-selected' : ''"
          @click="selectAdvice(adv)"
        >
          <div class="history-header">
            <span class="history-date">{{ formatDateTime(adv.created_at) }}</span>
            <span style="font-size:11px; padding:2px 8px; border-radius:3px; background:#f0f9eb; color:#67c23a;">{{ adv.status }}</span>
          </div>
          <div class="history-summary">
            {{ (adv.prescription || []).length }} 条处方
            · {{ (adv as any).selected_industries?.length || (adv as any).market_intel?.industries?.length || 0 }} 个行业
            <span v-if="(adv as any).total_assets_snapshot"> · {{ formatMoney((adv as any).total_assets_snapshot) }} 元</span>
            · 耗时 {{ adv.elapsed_seconds ? (adv.elapsed_seconds / 60).toFixed(0) + ' 分钟' : '--' }}
          </div>
        </div>
      </div>
    </div>

    <!-- 行业详情抽屉 -->
    <div v-if="showIndustryDrawer && selectedIndustry" style="position:fixed; top:0; right:0; width:520px; height:100vh; background:#fff; box-shadow:-4px 0 12px rgba(0,0,0,0.12); z-index:1000; overflow-y:auto; padding:24px;">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
        <span style="font-size:16px; font-weight:600;">{{ selectedIndustry.industry }}</span>
        <button style="border:none; background:none; font-size:18px; cursor:pointer; color:#909399;" @click="showIndustryDrawer = false">×</button>
      </div>

      <div class="industry-snapshot">
        <div class="snap-row">
          <span class="snap-label">{{ selectedIndustry.industry }}</span>
          <span v-if="selectedIndustry.lifecycle" class="lifecycle-tag">{{ selectedIndustry.lifecycle }}</span>
          <span class="snap-money">{{ formatMoney(actionAmount(selectedIndustry)) }} 元</span>
        </div>
        <div style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;">
          <span>当前 {{ (selectedIndustry.holdings_weight || 0).toFixed(1) }}%</span>
          <span style="color:#c0c4cc;">→</span>
          <span style="color:#409eff; font-weight:600;">目标 {{ (selectedIndustry.target_weight || 0).toFixed(1) }}%</span>
        </div>
      </div>

      <!-- 标的处方列表 -->
      <div v-if="industryPositions.length" class="rx-section">
        <div class="rx-title">处方明细</div>
        <div v-for="pos in industryPositions" :key="pos.code" class="rx-card">
          <!-- 行1: 名称 + 代码 + 操作 + 盈亏 + PE -->
          <div class="rx-row1">
            <div style="display:flex; align-items:center; gap:6px; flex:1; min-width:0;">
              <span class="rx-name">{{ pos.name || pos.code }}</span>
              <span class="rx-code">{{ pos.code }}</span>
              <span :class="'action action-' + (pos.action === 'buy' || pos.action === 'add' || pos.action === 'new_position' ? 'buy' : pos.action === 'sell' || pos.action === 'reduce' ? 'sell' : 'hold')">
                {{ actionLabel(pos.action) }}
              </span>
            </div>
            <div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">
              <span v-if="pos.pnl_pct !== undefined && pos.pnl_pct !== null"
                :style="pos.pnl_pct >= 0 ? 'color:#f56c6c; font-size:12px; font-weight:600;' : 'color:#67c23a; font-size:12px; font-weight:600;'">
                {{ pos.pnl_pct >= 0 ? '+' : '' }}{{ (pos.pnl_pct || 0).toFixed(1) }}%
              </span>
              <span v-if="pos.pe_data && pos.pe_data.pe_percentile_5y !== undefined"
                class="pe-badge"
                :class="pos.pe_data.pe_percentile_5y > 80 ? 'pe-high' : pos.pe_data.pe_percentile_5y < 30 ? 'pe-low' : 'pe-mid'">
                PE {{ pos.pe_data.pe_percentile_5y.toFixed(0) }}%ile
              </span>
            </div>
          </div>
          <!-- 行2: 仓位变动 + 调仓金额 + 时机 -->
          <div class="rx-row2">
            <span class="pos-change">{{ (pos.current_weight || 0).toFixed(1) }}% → {{ (pos.target_weight || 0).toFixed(1) }}%</span>
            <span class="capital-amount">{{ formatMoney(calcCapital(pos)) }} 元</span>
            <span v-if="pos.timing" class="timing-badge" :class="'timing-' + pos.timing">{{ timingLabel(pos.timing) }}</span>
            <span v-if="pos.suggested_price" style="font-size:12px; color:#409eff;">参考价 {{ pos.suggested_price }}</span>
          </div>
          <!-- 行3: reasoning -->
          <div v-if="pos.reasoning" class="reasoning-text" style="-webkit-line-clamp:3; display:-webkit-box; -webkit-box-orient:vertical; overflow:hidden;">{{ pos.reasoning }}</div>
        </div>
      </div>
      <div v-else style="color:#909399; font-size:13px; margin-top:12px;">暂无处方明细</div>
    </div>
    <!-- 遮罩 -->
    <div v-if="showIndustryDrawer" style="position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.3); z-index:999;" @click="showIndustryDrawer = false"></div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { portfolioApi, type PortfolioAdvice, type IndustryOverviewRow, type AdviceItem } from '@/api/paper'
import { usePageCache } from '@/composables/usePageCache'

// --- state ---
const loading = ref(false)
const overview = ref<any>(null)
const { loadWithCache, forceRefresh } = usePageCache()
const adviceHistory = ref<PortfolioAdvice[]>([])

const showIndustryDrawer = ref(false)
const selectedIndustry = ref<IndustryOverviewRow | null>(null)
const expandedRow = ref<string | null>(null)

const latestAdvice = ref<any>(null)
const debateCollapsed = ref(true)
const activeDebateTab = ref('market')
const debateTabs = [
  { key: 'market', label: '市场研判（L1）' },
  { key: 'stock', label: '个股辩论（L3）' },
  { key: 'final', label: '综合裁决' },
]

// --- filtered matrix (exclude 现金 for display, show cash separately) ---
const filteredMatrix = computed(() => {
  if (!overview.value?.matrix) return []
  return overview.value.matrix.filter((r: IndustryOverviewRow) => r.industry !== '现金')
})

// --- industry positions (from latest advice prescription) ---
const industryPositions = computed(() => {
  if (!selectedIndustry.value) return []
  return selectedIndustry.value.positions_detail || []
})

// --- helpers ---
function actionAmount(row: IndustryOverviewRow): number {
  const total = overview.value?.total_assets || 0
  const diff = (row.target_weight || 0) - (row.holdings_weight || 0)
  return Math.abs(roundMoney(diff / 100 * total))
}
function formatMoney(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toFixed(0)
}
function roundMoney(n: number): number {
  return Math.round(n / 100) * 100
}
function formatPrice(epr: any): string {
  if (Array.isArray(epr) && epr.length >= 2) return `${epr[0]} - ${epr[1]}`
  if (epr?.low && epr?.high) return `${epr.low} - ${epr.high}`
  return `${epr}`
}
function formatDateTime(utcStr?: string): string {
  if (!utcStr) return '--'
  return new Date(utcStr).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}
function sourceLabel(s: string): string {
  const m: Record<string, string> = { holding: '持仓', watchlist: '关注', vitality: '景气' }
  return m[s] || s
}

function actionLabel(a: string): string {
  const m: Record<string, string> = { buy: '买入', add: '加仓', reduce: '减仓', sell: '卖出', hold: '持有', new_position: '建仓' }
  return m[a?.toLowerCase()] || a || '--'
}
function buildStrategyLabel(s: string): string {
  const m: Record<string, string> = { immediate: '立即', batch: '分批', conditional: '条件' }
  return m[s] || s
}
function calcCapital(pos: any): number {
  const total = overview.value?.total_assets || 0
  const delta = (pos.target_weight || 0) - (pos.current_weight || 0)
  return Math.abs(roundMoney(delta / 100 * total))
}
function timingLabel(t: string): string {
  const m: Record<string, string> = { immediate: '立即建仓', batch: '分批建仓', conditional: '条件建仓', wait: '等待时机' }
  return m[t] || t
}

function openIndustryDrawer(row: IndustryOverviewRow) {
  selectedIndustry.value = row
  showIndustryDrawer.value = true
}

function toggleRowExpand(row: IndustryOverviewRow) {
  if (expandedRow.value === row.industry) {
    expandedRow.value = null
  } else {
    expandedRow.value = row.industry
    openIndustryDrawer(row)
  }
}

function selectAdvice(adv: PortfolioAdvice) {
  latestAdvice.value = adv
  debateCollapsed.value = false
  openAdviceDetail(adv)
}

function openAdviceDetail(adv: PortfolioAdvice) {
  // Load overview with this advice's data
  loadOverview(false, adv)
}

// --- data loading ---
async function loadOverview(force = false, adv?: PortfolioAdvice) {
  loading.value = true
  try {
    const fn = force ? forceRefresh : loadWithCache
    overview.value = await fn('overview', async () => {
      const res = await portfolioApi.getPortfolioOverview()
      if (res.success) return res.data
      throw new Error('API failed')
    })
    // If we have a specific advice, load its prescription into the matrix
    if (adv) {
      // merge prescription into matrix as positions_detail
      const rx = adv.prescription || []
      const byIndustry: Record<string, AdviceItem[]> = {}
      for (const item of rx) {
        const ib = (item as any).industry_bucket || '其他'
        byIndustry[ib] = byIndustry[ib] || []
        byIndustry[ib].push(item)
      }
      if (overview.value?.matrix) {
        for (const row of overview.value.matrix) {
          row.positions_detail = byIndustry[row.industry] || []
        }
      }
    }
  } catch { /* ignore */ }
  loading.value = false
}

async function loadHistory() {
  try {
    adviceHistory.value = await loadWithCache('advice-history', async () => {
      const res = await portfolioApi.getAdviceHistory(1, 20)
      if (res.success) return (res.data.items || []).filter((a: PortfolioAdvice) => a.status === 'COMPLETED')
      throw new Error('API failed')
    })
    if (adviceHistory.value.length > 0) {
      latestAdvice.value = adviceHistory.value[0]
    }
  } catch { /* ignore */ }
}

onMounted(() => {
  loadOverview()
  loadHistory()
})
</script>

<style scoped>
.portfolio-overview { max-width: 1400px; margin: 0 auto; }
.page-content { padding: 20px; }
.card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 6px; }
.card-header { padding: 14px 20px; font-weight: 600; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; justify-content: space-between; }
.card-body { padding: 20px; }
.industry-table { width: 100%; border-collapse: collapse; }
.industry-table th { text-align: left; padding: 10px 14px; font-size: 12px; color: #909399; border-bottom: 1px solid #eee; white-space: nowrap; }
.industry-table td { padding: 12px 14px; border-bottom: 1px solid #f5f5f5; font-size: 13px; }
.industry-row { cursor: pointer; transition: background 0.15s; }
.industry-row:hover { background: #f5f7fa; }
.row-go { border-left: 3px solid #67c23a; }
.row-nogo { border-left: 3px solid #f56c6c; }

.ind-name { font-weight: 600; margin-right: 6px; }
.ind-source-tag { font-size: 10px; padding: 1px 5px; border-radius: 3px; }
.src-holding { background: #ecf5ff; color: #409eff; }
.src-watchlist { background: #f0f9eb; color: #67c23a; }
.src-vitality { background: #fdf6ec; color: #e6a23c; }

.weight-transition .arrow { margin: 0 6px; color: #c0c4cc; font-size: 11px; }
.weight-transition .target { color: #409eff; font-weight: 600; }

.v-tag { font-size: 11px; padding: 2px 8px; border-radius: 3px; font-weight: 600; }
.v-强烈看好, .v-看好 { background: #f0f9eb; color: #67c23a; }
.v-中性 { background: #f5f7fa; color: #909399; }
.v-看空 { background: #fef0f0; color: #f56c6c; }

.lifecycle-tag { font-size: 11px; color: #e6a23c; background: #fdf6ec; padding: 2px 6px; border-radius: 3px; }

.action { font-size: 12px; font-weight: 600; white-space: nowrap; }
.action-buy { color: #e6a23c; }
.action-sell { color: #409eff; }
.action-hold { color: #909399; }

.industry-snapshot { padding: 16px 0; border-bottom: 1px solid #eee; margin-bottom: 12px; }
.snap-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.snap-label { font-size: 15px; font-weight: 600; }
.snap-money { margin-left: auto; }

.reasoning-text { padding: 8px 0; font-size: 13px; color: #606266; line-height: 1.7; white-space: pre-wrap; }

.rx-section { margin-top: 16px; }
.rx-title { font-weight: 600; margin-bottom: 10px; font-size: 14px; }
.rx-name { font-weight: 600; font-size: 13px; }
.rx-code { font-size: 11px; color: #909399; }

.strat-tag { font-size: 11px; padding: 1px 6px; border-radius: 3px; }
.strat-immediate { background: #fef0f0; color: #f56c6c; }
.strat-batch { background: #fdf6ec; color: #e6a23c; }
.strat-conditional { background: #f0f5ff; color: #409eff; }

.expand-content { font-size: 12px; padding: 8px; }
.expand-block { margin-bottom: 10px; }
.expand-block strong { display: block; margin-bottom: 4px; color: #303133; }
.batch-line { color: #606266; margin: 2px 0; padding-left: 12px; }

.history-card { padding: 12px 16px; border-bottom: 1px solid #f5f5f5; cursor: pointer; }
.history-card:hover { background: #f5f7fa; }
.history-card-selected { border-left: 3px solid #409eff; background: #ecf5ff; }
.history-card-selected:hover { background: #dbeeff; }
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.history-date { font-size: 13px; color: #606266; }
.history-summary { font-size: 12px; color: #909399; }

.empty-state { text-align: center; padding: 40px; }
.empty-title { font-size: 16px; color: #606266; margin-bottom: 8px; }
.empty-desc { font-size: 13px; color: #909399; }

.text-muted { color: #c0c4cc; }
.mt-4 { margin-top: 16px; }

.go-badge { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }
.go-badge-go { background: #67c23a; color: #fff; }
.go-badge-nogo { background: #f56c6c; color: #fff; }
.go-badge-hold { background: #e9e9eb; color: #909399; }

.row-expanded { background: #f0f9eb; }
.reasoning-row { background: #f9fbf9; }
.reasoning-cell { padding: 10px 14px 10px 28px; font-size: 12px; color: #606266; line-height: 1.7; border-bottom: 1px solid #eee; }

.rx-card { border: 1px solid #eee; border-radius: 6px; padding: 12px; margin-bottom: 10px; }
.rx-row1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.rx-row2 { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; font-size: 12px; }
.pos-change { color: #606266; }
.capital-amount { color: #303133; font-weight: 600; }
.timing-badge { font-size: 11px; padding: 1px 6px; border-radius: 3px; }
.timing-immediate { background: #fef0f0; color: #f56c6c; }
.timing-batch { background: #fdf6ec; color: #e6a23c; }
.timing-conditional, .timing-wait { background: #f0f5ff; color: #409eff; }
.pe-badge { font-size: 11px; padding: 1px 6px; border-radius: 3px; font-weight: 600; }
.pe-high { background: #fef0f0; color: #f56c6c; }
.pe-low { background: #f0f9eb; color: #67c23a; }
.pe-mid { background: #f5f7fa; color: #909399; }

.debate-card {}
.debate-header { user-select: none; }
.collapse-arrow { font-size: 14px; transition: transform 0.2s; display: inline-block; }
.collapse-arrow.open { transform: rotate(90deg); }
.debate-tabs { display: flex; gap: 0; border-bottom: 1px solid #eee; padding: 0 20px; }
.debate-tab { background: none; border: none; border-bottom: 2px solid transparent; padding: 8px 16px; cursor: pointer; font-size: 13px; color: #606266; }
.debate-tab.active { color: #409eff; border-bottom-color: #409eff; font-weight: 600; }
.debate-content { padding: 12px 20px 16px; }
.debate-content pre { font-size: 13px; line-height: 1.7; white-space: pre-wrap; word-break: break-all; max-height: 400px; overflow-y: auto; margin: 0; color: #303133; background: #f8f9fa; border-radius: 4px; padding: 12px; }
</style>