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
        <button class="btn btn-plain btn-sm" @click="loadOverview">刷新</button>
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
      <div class="card" v-if="overview?.matrix?.length">
        <div class="card-header">
          <span>行业覆盖矩阵</span>
          <el-tag v-if="overview.latest_advice_at" size="small" type="info">
            最近分析: {{ overview.latest_advice_at.slice(0, 10) }}
          </el-tag>
        </div>
        <div class="card-body" style="padding:0;overflow-x:auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>行业</th>
                <th>持仓权重</th>
                <th>持仓标的</th>
                <th>生命周期</th>
                <th>Go/NoGo</th>
                <th>覆盖状态</th>
                <th>关键判断</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in overview.matrix" :key="row.industry">
                <td>
                  <span class="ind-name">{{ row.industry }}</span>
                </td>
                <td>
                  <span v-if="row.holdings_weight > 0" class="weight-badge">
                    {{ row.holdings_weight.toFixed(1) }}%
                  </span>
                  <span v-else style="color:#909399">--</span>
                </td>
                <td>
                  <div class="position-names">
                    <span v-for="(name, i) in row.position_names.slice(0, 3)" :key="name" class="pos-name-tag">{{ name }}</span>
                    <span v-if="row.position_names.length > 3" style="color:#909399;font-size:11px"> +{{ row.position_names.length - 3 }}</span>
                  </div>
                  <div class="position-codes-sub" v-if="row.position_codes.length">
                    {{ row.position_codes.slice(0, 4).join(' ') }}{{ row.position_codes.length > 4 ? ' ...' : '' }}
                  </div>
                </td>
                <td>{{ row.lifecycle || '--' }}</td>
                <td>
                  <el-tag
                    v-if="row.go_nogo"
                    :type="row.go_nogo === 'Go' ? 'success' : row.go_nogo === 'NoGo' ? 'danger' : 'warning'"
                    size="small"
                  >
                    {{ row.go_nogo }}
                  </el-tag>
                  <span v-else style="color:#909399">--</span>
                </td>
                <td>
                  <el-tag
                    :type="coverageTagType(row.coverage_status)"
                    size="small"
                  >
                    {{ coverageLabel(row.coverage_status) }}
                  </el-tag>
                </td>
                <td>
                  <div class="reason-cell" v-if="row.reasoning">{{ row.reasoning.slice(0, 80) }}{{ row.reasoning.length > 80 ? '...' : '' }}</div>
                  <span v-else style="color:#909399">--</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

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
            <h4 style="margin:0 0 12px">操作处方</h4>
            <div class="decision-card-stream">
              <DecisionCard
                v-for="item in sortedHistoryPrescription"
                :key="item.code"
                :item="item"
              />
            </div>
            <h4 style="margin:20px 0 8px">CIO 裁决</h4>
            <div class="advice-text" v-html="renderMd(selectedAdvice.cio_verdict)" />
            <el-collapse style="margin-top:16px">
              <el-collapse-item v-if="selectedAdvice.macro_judge_verdict" title="L1 · 行业方向" name="l1">
                <div class="advice-text" v-html="renderMd(selectedAdvice.macro_judge_verdict)" />
              </el-collapse-item>
              <el-collapse-item v-if="selectedAdvice.stock_judge_verdict" title="L2 · 候选标的" name="l2">
                <div class="advice-text" v-html="renderMd(selectedAdvice.stock_judge_verdict)" />
              </el-collapse-item>
              <el-collapse-item title="L3 · 分析师" name="analyst">
                <div class="advice-text" v-html="renderMd(selectedAdvice.analyst_assessment)" />
              </el-collapse-item>
              <el-collapse-item title="L3 · 策略师" name="strategist">
                <div class="advice-text" v-html="renderMd(selectedAdvice.strategist_assessment)" />
              </el-collapse-item>
              <el-collapse-item title="L3 · 侦察兵" name="scout">
                <div class="advice-text" v-html="renderMd(selectedAdvice.scout_assessment)" />
              </el-collapse-item>
              <el-collapse-item v-if="selectedAdvice.risk_director_review" title="L4 · 风险审查" name="risk">
                <div class="advice-text" v-html="renderMd(selectedAdvice.risk_director_review)" />
              </el-collapse-item>
            </el-collapse>
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

const sortedHistoryPrescription = computed(() => {
  const items = (selectedAdvice.value?.prescription || []) as AdviceItem[]
  const order: Record<string, number> = { urgent: 0, important: 1, optional: 2 }
  return [...items].sort((a, b) => (order[a.priority || 'optional'] ?? 2) - (order[b.priority || 'optional'] ?? 2))
})

function coverageTagType(s: string) {
  return s === 'covered' ? 'success' : s === 'stale' ? 'warning' : s === 'planned' ? 'info' : 'danger'
}

function coverageLabel(s: string) {
  return s === 'covered' ? '已覆盖' : s === 'stale' ? '陈旧' : s === 'planned' ? '计划中' : '未覆盖'
}

async function loadOverview() {
  loading.value = true
  try {
    const res = await portfolioApi.getPortfolioOverview()
    if (res.success) {
      overview.value = res.data
    }
  } catch { /* ignore */ }
  loading.value = false
}

async function loadHistory() {
  try {
    const res = await portfolioApi.getAdviceHistory(1, 20)
    if (res.success) {
      adviceHistory.value = (res.data.items || []).filter((a: PortfolioAdvice) => a.status === 'COMPLETED')
    }
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
</style>
