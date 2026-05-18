<template>
  <div class="portfolio-page">
    <div class="header">
      <div class="title">
        <el-icon style="margin-right:8px"><Wallet /></el-icon>
        <span>我的持仓</span>
      </div>
      <div class="actions">
        <el-button :icon="Refresh" text size="small" @click="refreshAll">刷新</el-button>
        <el-button type="warning" @click="requestAdvice" :loading="adviceGenerating" :disabled="!summary?.positions?.length">
          {{ adviceGenerating ? adviceStep : '组合建议' }}
        </el-button>
        <el-button type="primary" :icon="Plus" @click="openAddDialog">添加持仓</el-button>
        <el-button text size="small" @click="showAccountDialog = true">设置账户</el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">总资产</div>
          <div class="stat-value">{{ fmtMoney(summary?.total_assets) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">总投入</div>
          <div class="stat-value">{{ fmtMoney(summary?.total_invested) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">可用现金</div>
          <div class="stat-value">{{ fmtMoney(summary?.available_cash) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">总盈亏</div>
          <div class="stat-value" :style="{ color: pnlColor(summary?.total_pnl) }">
            {{ fmtMoney(summary?.total_pnl) }}
            <span v-if="summary?.total_pnl_pct" class="pnl-pct">
              ({{ summary.total_pnl_pct >= 0 ? '+' : '' }}{{ summary.total_pnl_pct.toFixed(2) }}%)
            </span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="body">
      <!-- 仓位分布饼图 -->
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header><div class="card-hd">仓位分布</div></template>
          <div ref="pieChartRef" class="pie-chart" />
          <el-empty v-if="!summary?.positions?.length" description="暂无持仓" />
        </el-card>
      </el-col>

      <!-- 持仓列表 -->
      <el-col :span="16">
        <el-card shadow="hover" class="positions-card">
          <template #header>
            <div class="card-hd">
              持仓明细
              <span class="sub-count">({{ summary?.positions?.length || 0 }} 只)</span>
            </div>
          </template>
          <el-table :data="summary?.positions || []" size="small" v-loading="loading">
            <el-table-column label="代码" width="100">
              <template #default="{ row }">
                <el-link type="primary" @click="viewStockDetail(row.code)">{{ row.code }}</el-link>
              </template>
            </el-table-column>
            <el-table-column label="市场" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.market === 'CN'" type="success" size="small">A股</el-tag>
                <el-tag v-else-if="row.market === 'HK'" type="warning" size="small">港股</el-tag>
                <el-tag v-else-if="row.market === 'US'" type="info" size="small">美股</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="数量" prop="quantity" width="80" />
            <el-table-column label="均价" width="100">
              <template #default="{ row }">{{ fmtPrice(row.avg_cost) }}</template>
            </el-table-column>
            <el-table-column label="最新价" width="100">
              <template #default="{ row }">{{ fmtPrice(row.last_price) }}</template>
            </el-table-column>
            <el-table-column label="市值(CNY)" width="120">
              <template #default="{ row }">{{ fmtMoney(row.market_value_cny) }}</template>
            </el-table-column>
            <el-table-column label="仓位" width="100">
              <template #default="{ row }">
                <div class="weight-cell">
                  <el-progress :percentage="row.weight || 0" :show-text="false" :stroke-width="6" />
                  <span class="weight-text">{{ (row.weight || 0).toFixed(1) }}%</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="盈亏" width="130">
              <template #default="{ row }">
                <span v-if="row.pnl_cny != null" :style="{ color: pnlColor(row.pnl_cny) }">
                  {{ fmtMoney(row.pnl_cny) }}
                  <span v-if="row.pnl_pct != null" class="pnl-pct">
                    ({{ row.pnl_pct >= 0 ? '+' : '' }}{{ row.pnl_pct.toFixed(2) }}%)
                  </span>
                </span>
                <span v-else style="color:#909399">--</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" type="success" link @click="goAnalysis(row.code)">分析</el-button>
                <el-button size="small" type="primary" link @click="editPosition(row)">编辑</el-button>
                <el-button size="small" type="danger" link @click="removePosition(row.code)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加持仓弹窗 -->
    <el-dialog v-model="addDialog" title="添加持仓" width="480px">
      <el-form label-width="90px">
        <el-form-item label="股票代码">
          <el-input v-model="addForm.code" placeholder="A股: 600519 | 港股: 0700 | 美股: AAPL" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="addForm.quantity" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="买入均价">
          <el-input-number v-model="addForm.avg_cost" :min="0.01" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="买入日期">
          <el-date-picker v-model="addForm.buy_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addForm.notes" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAdd">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 编辑持仓弹窗 -->
    <el-dialog v-model="editDialog" title="编辑持仓" width="480px">
      <el-form label-width="90px">
        <el-form-item label="股票代码">
          <el-input :model-value="editForm.code" disabled />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="editForm.quantity" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="均价">
          <el-input-number v-model="editForm.avg_cost" :min="0.01" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 组合建议抽屉 -->
    <el-drawer v-model="adviceDrawer" title="组合建议" size="55%" direction="rtl">
      <template v-if="currentAdvice">
        <div v-if="currentAdvice.status === 'COMPLETED'">
          <!-- 处方表格 -->
          <h4 style="margin:0 0 12px">操作建议</h4>
          <el-table :data="currentAdvice.prescription || []" size="small" border>
            <el-table-column label="代码" prop="code" width="100" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-tag :type="actionTagType(row.action)" size="small">{{ actionLabel(row.action) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="当前仓位" width="90">
              <template #default="{ row }">{{ row.current_weight?.toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="目标仓位" width="90">
              <template #default="{ row }">{{ row.target_weight?.toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="理由" prop="reasoning" min-width="160" show-overflow-tooltip />
            <el-table-column label="风险" prop="risk_note" min-width="140" show-overflow-tooltip />
          </el-table>

          <!-- CIO 总体判断 -->
          <h4 style="margin:20px 0 8px">CIO 裁决</h4>
          <div class="advice-text" v-html="renderMd(currentAdvice.cio_verdict)" />

          <!-- 辩论记录 -->
          <el-collapse style="margin-top:16px">
            <el-collapse-item title="持仓分析师评估" name="analyst">
              <div class="advice-text" v-html="renderMd(currentAdvice.analyst_assessment)" />
            </el-collapse-item>
            <el-collapse-item title="策略师评估" name="strategist">
              <div class="advice-text" v-html="renderMd(currentAdvice.strategist_assessment)" />
            </el-collapse-item>
            <el-collapse-item title="侦察兵评估" name="scout">
              <div class="advice-text" v-html="renderMd(currentAdvice.scout_assessment)" />
            </el-collapse-item>
            <el-collapse-item title="辩论记录" name="debate">
              <div class="advice-text" v-html="renderMd(currentAdvice.debate_history)" />
            </el-collapse-item>
          </el-collapse>

          <div class="advice-meta">
            生成于 {{ currentAdvice.completed_at?.slice(0, 19).replace('T', ' ') }}
            · 耗时 {{ currentAdvice.elapsed_seconds }}s
          </div>
        </div>

        <div v-else-if="currentAdvice.status === 'FAILED'" class="advice-error">
          <el-result icon="error" title="生成失败" :sub-title="currentAdvice.error || '未知错误'" />
        </div>

        <div v-else class="advice-loading">
          <el-result icon="info" title="正在生成" :sub-title="currentAdvice.current_step || '请稍候...'" />
        </div>
      </template>

      <el-empty v-else description="暂无组合建议" />

      <!-- 历史记录 -->
      <template v-if="adviceHistory.length > 1">
        <el-divider />
        <h4>历史建议</h4>
        <el-select v-model="selectedAdviceId" placeholder="选择历史记录" style="width:100%" @change="loadAdvice">
          <el-option
            v-for="h in adviceHistory"
            :key="h.advice_id"
            :label="(h.created_at?.slice(0, 19).replace('T', ' ') || '') + ' — ' + h.status"
            :value="h.advice_id"
          />
        </el-select>
      </template>
    </el-drawer>

    <!-- 设置账户弹窗 -->
    <el-dialog v-model="showAccountDialog" title="设置账户" width="400px">
      <el-form label-width="90px">
        <el-form-item label="总投入">
          <el-input-number v-model="accountForm.total_invested" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="可用现金">
          <el-input-number v-model="accountForm.available_cash" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAccountDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAccount">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Wallet, Refresh, Plus } from '@element-plus/icons-vue'
import { portfolioApi, type PortfolioSummary, type PortfolioAdvice } from '@/api/paper'
import * as echarts from 'echarts'

const router = useRouter()

const summary = ref<PortfolioSummary | null>(null)
const loading = ref(false)

const addDialog = ref(false)
const addForm = ref({ code: '', quantity: 100, avg_cost: 0, buy_date: '', notes: '' })

const editDialog = ref(false)
const editForm = ref({ code: '', quantity: 0, avg_cost: 0, notes: '' })

const showAccountDialog = ref(false)
const accountForm = ref({ total_invested: 0, available_cash: 0 })

const pieChartRef = ref<HTMLElement>()
let pieChart: echarts.ECharts | null = null

const adviceDrawer = ref(false)
const adviceGenerating = ref(false)
const adviceStep = ref('')
const currentAdvice = ref<PortfolioAdvice | null>(null)
const adviceHistory = ref<PortfolioAdvice[]>([])
const selectedAdviceId = ref('')
let advicePollTimer: ReturnType<typeof setInterval> | null = null

function fmtMoney(n: number | null | undefined) {
  if (n == null) return '--'
  return `¥${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtPrice(n: number | null | undefined) {
  if (n == null) return '--'
  return Number(n).toFixed(2)
}

function pnlColor(n: number | null | undefined) {
  if (n == null || n === 0) return '#909399'
  return n > 0 ? '#67C23A' : '#F56C6C'
}

async function fetchSummary() {
  try {
    loading.value = true
    const res = await portfolioApi.getSummary()
    if (res.success) {
      summary.value = res.data
      accountForm.value = {
        total_invested: res.data.total_invested || 0,
        available_cash: res.data.available_cash || 0,
      }
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '获取组合数据失败')
  } finally {
    loading.value = false
  }
}

function renderPieChart() {
  if (!pieChartRef.value || !summary.value?.positions?.length) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }
  const data = summary.value.positions.map(p => ({
    name: p.code,
    value: p.market_value_cny,
  }))
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      label: { show: true, formatter: '{b}\n{d}%' },
      data,
    }],
  })
}

function openAddDialog() {
  addForm.value = { code: '', quantity: 100, avg_cost: 0, buy_date: '', notes: '' }
  addDialog.value = true
}

async function submitAdd() {
  if (!addForm.value.code || !addForm.value.avg_cost) {
    ElMessage.warning('请填写股票代码和买入均价')
    return
  }
  try {
    const res = await portfolioApi.addPosition({
      code: addForm.value.code,
      quantity: addForm.value.quantity,
      avg_cost: addForm.value.avg_cost,
      buy_date: addForm.value.buy_date || undefined,
      notes: addForm.value.notes || undefined,
    })
    if (res.success) {
      ElMessage.success('持仓已添加')
      addDialog.value = false
      await refreshAll()
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '添加失败')
  }
}

function editPosition(row: any) {
  editForm.value = {
    code: row.code,
    quantity: row.quantity,
    avg_cost: row.avg_cost,
    notes: row.notes || '',
  }
  editDialog.value = true
}

async function submitEdit() {
  try {
    const res = await portfolioApi.updatePosition(editForm.value.code, {
      quantity: editForm.value.quantity,
      avg_cost: editForm.value.avg_cost,
      notes: editForm.value.notes || undefined,
    })
    if (res.success) {
      ElMessage.success('持仓已更新')
      editDialog.value = false
      await refreshAll()
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '更新失败')
  }
}

async function removePosition(code: string) {
  try {
    await ElMessageBox.confirm(`确认删除持仓 ${code}？`, '删除确认', { type: 'warning' })
    const res = await portfolioApi.deletePosition(code)
    if (res.success) {
      ElMessage.success('持仓已删除')
      await refreshAll()
    }
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.message || '删除失败')
  }
}

async function submitAccount() {
  try {
    const res = await portfolioApi.updateAccount({
      total_invested: accountForm.value.total_invested,
      available_cash: accountForm.value.available_cash,
    })
    if (res.success) {
      ElMessage.success('账户已更新')
      showAccountDialog.value = false
      await refreshAll()
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '更新失败')
  }
}

function viewStockDetail(code: string) {
  router.push({ name: 'StockDetail', params: { code } })
}

function goAnalysis(code: string) {
  router.push({ name: 'SingleAnalysis', query: { stock: code } })
}

async function requestAdvice() {
  try {
    adviceGenerating.value = true
    adviceStep.value = '提交中...'
    const res = await portfolioApi.generateAdvice()
    if (res.success && res.data?.advice_id) {
      adviceStep.value = '准备数据'
      selectedAdviceId.value = res.data.advice_id
      pollAdviceStatus(res.data.advice_id)
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '触发组合建议失败')
    adviceGenerating.value = false
  }
}

function pollAdviceStatus(adviceId: string) {
  if (advicePollTimer) clearInterval(advicePollTimer)
  advicePollTimer = setInterval(async () => {
    try {
      const res = await portfolioApi.getAdvice(adviceId)
      if (!res.success) return
      const adv = res.data
      if (adv.status === 'COMPLETED' || adv.status === 'FAILED') {
        if (advicePollTimer) { clearInterval(advicePollTimer); advicePollTimer = null }
        adviceGenerating.value = false
        currentAdvice.value = adv
        adviceDrawer.value = true
        await fetchAdviceHistory()
        if (adv.status === 'COMPLETED') {
          ElMessage.success('组合建议已生成')
        } else {
          ElMessage.error('组合建议生成失败')
        }
      } else {
        adviceStep.value = adv.current_step || '分析中...'
      }
    } catch {
      // ignore transient errors
    }
  }, 3000)
}

async function loadAdvice(adviceId: string) {
  try {
    const res = await portfolioApi.getAdvice(adviceId)
    if (res.success) {
      currentAdvice.value = res.data
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载建议失败')
  }
}

async function fetchAdviceHistory() {
  try {
    const res = await portfolioApi.getAdviceHistory(1, 20)
    if (res.success) {
      adviceHistory.value = res.data.items || []
    }
  } catch { /* ignore */ }
}

function actionTagType(action: string) {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
    buy: 'danger', add: 'danger', new_position: 'danger',
    sell: 'success', reduce: 'warning',
    hold: 'info',
  }
  return map[action] || ('info' as const)
}

function actionLabel(action: string): string {
  const map: Record<string, string> = {
    buy: '买入', sell: '卖出', hold: '持有',
    reduce: '减仓', add: '加仓', new_position: '建仓',
  }
  return map[action] || action
}

function renderMd(text: string | undefined): string {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

async function refreshAll() {
  await fetchSummary()
  await nextTick()
  renderPieChart()
}

watch(() => summary.value?.positions, () => {
  nextTick(() => renderPieChart())
})

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.portfolio-page { padding: 16px; }
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.title { display: flex; align-items: center; font-weight: 600; font-size: 16px; }
.stat-cards { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.stat-value { font-size: 20px; font-weight: 600; }
.pnl-pct { font-size: 12px; font-weight: normal; }
.card-hd { font-weight: 600; }
.sub-count { margin-left: 8px; font-size: 12px; color: #909399; font-weight: normal; }
.pie-chart { width: 100%; height: 300px; }
.weight-cell { display: flex; align-items: center; gap: 6px; }
.weight-text { font-size: 12px; color: #606266; white-space: nowrap; }
.advice-text { font-size: 13px; line-height: 1.7; color: #303133; word-break: break-word; }
.advice-meta { margin-top: 16px; font-size: 12px; color: #909399; text-align: right; }
.advice-error, .advice-loading { text-align: center; padding: 40px 0; }
</style>
