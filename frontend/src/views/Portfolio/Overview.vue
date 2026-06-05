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
const reasoningOpen = ref(['reasoning'])

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
function sourceLabel(s: string): string {
  const m: Record<string, string> = { holding: '持仓', watchlist: '关注', vitality: '景气' }
  return m[s] || s
}
function actionTagType(a: string): string {
  const act = (a || '').toLowerCase()
  if (act === 'buy' || act === 'add' || act === 'new_position') return 'success'
  if (act === 'sell' || act === 'reduce') return 'danger'
  return 'info'
}
function actionLabel(a: string): string {
  const m: Record<string, string> = { buy: '买入', add: '加仓', reduce: '减仓', sell: '卖出', hold: '持有', new_position: '建仓' }
  return m[a?.toLowerCase()] || a || '--'
}
function buildStrategyLabel(s: string): string {
  const m: Record<string, string> = { immediate: '立即', batch: '分批', conditional: '条件' }
  return m[s] || s
}

function openIndustryDrawer(row: IndustryOverviewRow) {
  selectedIndustry.value = row
  showIndustryDrawer.value = true
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
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.history-date { font-size: 13px; color: #606266; }
.history-summary { font-size: 12px; color: #909399; }

.empty-state { text-align: center; padding: 40px; }
.empty-title { font-size: 16px; color: #606266; margin-bottom: 8px; }
.empty-desc { font-size: 13px; color: #909399; }

.text-muted { color: #c0c4cc; }
.mt-4 { margin-top: 16px; }
</style>