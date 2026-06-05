<template>
  <div class="portfolio-analysis">
    <div class="page-content">
      <!-- 页面标题 -->
      <div class="flex items-center justify-between mb-5">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5" style="color:var(--primary)" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
          </svg>
          <span class="text-base font-semibold">持仓分析</span>
        </div>
        <div class="flex items-center gap-3">
          <button
            class="btn btn-primary btn-sm"
            :disabled="phase !== 'idle'"
            @click="startL1Plan"
          >
            开始分析
          </button>
        </div>
      </div>

      <!-- ====== Phase 1: L1 行业方向 ====== -->
      <div v-if="phase === 'planning' || phase === 'plan_ready'" class="card mb-4">
        <div class="card-header">
          <span>Phase 1：行业方向扫描（L1 Market Strategist + Contrarian + Macro Judge）</span>
          <el-tag v-if="phase === 'planning'" type="warning" size="small">运行中...</el-tag>
          <el-tag v-else type="success" size="small">完成</el-tag>
        </div>
        <div class="card-body">
          <!-- 流式日志 -->
          <div v-if="l1Logs.length" class="stream-log mb-4">
            <div v-for="(log, i) in l1Logs" :key="i" class="stream-log-item">
              <span class="log-node">{{ log.node }}</span>
              <span v-if="log.text" class="log-text">{{ log.text.slice(0, 200) }}...</span>
            </div>
          </div>

          <!-- 行业计划（plan_ready 时展示） -->
          <div v-if="phase === 'plan_ready' && l1Industries.length" class="industry-selection">
            <h4 style="margin:0 0 12px">
              持仓行业全覆盖
              <span style="font-weight:400;font-size:12px;color:#909399">
                （全部持仓行业已评估，勾选要深度分析的行业，然后执行 L2-L4）
              </span>
            </h4>
            <el-checkbox-group v-model="selectedIndustries">
              <div class="industry-grid">
                <div
                  v-for="ind in l1Industries"
                  :key="ind.industry"
                  class="industry-card"
                  :class="{
                    selected: selectedIndustries.includes(ind.industry),
                    'is-opportunity': ind.depth === 'opportunity',
                  }"
                >
                  <el-checkbox :value="ind.industry" style="margin-right:0">
                    <div class="ind-info">
                      <div class="ind-name">
                        {{ ind.industry }}
                        <el-tag v-if="ind.depth === 'deep'" type="primary" size="small">深度辩论</el-tag>
                        <el-tag v-else-if="ind.depth === 'opportunity'" type="success" size="small">机会推荐</el-tag>
                        <el-tag v-else type="info" size="small">轻量评估</el-tag>
                        <el-tag :type="ind.recommendation === 'Go' ? 'success' : ind.recommendation === 'NoGo' ? 'danger' : 'warning'" size="small">
                          {{ ind.recommendation || ind.go_nogo || '--' }}
                        </el-tag>
                      </div>
                      <div class="ind-meta">
                        <span v-if="ind.lifecycle">{{ ind.lifecycle }}</span>
                        <span v-if="ind.confidence">置信度: {{ ind.confidence }}</span>
                        <span>{{ ind.market === 'hk' ? '港股' : ind.market === 'us' ? '美股' : 'A股' }}</span>
                      </div>
                      <div v-if="ind.reasoning" class="ind-reason">{{ ind.reasoning.slice(0, 120) }}{{ ind.reasoning.length > 120 ? '...' : '' }}</div>
                    </div>
                  </el-checkbox>
                </div>
              </div>
            </el-checkbox-group>

            <div style="margin-top:16px;display:flex;gap:12px">
              <button class="btn btn-primary" :disabled="!selectedIndustries.length" @click="startL2L4">
                {{ selectedIndustries.length ? `执行分析（已选 ${selectedIndustries.length} 个行业）` : '请选择行业' }}
              </button>
              <button class="btn btn-plain" @click="resetToIdle">取消</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== Phase 2: L2-L4 执行 ====== -->
      <div v-if="phase === 'executing'" class="card mb-4">
        <div class="card-header">
          <span>Phase 2：深度分析执行中（L2 Scout → L3 Debate → L4 CIO）</span>
          <el-tag type="warning" size="small">运行中...</el-tag>
        </div>
        <div class="card-body">
          <div class="stage-bar mb-4">
            <div class="stage-indicator">
              <div
                v-for="s in ['L1: 行业方向', 'L2: 标的筛选', 'L3: 组合构建', 'L4: 终裁处方']"
                :key="s"
                class="stage-dot"
                :class="{
                  active: currentStage === s.slice(0, 2),
                  done: stageDone(s.slice(0, 2))
                }"
              >
                <div class="dot" />
                <span class="stage-label">{{ s }}</span>
              </div>
            </div>
          </div>
          <div class="stream-log">
            <div v-for="(log, i) in l2Logs" :key="i" class="stream-log-item">
              <span class="log-node">{{ log.node }}</span>
              <span v-if="log.text" class="log-text">{{ log.text.slice(0, 200) }}...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== Result ====== -->
      <div v-if="phase === 'completed' && result" class="card mb-4">
        <div class="card-header">
          <span>分析结果</span>
          <el-tag type="success" size="small">完成 · 耗时 {{ result.elapsed_seconds }}s</el-tag>
        </div>
        <div class="card-body">
          <!-- 决策卡片 -->
          <h4 style="margin:0 0 12px">操作处方</h4>
          <div class="decision-card-stream">
            <DecisionCard
              v-for="item in sortedPrescription"
              :key="item.code"
              :item="item"
            />
          </div>
          <div v-if="!result.prescription?.length" style="color:#909399;font-size:13px;padding:12px 0">
            暂无操作建议
          </div>

          <!-- CIO 裁决 -->
          <h4 style="margin:20px 0 8px">CIO 裁决</h4>
          <div class="advice-text" v-html="renderMd(result.cio_verdict)" />

          <!-- 可折叠报告 -->
          <el-collapse style="margin-top:16px">
            <el-collapse-item v-if="result.macro_judge_verdict" title="L1 · 行业方向" name="l1">
              <div class="advice-text" v-html="renderMd(result.macro_judge_verdict)" />
            </el-collapse-item>
            <el-collapse-item v-if="result.stock_judge_verdict" title="L2 · 候选标的" name="l2">
              <div class="advice-text" v-html="renderMd(result.stock_judge_verdict)" />
            </el-collapse-item>
            <el-collapse-item title="L3 · 持仓分析师" name="analyst">
              <div class="advice-text" v-html="renderMd(result.analyst_assessment)" />
            </el-collapse-item>
            <el-collapse-item title="L3 · 策略师" name="strategist">
              <div class="advice-text" v-html="renderMd(result.strategist_assessment)" />
            </el-collapse-item>
            <el-collapse-item title="L3 · 侦察兵" name="scout">
              <div class="advice-text" v-html="renderMd(result.scout_assessment)" />
            </el-collapse-item>
            <el-collapse-item v-if="result.risk_director_review" title="L4 · 风险审查" name="risk">
              <div class="advice-text" v-html="renderMd(result.risk_director_review)" />
            </el-collapse-item>
            <el-collapse-item v-if="result.market_debate_history" title="辩论 · L1 行业辩论" name="m_debate">
              <div class="advice-text" v-html="renderMd(result.market_debate_history)" />
            </el-collapse-item>
            <el-collapse-item v-if="result.stock_debate_history" title="辩论 · L2 标的辩论" name="s_debate">
              <div class="advice-text" v-html="renderMd(result.stock_debate_history)" />
            </el-collapse-item>
            <el-collapse-item v-if="result.debate_history" title="辩论 · L3 组合辩论" name="debate">
              <div class="advice-text" v-html="renderMd(result.debate_history)" />
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <!-- ====== Error ====== -->
      <div v-if="phase === 'failed'" class="card mb-4">
        <div class="card-body">
          <el-result icon="error" title="分析失败" :sub-title="errorMsg || '未知错误'">
            <template #extra>
              <button class="btn btn-primary" @click="resetToIdle">重新分析</button>
            </template>
          </el-result>
        </div>
      </div>

      <!-- ====== Idle / Empty ====== -->
      <div v-if="phase === 'idle'" class="card">
        <div class="card-body">
          <div class="empty-state">
            <div class="empty-title">两阶段持仓分析</div>
            <div class="empty-desc">
              <p>Phase 1：基于你的全部持仓行业 + 投资目标，AI 逐行业判 Go/NoGo</p>
              <p>Phase 2：确认行业后，L2-L4 深度分析（标的筛选 → 组合构建 → 终裁处方）</p>
            </div>
            <div style="margin-top:20px;max-width:420px;margin-left:auto;margin-right:auto">
              <el-input
                v-model="userGoal"
                type="textarea"
                :rows="2"
                placeholder="投资目标（选填），如：年化收益10%、最大化收益。不填则由 AI 以值博率最高为目标"
                style="font-size:13px"
              />
            </div>
            <p style="color:#909399;font-size:12px;margin-top:16px">
              点击"开始分析"启动两阶段分析流程
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { portfolioApi, type AdviceItem, type PortfolioAdvice } from '@/api/paper'
import DecisionCard from '@/components/Analysis/DecisionCard.vue'

type Phase = 'idle' | 'planning' | 'plan_ready' | 'executing' | 'completed' | 'failed'

const phase = ref<Phase>('idle')
const errorMsg = ref('')
const taskId = ref('')
const executeId = ref('')
const userGoal = ref('')

// L1 state
const l1Logs = ref<Array<{ node: string; text: string }>>([])
const l1Industries = ref<Array<{ industry: string; recommendation: string; go_nogo: string; lifecycle: string; confidence: string; market: string; reasoning: string; priority: number; depth: string }>>([])
const selectedIndustries = ref<string[]>([])

// L2-L4 state
const l2Logs = ref<Array<{ node: string; text: string }>>([])
const currentStage = ref('L1')
const completedStages = ref<Set<string>>(new Set())

// Result
const result = ref<PortfolioAdvice | null>(null)

// SSE connections
let l1EventSource: EventSource | null = null
let l2EventSource: EventSource | null = null

const sortedPrescription = computed(() => {
  const items = (result.value?.prescription || []) as AdviceItem[]
  const order: Record<string, number> = { urgent: 0, important: 1, optional: 2 }
  return [...items].sort((a, b) => (order[a.priority || 'optional'] ?? 2) - (order[b.priority || 'optional'] ?? 2))
})

function stageDone(s: string) {
  return completedStages.value.has(s)
}

async function startL1Plan() {
  phase.value = 'planning'
  l1Logs.value = []
  l1Industries.value = []
  selectedIndustries.value = []
  errorMsg.value = ''

  try {
    const res = await portfolioApi.startL1Plan(userGoal.value.trim())
    if (!res.success || !res.data?.task_id) {
      throw new Error(res.message || '启动 L1 失败')
    }
    taskId.value = res.data.task_id
    connectL1SSE(res.data.task_id)
  } catch (e: any) {
    ElMessage.error(e?.message || '启动分析失败')
    phase.value = 'failed'
    errorMsg.value = e?.message || '启动分析失败'
  }
}

function connectL1SSE(tid: string) {
  closeL1SSE()
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const url = `${baseUrl}/api/stream/portfolio/${tid}`

  l1EventSource = new EventSource(url)

  l1EventSource.addEventListener('progress', (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'node_complete') {
        l1Logs.value.push({ node: data.node, text: data.text || '' })
      }
    } catch { /* ignore */ }
  })

  l1EventSource.addEventListener('error', () => {
    // SSE error → poll for L1 completion
    closeL1SSE()
    pollL1Completion()
  })

  // Fallback: poll after 5s
  setTimeout(() => {
    if (phase.value === 'planning') pollL1Completion()
  }, 5000)
}

function closeL1SSE() {
  if (l1EventSource) { l1EventSource.close(); l1EventSource = null }
}

async function pollL1Completion() {
  if (!taskId.value) return
  try {
    const res = await portfolioApi.getAnalysisStatus(taskId.value)
    if (res.success && res.data) {
      const d = res.data
      if (d.status === 'l1_completed' || d.status === 'completed') {
        if (d.result?.market_intel?.industries) {
          l1Industries.value = d.result.market_intel.industries
        }
        // Also check macro_judge_verdict for industries
        if (!l1Industries.value.length && d.result?.macro_judge_verdict) {
          // Try to parse from the verdict text
          extractIndustriesFromVerdict(d.result.macro_judge_verdict)
        }
        phase.value = 'plan_ready'
        closeL1SSE()
      } else if (d.status === 'failed') {
        phase.value = 'failed'
        errorMsg.value = d.result?.error || 'L1 分析失败'
      }
    }
  } catch { /* ignore */ }
}

function extractIndustriesFromVerdict(verdict: string) {
  // Try to parse industry names from the verdict text
  const lines = verdict.split('\n')
  const industries: typeof l1Industries.value = []
  for (const line of lines) {
    // Match patterns like "1. **银行** → Go" or "- 银行: Go"
    const m = line.match(/(?:\d+[\.\、]?\s*(?:\*\*)?|[-*]\s*)(.{2,8})(?:\*\*)?\s*(?:[→:]\s*|[：])?\s*(Go|NoGo|观望|观察)/i)
    if (m) {
      industries.push({
        industry: m[1].trim(),
        recommendation: m[2] === 'Go' ? 'Go' : m[2] === 'NoGo' ? 'NoGo' : 'Watch',
        go_nogo: m[2],
        lifecycle: '',
        confidence: '',
        market: 'cn',
        reasoning: '',
        depth: 'light',
        priority: m[2] === 'Go' ? 1 : 2,
      })
    }
  }
  if (industries.length) l1Industries.value = industries
}

async function startL2L4() {
  if (!selectedIndustries.value.length || !taskId.value) return
  phase.value = 'executing'
  l2Logs.value = []
  currentStage.value = 'L2'
  completedStages.value = new Set(['L1'])
  result.value = null

  try {
    const res = await portfolioApi.executeAnalysis(taskId.value, selectedIndustries.value)
    if (!res.success || !res.data?.task_id) {
      throw new Error(res.message || '启动执行失败')
    }
    executeId.value = res.data.task_id
    connectL2SSE(res.data.task_id)
  } catch (e: any) {
    ElMessage.error(e?.message || '启动执行失败')
    phase.value = 'failed'
    errorMsg.value = e?.message || '启动执行失败'
  }
}

function connectL2SSE(tid: string) {
  closeL2SSE()
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const url = `${baseUrl}/api/stream/portfolio/${tid}`

  l2EventSource = new EventSource(url)

  l2EventSource.addEventListener('progress', (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'node_complete') {
        l2Logs.value.push({ node: data.node, text: data.text || '' })
        const stage = data.stage || ''
        if (stage.startsWith('2')) { currentStage.value = 'L2'; completedStages.value.add('L1') }
        if (stage.startsWith('3')) { currentStage.value = 'L3'; completedStages.value.add('L2') }
        if (stage.startsWith('4')) { currentStage.value = 'L4'; completedStages.value.add('L3') }
      }
    } catch { /* ignore */ }
  })

  l2EventSource.addEventListener('error', () => {
    closeL2SSE()
    pollL2L4Completion()
  })

  // Fallback poll
  setTimeout(() => {
    if (phase.value === 'executing') pollL2L4Completion()
  }, 10000)
}

function closeL2SSE() {
  if (l2EventSource) { l2EventSource.close(); l2EventSource = null }
}

async function pollL2L4Completion() {
  if (!taskId.value) return
  try {
    const res = await portfolioApi.getAnalysisStatus(taskId.value)
    if (res.success && res.data) {
      const d = res.data
      if (d.status === 'completed') {
        completedStages.value.add('L4')
        currentStage.value = 'L4'
        result.value = d.result
        phase.value = 'completed'
        closeL2SSE()
        ElMessage.success('持仓分析完成')
      } else if (d.status === 'failed') {
        phase.value = 'failed'
        errorMsg.value = d.result?.error || '分析失败'
        closeL2SSE()
      }
    }
  } catch { /* ignore */ }
}

function resetToIdle() {
  closeL1SSE()
  closeL2SSE()
  phase.value = 'idle'
  l1Logs.value = []
  l1Industries.value = []
  selectedIndustries.value = []
  l2Logs.value = []
  currentStage.value = 'L1'
  completedStages.value = new Set()
  result.value = null
  taskId.value = ''
  executeId.value = ''
}

function renderMd(text: string | undefined): string {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

onUnmounted(() => {
  closeL1SSE()
  closeL2SSE()
})
</script>

<style scoped>
.portfolio-analysis {
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

.page-content { max-width: 1200px; margin: 0 auto; padding: 24px; }

/* Flex helpers */
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.mb-4 { margin-bottom: 16px; }
.mb-5 { margin-bottom: 20px; }
.w-5 { width: 20px; }
.h-5 { height: 20px; }
.text-base { font-size: 14px; }
.font-semibold { font-weight: 600; }

/* Card */
.card { background: #fff; border-radius: 8px; border: 1px solid #ebeef5; }
.card-header { padding: 14px 20px; border-bottom: 1px solid #ebeef5; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: space-between; }
.card-body { padding: 20px; }

/* Buttons */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 4px; font-size: 14px; cursor: pointer; border: 1px solid; transition: all 0.2s; font-weight: 400; line-height: 1; white-space: nowrap; }
.btn-primary { background: #409eff; color: #fff; border-color: #409eff; }
.btn-primary:hover { background: #66b1ff; border-color: #66b1ff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-plain { background: #fff; border-color: #dcdfe6; color: #606266; }
.btn-plain:hover { color: #409eff; border-color: #c6e2ff; background: #ecf5ff; }
.btn-sm { padding: 5px 12px; font-size: 12px; }

/* Stream log */
.stream-log { background: #1e1e1e; border-radius: 6px; padding: 12px 16px; max-height: 320px; overflow-y: auto; font-family: 'Menlo', 'Monaco', monospace; font-size: 12px; }
.stream-log-item { padding: 4px 0; display: flex; gap: 12px; }
.log-node { color: #4ec9b0; white-space: nowrap; min-width: 120px; }
.log-text { color: #d4d4d4; }

/* Industry selection */
.industry-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; margin-top: 8px; }
.industry-card { border: 1px solid #ebeef5; border-radius: 6px; padding: 12px; transition: border-color 0.2s; cursor: pointer; }
.industry-card:hover { border-color: #b3d8ff; }
.industry-card.selected { border-color: #409eff; background: #ecf5ff; }
.industry-card.is-opportunity { border-color: #e1f3d8; background: #f0f9eb; }
.industry-card.is-opportunity:hover { border-color: #b3e19d; }
.industry-card.is-opportunity.selected { border-color: #67c23a; background: #e1f3d8; }
.ind-info { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.ind-name { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; }
.ind-meta { display: flex; gap: 12px; font-size: 12px; color: #909399; }
.ind-reason { font-size: 12px; color: #606266; line-height: 1.5; margin-top: 4px; }

/* Stage bar */
.stage-indicator { display: flex; justify-content: space-between; align-items: flex-start; }
.stage-dot { display: flex; flex-direction: column; align-items: center; gap: 6px; flex: 1; position: relative; }
.stage-dot::after { content: ''; position: absolute; top: 8px; left: calc(50% + 12px); width: calc(100% - 24px); height: 2px; background: #ebeef5; }
.stage-dot:last-child::after { display: none; }
.stage-dot .dot { width: 16px; height: 16px; border-radius: 50%; background: #ebeef5; border: 2px solid #dcdfe6; }
.stage-dot.active .dot { background: #409eff; border-color: #409eff; animation: pulse 1.5s infinite; }
.stage-dot.done .dot { background: #67c23a; border-color: #67c23a; }
.stage-dot.done::after { background: #67c23a; }
.stage-label { font-size: 11px; color: #909399; text-align: center; }
.stage-dot.active .stage-label { color: #409eff; font-weight: 600; }
.stage-dot.done .stage-label { color: #67c23a; }

@keyframes pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(64,158,255,0.4); } 50% { box-shadow: 0 0 0 6px rgba(64,158,255,0); } }

/* Decision card stream */
.decision-card-stream { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 12px; }

/* Advice text */
.advice-text { font-size: 13px; line-height: 1.7; color: #303133; word-break: break-word; }

/* Empty state */
.empty-state { text-align: center; padding: 40px 20px; }
.empty-title { font-size: 18px; font-weight: 600; color: #303133; margin-bottom: 12px; }
.empty-desc { font-size: 14px; color: #606266; line-height: 1.8; }
</style>
