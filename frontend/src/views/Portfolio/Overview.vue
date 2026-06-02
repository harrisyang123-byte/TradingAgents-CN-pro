<template>
  <div class="portfolio-overview">
    <div class="page-content">
      <!-- 页面标题 -->
      <div class="flex items-center justify-between mb-5">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5" style="color:var(--primary)" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
          </svg>
          <span class="text-base font-semibold">组合总揽</span>
          <span v-if="overview" class="text-xs" style="color:#909399">
            {{ overview.total_industries }} 个行业 ·
            已覆盖 {{ overview.covered_count }} · 陈旧 {{ overview.stale_count }} · 未覆盖 {{ overview.never_count }}
          </span>
        </div>
        <button class="btn btn-plain btn-sm" @click="loadOverview(true)">刷新</button>
      </div>

      <!-- 统计卡片 -->
      <div class="stat-grid" v-if="overview">
        <div class="stat-card">
          <div class="label">行业总数</div>
          <div class="value">{{ overview.total_industries }}</div>
          <div class="sub">持仓 + 已分析</div>
        </div>
        <div class="stat-card covered">
          <div class="label">已覆盖</div>
          <div class="value">{{ overview.covered_count }}</div>
          <div class="sub">30天内分析过</div>
        </div>
        <div class="stat-card stale">
          <div class="label">陈旧</div>
          <div class="value">{{ overview.stale_count }}</div>
          <div class="sub">超过30天</div>
        </div>
        <div class="stat-card never">
          <div class="label">未覆盖</div>
          <div class="value">{{ overview.never_count }}</div>
          <div class="sub">从未分析</div>
        </div>
      </div>

      <!-- 行业覆盖矩阵 -->
      <template v-if="overview?.matrix?.length">
        <div class="card">
          <div class="card-header">
            <span>行业覆盖矩阵</span>
            <el-tag v-if="overview.latest_advice_at" size="small" type="info">
              最近分析: {{ overview.latest_advice_at.slice(0, 10) }}
            </el-tag>
          </div>
          <div class="card-body" style="padding:0">
            <table class="industry-table">
              <thead>
                <tr>
                  <th style="width:180px;cursor:pointer" @click="toggleMatrixSort('industry')">行业{{ matrixSortArrow('industry') }}</th>
                  <th style="width:72px;cursor:pointer" @click="toggleMatrixSort('holdings_weight')">当前仓位{{ matrixSortArrow('holdings_weight') }}</th>
                  <th style="width:72px;cursor:pointer" @click="toggleMatrixSort('target_weight')">建议仓位{{ matrixSortArrow('target_weight') }}</th>
                  <th style="width:64px;cursor:pointer" @click="toggleMatrixSort('delta')">变化{{ matrixSortArrow('delta') }}</th>
                  <th style="width:72px;cursor:pointer" @click="toggleMatrixSort('go_nogo')">评级{{ matrixSortArrow('go_nogo') }}</th>
                  <th style="width:100px;cursor:pointer" @click="toggleMatrixSort('position_names')">持仓标的{{ matrixSortArrow('position_names') }}</th>
                  <th style="width:72px;cursor:pointer" @click="toggleMatrixSort('coverage_status')">覆盖{{ matrixSortArrow('coverage_status') }}</th>
                  <th>判断摘要</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in sortedMatrix"
                  :key="row.industry"
                  class="industry-row"
                  :class="{ 'row-go': row.go_nogo === 'Go', 'row-nogo': row.go_nogo === 'NoGo' }"
                  @click="openIndustryDetail(row)"
                >
                  <td>
                    <span class="ind-name">{{ row.industry }}</span>
                    <span v-if="row.lifecycle" class="ind-lifecycle">{{ row.lifecycle }}</span>
                  </td>
                  <td>
                    <span v-if="row.holdings_weight > 0" class="weight-badge">{{ row.holdings_weight.toFixed(1) }}%</span>
                    <span v-else class="text-muted">--</span>
                  </td>
                  <td>
                    <span v-if="row.target_weight > 0" class="weight-badge target">{{ row.target_weight.toFixed(1) }}%</span>
                    <span v-else-if="row.industry === '现金'" class="weight-badge target">{{ row.target_weight.toFixed(1) }}%</span>
                    <span v-else class="text-muted">--</span>
                  </td>
                  <td>
                    <span
                      v-if="Math.abs(row.delta) > 0.1"
                      class="delta-tag"
                      :class="row.delta > 0 ? 'delta-up' : 'delta-down'"
                    >
                      {{ row.delta > 0 ? '+' : '' }}{{ row.delta.toFixed(1) }}%
                    </span>
                    <span v-else class="text-muted">0</span>
                  </td>
                  <td>
                    <el-tag
                      v-if="row.go_nogo"
                      :type="row.go_nogo === 'Go' ? 'success' : row.go_nogo === 'NoGo' ? 'danger' : 'warning'"
                      size="small"
                    >{{ row.go_nogo }}</el-tag>
                    <span v-else class="text-muted">--</span>
                  </td>
                  <td>
                    <el-button
                      v-if="row.position_names.length"
                      link
                      size="small"
                      type="primary"
                      @click.stop="openPositionsDrawer(row)"
                    >
                      {{ row.position_names.length }} 只
                    </el-button>
                    <span v-else class="text-muted">0</span>
                  </td>
                  <td>
                    <el-tag :type="coverageTagType(row.coverage_status)" size="small">
                      {{ coverageLabel(row.coverage_status) }}
                    </el-tag>
                  </td>
                  <td>
                    <el-tag v-if="row.depth === 'deep'" type="primary" size="small" effect="plain">深度</el-tag>
                    <el-tag v-else-if="row.depth === 'opportunity'" type="success" size="small" effect="plain">机会</el-tag>
                    <span v-else class="text-muted">轻量</span>
                  </td>
                  <td class="reason-cell" @click.stop>
                    {{ row.reasoning?.slice(0, 80) }}{{ row.reasoning?.length > 80 ? '...' : '' }}
                    <span v-if="!row.reasoning" class="text-muted">--</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 持仓标的抽屉 -->
        <el-drawer
          v-model="showPositionsDrawer"
          :title="drawerIndustry?.industry + ' · 持仓标的'"
          size="420px"
          direction="rtl"
        >
          <template v-if="drawerIndustry">
            <div class="drawer-stat-row">
              <span>仓位占比</span>
              <strong>{{ drawerIndustry.holdings_weight?.toFixed(1) }}%</strong>
            </div>
            <div class="drawer-stat-row">
              <span>评级</span>
              <el-tag
                :type="drawerIndustry.go_nogo === 'Go' ? 'success' : drawerIndustry.go_nogo === 'NoGo' ? 'danger' : 'warning'"
                size="small"
              >{{ drawerIndustry.go_nogo || '--' }}</el-tag>
            </div>
            <div class="drawer-stat-row">
              <span>判断摘要</span>
              <span style="font-size:13px;color:#606266">{{ drawerIndustry.reasoning || '--' }}</span>
            </div>
            <el-divider />
            <div class="drawer-pos-list">
              <div
                v-for="(name, i) in drawerIndustry.position_names"
                :key="name"
                class="drawer-pos-item"
              >
                <div class="drawer-pos-name">{{ name }}</div>
                <div class="drawer-pos-code" v-if="drawerIndustry.position_codes[i]">{{ drawerIndustry.position_codes[i] }}</div>
              </div>
            </div>
          </template>
        </el-drawer>
      </template>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="card">
        <div class="card-body">
          <div class="empty-state">
            <div class="empty-title">暂无覆盖数据</div>
            <div class="empty-desc">
              <p>请先在 <router-link to="/portfolio/analysis">持仓分析</router-link> 中运行一次分析</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史建议列表 -->
      <div class="card mt-4" v-if="adviceHistory.length">
        <div class="card-header">
          <span>历史组合建议</span>
        </div>
        <div class="card-body">
          <div
            v-for="adv in adviceHistory"
            :key="adv.advice_id"
            class="history-card"
            @click="openAdviceDetail(adv)"
          >
            <div class="history-header">
              <span class="history-date">{{ adv.created_at?.slice(0, 19).replace('T', ' ') }}</span>
              <el-tag
                :type="adv.status === 'COMPLETED' ? 'success' : adv.status === 'FAILED' ? 'danger' : 'info'"
                size="small"
              >
                {{ adv.status }}
              </el-tag>
            </div>
            <div class="history-summary">
              覆盖 {{ adv.selected_industries?.length || adv.prescription?.length || 0 }} 个行业 ·
              {{ adv.prescription?.length || 0 }} 条处方
            </div>
            <div v-if="adv.cio_verdict" class="history-verdict">
              {{ adv.cio_verdict.slice(0, 150) }}{{ adv.cio_verdict.length > 150 ? '...' : '' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 历史建议详情弹窗 -->
      <el-dialog
        v-model="showDetailDialog"
        :title="'组合建议 · ' + (selectedAdvice?.created_at?.slice(0, 10) || '')"
        width="70%"
        top="5vh"
      >
        <template v-if="selectedAdvice">
          <div v-if="selectedAdvice.status === 'COMPLETED'">
            <!-- 决策总览 -->
            <div class="advice-summary-bar">
              <span>处方 {{ sortedHistoryPrescription.length }} 条</span>
              <span>耗时 {{ selectedAdvice.elapsed_seconds || 0 }}s</span>
              <span v-if="selectedAdvice.data_score !== undefined">数据完整度 {{ selectedAdvice.data_score }}%</span>
              <span v-if="buySignalCount" class="signal-summary">
                🟢{{ strongBuyCount }} 🟡{{ buyCount }} ⚪{{ holdCount }}
              </span>
            </div>

            <!-- 市场信号快照 -->
            <div v-if="selectedAdvice.market_signals" class="market-signals-bar">
              <span class="ms-item">北向 {{ selectedAdvice.market_signals.north_net > 0 ? '流入' : '流出' }} {{ Math.abs(selectedAdvice.market_signals.north_net || 0) }}亿</span>
              <span v-if="selectedAdvice.market_signals.breadth" class="ms-item">
                涨跌比 {{ selectedAdvice.market_signals.breadth.up_ratio }}% · {{ selectedAdvice.market_signals.breadth.breadth_signal }}
              </span>
              <span v-if="selectedAdvice.market_signals.macro?.pmi" class="ms-item">
                PMI {{ selectedAdvice.market_signals.macro.pmi }}
              </span>
            </div>

            <!-- 决策流 -->
            <div class="decision-flow">
              <div class="flow-step" v-if="selectedAdvice.macro_judge_verdict">
                <div class="flow-step-header" @click="flowOpen = (flowOpen === 'l1' ? '' : 'l1')">
                  <span class="flow-step-num">L1</span>
                  <span class="flow-step-title">行业方向</span>
                  <span class="flow-step-stat">{{ selectedAdvice.market_intel?.industries?.length || 0 }} 行业扫描</span>
                  <span class="flow-arrow">{{ flowOpen === 'l1' ? '▼' : '▶' }}</span>
                </div>
                <div v-if="flowOpen === 'l1'" class="flow-step-body">
                  <div class="advice-text" v-html="renderMd(selectedAdvice.macro_judge_verdict?.slice(0, 8000))"></div>
                  <div v-if="selectedAdvice.market_debate_history" class="debate-section">
                    <div class="debate-toggle" @click="debateOpen = (debateOpen === 'l1' ? '' : 'l1')">
                      L1 辩论记录 ({{ selectedAdvice.market_debate_history.length }} 字符)
                    </div>
                    <div v-if="debateOpen === 'l1'" class="advice-text" v-html="renderMd(selectedAdvice.market_debate_history?.slice(0, 5000))"></div>
                </div>
              </div>

              <div class="flow-connector"></div>

              <div class="flow-step" v-if="selectedAdvice.stock_judge_verdict || selectedAdvice.stock_candidates?.length">
                <div class="flow-step-header" @click="flowOpen = (flowOpen === 'l2' ? '' : 'l2')">
                  <span class="flow-step-num">L2</span>
                  <span class="flow-step-title">标的筛选</span>
                  <span class="flow-step-stat">{{ selectedAdvice.stock_candidates?.length || 0 }} 候选标的</span>
                  <span class="flow-arrow">{{ flowOpen === 'l2' ? '▼' : '▶' }}</span>
                </div>
                <div v-if="flowOpen === 'l2'" class="flow-step-body">
                  <div v-if="selectedAdvice.stock_candidates?.length" class="candidates-table-wrap">
                    <table class="candidates-table">
                      <thead><tr>
                        <th>代码</th><th>名称</th><th>推荐</th><th>评分</th><th>估值</th>
                      </tr></thead>
                      <tbody>
                        <tr v-for="c in (selectedAdvice.stock_candidates || []).slice(0, 15)" :key="c.code">
                          <td style="font-family:monospace">{{ c.code }}</td>
                          <td>{{ c.name }}</td>
                          <td>
                            <el-tag v-if="c.action" :type="c.action==='buy'?'success':c.action==='observe'?'warning':'info'" size="small">{{ c.action }}</el-tag>
                          </td>
                          <td>{{ c.total_score || '-' }}</td>
                          <td>{{ c.valuation || '-' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div class="advice-text" v-html="renderMd(selectedAdvice.stock_judge_verdict?.slice(0, 8000))"></div>
                  <div v-if="selectedAdvice.stock_debate_history" class="debate-section mt-2">
                    <div class="debate-toggle" @click="debateOpen = (debateOpen === 'l2' ? '' : 'l2')">
                      L2 辩论记录 ({{ selectedAdvice.stock_debate_history.length }} 字符)
                    </div>
                    <div v-if="debateOpen === 'l2'" class="advice-text" v-html="renderMd(selectedAdvice.stock_debate_history?.slice(0, 5000))"></div>
                  </div>
                </div>
              </div>

              <div class="flow-connector"></div>

              <div class="flow-step">
                <div class="flow-step-header" @click="flowOpen = (flowOpen === 'l3' ? '' : 'l3')">
                  <span class="flow-step-num">L3</span>
                  <span class="flow-step-title">组合构建</span>
                  <span class="flow-step-stat">4 人红队辩论</span>
                  <span class="flow-arrow">{{ flowOpen === 'l3' ? '▼' : '▶' }}</span>
                </div>
                <div v-if="flowOpen === 'l3'" class="flow-step-body">
                  <el-tabs>
                    <el-tab-pane label="组合反向者">
                      <div class="advice-text" v-html="renderMd((selectedAdvice.contrarian_assessment || selectedAdvice.debate_history?.split('[反向意见者]')[1] || '').slice(0, 8000))"></div>
                    </el-tab-pane>
                    <el-tab-pane label="持仓分析师">
                      <div class="advice-text" v-html="renderMd(selectedAdvice.analyst_assessment?.slice(0, 8000))"></div>
                    </el-tab-pane>
                    <el-tab-pane label="策略师">
                      <div class="advice-text" v-html="renderMd(selectedAdvice.strategist_assessment?.slice(0, 8000))"></div>
                    </el-tab-pane>
                    <el-tab-pane label="侦察兵">
                      <div class="advice-text" v-html="renderMd(selectedAdvice.scout_assessment?.slice(0, 8000))"></div>
                    </el-tab-pane>
                  </el-tabs>
                  <div v-if="selectedAdvice.debate_history" class="debate-section mt-2">
                    <div class="debate-toggle" @click="debateOpen = (debateOpen === 'l3' ? '' : 'l3')">
                      L3 完整辩论记录 ({{ selectedAdvice.debate_history.length }} 字符)
                    </div>
                    <div v-if="debateOpen === 'l3'" class="advice-text" v-html="renderMd(selectedAdvice.debate_history?.slice(0, 8000))"></div>
                  </div>
                </div>
              </div>

              <div class="flow-connector"></div>

              <div class="flow-step">
                <div class="flow-step-header" @click="flowOpen = (flowOpen === 'l4' ? '' : 'l4')">
                  <span class="flow-step-num">L4</span>
                  <span class="flow-step-title">最终处方</span>
                  <span class="flow-step-stat">{{ sortedHistoryPrescription.length }} 条处方</span>
                  <span class="flow-arrow">{{ flowOpen === 'l4' ? '▼' : '▶' }}</span>
                </div>
                <div v-if="flowOpen === 'l4'" class="flow-step-body">
                  <div class="decision-card-stream">
                    <DecisionCard
                      v-for="item in sortedHistoryPrescription"
                      :key="item.code"
                      :item="item"
                      :buy-signal="selectedAdvice?.buy_signals?.[item.code] || null"
                    />
                  </div>
                  <el-collapse style="margin-top:12px">
                    <el-collapse-item v-if="selectedAdvice.cio_verdict" title="CIO 裁决原文">
                      <div class="advice-text" v-html="renderMd(selectedAdvice.cio_verdict?.slice(0, 10000))"></div>
                    </el-collapse-item>
                    <el-collapse-item v-if="selectedAdvice.risk_director_review" title="风险总监审查">
                      <div class="advice-text" v-html="renderMd(selectedAdvice.risk_director_review)"></div>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </div>
            </div>
          </div>
          <el-result v-else-if="selectedAdvice.status === 'FAILED'" icon="error" :sub-title="selectedAdvice.error || '未知错误'" />
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { portfolioApi, type PortfolioAdvice, type AdviceItem, type IndustryOverviewRow } from '@/api/paper'
import DecisionCard from '@/components/Analysis/DecisionCard.vue'
import { usePageCache } from '@/composables/usePageCache'

const { loadWithCache, forceRefresh } = usePageCache()

const loading = ref(false)
const overview = ref<{
  matrix: IndustryOverviewRow[]
  total_industries: number
  covered_count: number
  stale_count: number
  never_count: number
  planned_count: number
  latest_advice_at: string
} | null>(null)

const adviceHistory = ref<PortfolioAdvice[]>([])
const selectedAdvice = ref<PortfolioAdvice | null>(null)
const showDetailDialog = ref(false)
const flowOpen = ref('')
const debateOpen = ref('')

// 矩阵排序
const matrixSortField = ref<string>('holdings_weight')
const matrixSortOrder = ref<'asc' | 'desc'>('desc')

const sortedMatrix = computed(() => {
  if (!overview.value?.matrix) return []
  const rows = [...overview.value.matrix]
  const field = matrixSortField.value
  const order = matrixSortOrder.value === 'desc' ? -1 : 1
  rows.sort((a: any, b: any) => {
    let va: any, vb: any
    if (field === 'position_names') {
      va = a.position_names?.length || 0
      vb = b.position_names?.length || 0
    } else if (field === 'go_nogo') {
      // Go > NoGo > 空
      const rank: Record<string, number> = { 'Go': 2, 'NoGo': 1 }
      va = rank[a.go_nogo || ''] || 0
      vb = rank[b.go_nogo || ''] || 0
    } else if (field === 'coverage_status') {
      const rank: Record<string, number> = { 'covered': 3, 'stale': 2, 'planned': 1, 'never': 0 }
      va = rank[a.coverage_status || ''] ?? 0
      vb = rank[b.coverage_status || ''] ?? 0
    } else if (field === 'depth') {
      const rank: Record<string, number> = { 'deep': 3, 'opportunity': 2, 'light': 1 }
      va = rank[a.depth || ''] ?? 0
      vb = rank[b.depth || ''] ?? 0
    } else {
      va = a[field] ?? ''
      vb = b[field] ?? ''
    }
    if (typeof va === 'string') return va.localeCompare(vb) * order
    return (va - vb) * order
  })
  return rows
})

function toggleMatrixSort(field: string) {
  if (matrixSortField.value === field) {
    matrixSortOrder.value = matrixSortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    matrixSortField.value = field
    matrixSortOrder.value = 'desc'
  }
}

function matrixSortArrow(field: string) {
  if (matrixSortField.value !== field) return ''
  return matrixSortOrder.value === 'desc' ? ' ↓' : ' ↑'
}

// 持仓抽屉
const showPositionsDrawer = ref(false)
const drawerIndustry = ref<IndustryOverviewRow | null>(null)

function openPositionsDrawer(row: IndustryOverviewRow) {
  drawerIndustry.value = row
  showPositionsDrawer.value = true
}

function openIndustryDetail(row: IndustryOverviewRow) {
  // 预留：后续可扩展为行业详情弹窗
  openPositionsDrawer(row)
}

const sortedHistoryPrescription = computed(() => {
  const items = (selectedAdvice.value?.prescription || []) as AdviceItem[]
  const order: Record<string, number> = { urgent: 0, important: 1, optional: 2 }
  return [...items].sort((a, b) => (order[a.priority || 'optional'] ?? 2) - (order[b.priority || 'optional'] ?? 2))
})

const buySignals = computed(() => selectedAdvice.value?.buy_signals || {})
const buySignalCount = computed(() => Object.keys(buySignals.value).length)
const strongBuyCount = computed(() => Object.values(buySignals.value).filter((s: any) => s.signal === 'STRONG_BUY').length)
const buyCount = computed(() => Object.values(buySignals.value).filter((s: any) => s.signal === 'BUY').length)
const holdCount = computed(() => Object.values(buySignals.value).filter((s: any) => s.signal === 'HOLD').length)

function coverageTagType(s: string) {
  return s === 'covered' ? 'success' : s === 'stale' ? 'warning' : s === 'planned' ? 'info' : 'danger'
}

function coverageLabel(s: string) {
  return s === 'covered' ? '已覆盖' : s === 'stale' ? '陈旧' : s === 'planned' ? '计划中' : '未覆盖'
}

async function loadOverview(force = false) {
  loading.value = true
  try {
    const fn = force ? forceRefresh : loadWithCache
    overview.value = await fn('overview', async () => {
      const res = await portfolioApi.getPortfolioOverview()
      if (res.success) return res.data
      throw new Error('API failed')
    })
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

function openAdviceDetail(adv: PortfolioAdvice) {
  selectedAdvice.value = adv
  showDetailDialog.value = true
}

function renderMd(text: string | undefined): string {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

onMounted(() => {
  loadOverview()
  loadHistory()
})
</script>

<style scoped>
.portfolio-overview {
  --primary: #409eff;
  --primary-light: #ecf5ff;
  --text-primary: #303133;
  --text-regular: #606266;
  --text-secondary: #909399;
  --border-light: #e4e7ed;
  --border-lighter: #ebeef5;
  --fill-light: #f5f7fa;
  --bg-page: #f2f3f5;
  background: var(--bg-page);
  min-height: 100vh;
}

.page-content { max-width: 1400px; margin: 0 auto; padding: 24px; }

.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.mb-5 { margin-bottom: 20px; }
.mt-4 { margin-top: 16px; }
.w-5 { width: 20px; }
.h-5 { height: 20px; }
.text-base { font-size: 14px; }
.text-xs { font-size: 12px; }
.font-semibold { font-weight: 600; }

.card { background: #fff; border-radius: 8px; border: 1px solid #ebeef5; }
.card-header { padding: 14px 20px; border-bottom: 1px solid #ebeef5; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: space-between; }
.card-body { padding: 20px; }

.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 4px; font-size: 14px; cursor: pointer; border: 1px solid; transition: all 0.2s; font-weight: 400; line-height: 1; white-space: nowrap; }
.btn-plain { background: #fff; border-color: #dcdfe6; color: #606266; }
.btn-plain:hover { color: #409eff; border-color: #c6e2ff; background: #ecf5ff; }
.btn-sm { padding: 5px 12px; font-size: 12px; }

.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.stat-card { background: #fff; border-radius: 8px; border: 1px solid #ebeef5; padding: 20px; }
.stat-card .label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.stat-card .value { font-size: 28px; font-weight: 700; color: #303133; }
.stat-card .sub { font-size: 12px; color: #909399; margin-top: 4px; }
.stat-card.covered .value { color: #67c23a; }
.stat-card.stale .value { color: #e6a23c; }
.stat-card.never .value { color: #f56c6c; }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #fafafa; color: #909399; font-weight: 600; text-align: left; padding: 10px 12px; border-bottom: 1px solid #ebeef5; font-size: 12px; white-space: nowrap; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #ebeef5; color: #303133; }
.data-table tbody tr:hover { background: #f5f7fa; }

.ind-name { font-weight: 600; }
.weight-badge { background: #ecf5ff; color: #409eff; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.reason-cell { font-size: 12px; color: #606266; max-width: 220px; line-height: 1.5; }
.pos-name-tag { display: inline-block; background: #f0f2f5; color: #303133; padding: 1px 6px; border-radius: 3px; font-size: 12px; margin: 1px 2px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.position-codes-sub { font-size: 10px; color: #c0c4cc; margin-top: 2px; font-family: monospace; }

.history-card { padding: 12px 16px; border: 1px solid #ebeef5; border-radius: 6px; margin-bottom: 8px; cursor: pointer; transition: border-color 0.2s; }
.history-card:hover { border-color: #b3d8ff; background: #fafafa; }
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.history-date { font-weight: 600; font-size: 13px; color: #303133; }
.history-summary { font-size: 12px; color: #909399; margin-bottom: 4px; }
.history-verdict { font-size: 12px; color: #606266; line-height: 1.5; }

.decision-card-stream { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 12px; }
.advice-text { font-size: 13px; line-height: 1.7; color: #303133; word-break: break-word; }

.empty-state { text-align: center; padding: 40px 20px; }
.empty-title { font-size: 16px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.empty-desc { font-size: 14px; color: #909399; line-height: 1.6; }

/* 行业覆盖表格 */
.industry-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.industry-table th { background: #fafafa; color: #909399; font-weight: 600; text-align: left; padding: 10px 14px; border-bottom: 1px solid #ebeef5; font-size: 12px; white-space: nowrap; }
.industry-table td { padding: 10px 14px; border-bottom: 1px solid #ebeef5; color: #303133; vertical-align: middle; }
.industry-table tbody tr:hover { background: #f5f7fa; cursor: pointer; }
.industry-table .row-go { border-left: 3px solid #67c23a; }
.industry-table .row-nogo { border-left: 3px solid #f56c6c; }

.ind-name { font-weight: 600; }
.ind-lifecycle { display: block; font-size: 11px; color: #909399; margin-top: 2px; }
.text-muted { color: #c0c4cc; font-size: 12px; }
.weight-badge { background: #ecf5ff; color: #409eff; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.reason-cell { font-size: 12px; color: #606266; max-width: 280px; line-height: 1.5; }

/* 抽屉 */
.drawer-stat-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; font-size: 13px; color: #606266; }
.drawer-pos-list { display: flex; flex-direction: column; gap: 4px; }
.drawer-pos-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f5f7fa; border-radius: 6px; }
.drawer-pos-name { font-size: 13px; font-weight: 500; color: #303133; }
.drawer-pos-code { font-size: 12px; color: #909399; font-family: monospace; }

/* 决策流 */
.advice-summary-bar { display: flex; gap: 24px; padding: 8px 16px; background: #f0f5ff; border-radius: 6px; font-size: 13px; color: #606266; margin-bottom: 16px; }
.signal-summary { font-size: 14px; margin-left: auto; }

.market-signals-bar {
  display: flex; gap: 16px; padding: 6px 14px;
  background: #fef7e0; border-radius: 4px; margin-bottom: 12px;
  font-size: 12px; color: #8c6d1f;
}
.ms-item { white-space: nowrap; }
.decision-flow { }
.flow-step { border: 1px solid #ebeef5; border-radius: 8px; margin-bottom: 0; }
.flow-step-header { display: flex; align-items: center; gap: 12px; padding: 12px 16px; cursor: pointer; transition: background 0.15s; }
.flow-step-header:hover { background: #f5f7fa; }
.flow-step-num { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 6px; background: #409eff; color: #fff; font-weight: 700; font-size: 13px; flex-shrink: 0; }
.flow-step-title { font-weight: 600; font-size: 14px; color: #303133; }
.flow-step-stat { font-size: 12px; color: #909399; }
.flow-arrow { margin-left: auto; font-size: 12px; color: #909399; }
.flow-step-body { padding: 12px 16px 16px; border-top: 1px solid #ebeef5; }
.flow-connector { width: 2px; height: 16px; background: #dcdfe6; margin: 0 auto; border-radius: 1px; }
.candidates-table-wrap { margin-bottom: 12px; overflow-x: auto; }
.candidates-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.candidates-table th { background: #fafafa; text-align: left; padding: 6px 10px; border-bottom: 1px solid #ebeef5; color: #909399; }
.candidates-table td { padding: 6px 10px; border-bottom: 1px solid #ebeef5; }

.weight-badge.target { background: #fdf6ec; color: #e6a23c; }
.delta-tag { font-size: 12px; font-weight: 600; white-space: nowrap; }
.delta-up { color: #e6a23c; }
.delta-down { color: #67c23a; }
.mt-2 { margin-top: 8px; }
.text-xs { font-size: 12px; }

.debate-section { margin-top: 8px; }
.debate-toggle {
  cursor: pointer; font-size: 12px; color: #409eff;
  padding: 6px 10px; background: #ecf5ff; border-radius: 4px;
  display: inline-block;
}
.debate-toggle:hover { background: #d9ecff; }
</style>
