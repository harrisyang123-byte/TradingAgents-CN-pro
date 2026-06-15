<template>
  <div class="plan-card">
    <div v-if="!plan" class="pc-empty">
      <EmptyUnitState
        title="尚未生成投资方案"
        :description="`「${label}」的差异化投资方案需在 CLI 中触发分析`"
        :cli-hint="`./scripts/run_v4.sh analyze plan:${assetClass}`"
      />
    </div>

    <template v-else>
      <!-- 现金：持有结构（持有型，不荐个券） -->
      <div v-if="plan.holding_structure?.length" class="pc-section">
        <div class="pc-section-title">持有结构建议</div>
        <el-table :data="plan.holding_structure" size="small" border>
          <el-table-column prop="vehicle" label="工具" min-width="120" />
          <el-table-column label="建议占比" width="100" align="center">
            <template #default="{ row }">
              <b>{{ fmtPct(row.suggest_pct) }}</b>
            </template>
          </el-table-column>
          <el-table-column prop="reasoning" label="理由" min-width="220" show-overflow-tooltip />
        </el-table>
        <div v-if="plan.note" class="pc-note">{{ plan.note }}</div>
      </div>

      <!-- 固收：久期 + 品种结构 -->
      <div v-if="plan.duration_view" class="pc-section">
        <div class="pc-section-title">久期取向</div>
        <el-tag type="warning" effect="plain">{{ plan.duration_view }}</el-tag>
      </div>

      <!-- 通用品种/工具 mix（固收/大宗/贵金属/房地产/另类） -->
      <div v-if="plan.instrument_mix?.length" class="pc-section">
        <div class="pc-section-title">品种 / 工具配置</div>
        <el-table :data="plan.instrument_mix" size="small" border>
          <el-table-column prop="instrument" label="品种/工具" min-width="140" />
          <el-table-column label="可交易" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.tradable === true" type="success" size="small" effect="plain">可下钻</el-tag>
              <el-tag v-else-if="row.tradable === false" type="info" size="small" effect="plain">记敞口</el-tag>
              <span v-else>--</span>
            </template>
          </el-table-column>
          <el-table-column label="建议占比" width="100" align="center">
            <template #default="{ row }">
              <b>{{ fmtPct(row.suggest_pct) }}</b>
            </template>
          </el-table-column>
          <el-table-column prop="reasoning" label="理由" min-width="200" show-overflow-tooltip />
        </el-table>
      </div>

      <!-- 房地产实物敞口说明 -->
      <div v-if="plan.holding_only_note" class="pc-note pc-holding">
        🏠 {{ plan.holding_only_note }}
      </div>

      <!-- 风险标注（另类/大宗高波动+合规） -->
      <div v-if="plan.risk_flags?.length" class="pc-section">
        <div class="pc-section-title pc-risk-title">⚠ 风险提示</div>
        <div class="pc-risks">
          <el-tag v-for="(f, i) in plan.risk_flags" :key="i" type="danger" size="small" effect="dark">
            {{ f }}
          </el-tag>
        </div>
      </div>

      <!-- 新 schema(扁平方案: 固收/现金/大宗/贵金属/房地产/另类)：立场+摘要+结构目标+行动计划 -->
      <div v-if="anyNewSchema" class="pc-newschema">
        <div v-if="plan.stance || plan.target_weight != null" class="pc-section">
          <div class="pc-section-title">配置立场</div>
          <el-tag :type="stanceTagType" effect="plain">{{ stanceZh }}</el-tag>
          <span v-if="plan.current_weight != null || plan.target_weight != null" class="pc-weight">
            {{ fmtPct(plan.current_weight) }} → <b>{{ fmtPct(plan.target_weight) }}</b>
          </span>
        </div>
        <div v-if="plan.summary" class="pc-section">
          <div class="pc-section-title">方案摘要</div>
          <p class="pc-text">{{ plan.summary }}</p>
        </div>
        <div v-if="plan.structure_target" class="pc-section">
          <div class="pc-section-title">结构目标（买什么）</div>
          <p class="pc-text pc-target">{{ plan.structure_target }}</p>
        </div>
        <div v-if="plan.action_plan" class="pc-section">
          <div class="pc-section-title">行动计划</div>
          <div class="pc-actions">
            <div v-for="(v, k) in normalizedActionPlan" :key="k" class="pc-action-row">
              <span class="pc-action-key">{{ actionKeyZh(String(k)) }}</span>
              <span class="pc-action-val">{{ v }}</span>
            </div>
          </div>
        </div>
        <div v-if="plan.valuation_basis" class="pc-section">
          <div class="pc-section-title">估值依据</div>
          <p class="pc-text">{{ plan.valuation_basis }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import EmptyUnitState from './EmptyUnitState.vue'
import type { AssetPlan } from '@/api/portfolioV4'

const props = defineProps<{
  plan: AssetPlan | null | undefined
  assetClass: string
  label: string
}>()

function fmtPct(v: number | null | undefined): string {
  if (v == null) return '--'
  return `${Number(v).toFixed(1)}%`
}

// 新扁平 schema 检测（任一新字段存在）
const anyNewSchema = computed(() => {
  const p = props.plan as Record<string, unknown> | null | undefined
  if (!p) return false
  return !!(p.stance || p.summary || p.structure_target || p.action_plan || p.valuation_basis)
})

const STANCE_ZH: Record<string, string> = {
  reduce: '减配', add: '加配', overweight: '超配', underweight: '低配',
  hold: '持有', zero: '清零/不配', bullish: '看多', slight_add: '小幅加配',
  opportunistic_build: '择机建仓', overweight_init: '超配起步', add_REITs_only: '仅配 REITs',
}
const stanceZh = computed(() => {
  const s = (props.plan as Record<string, unknown> | null)?.stance as string | undefined
  return s ? (STANCE_ZH[s] || s) : ''
})
const stanceTagType = computed(() => {
  const s = (props.plan as Record<string, unknown> | null)?.stance as string | undefined
  if (!s) return 'info'
  if (/add|overweight|bullish|build/.test(s)) return 'success'
  if (/reduce|underweight|zero/.test(s)) return 'warning'
  return 'info'
}) as unknown as () => 'success' | 'warning' | 'info'

// action_plan 可能是对象或字符串，统一成 key→value
const normalizedActionPlan = computed<Record<string, string>>(() => {
  const ap = (props.plan as Record<string, unknown> | null)?.action_plan
  if (!ap) return {}
  if (typeof ap === 'string') return { plan: ap }
  if (typeof ap === 'object') {
    const out: Record<string, string> = {}
    for (const [k, v] of Object.entries(ap as Record<string, unknown>)) out[k] = String(v)
    return out
  }
  return {}
})
const ACTION_KEY_ZH: Record<string, string> = {
  immediate: '立即', immediate_add: '立即加仓', conditional_add_batch2: '条件加仓(二批)',
  trigger_add: '触发加仓', trigger: '触发条件', execution: '执行', stage2: '第二阶段',
  stop_loss: '止损线',
}
function actionKeyZh(k: string): string { return ACTION_KEY_ZH[k] || k }
</script>

<style scoped>
.plan-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pc-section-title {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}
.pc-risk-title {
  color: #f56c6c;
}
.pc-note {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}
.pc-holding {
  padding: 8px 12px;
  background: #f0f9eb;
  border-radius: 6px;
  color: #67833a;
}
.pc-risks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.pc-newschema { display: flex; flex-direction: column; gap: 16px; }
.pc-text { font-size: 13px; color: #303133; line-height: 1.7; margin: 0; }
.pc-target { background: #f0f9eb; padding: 8px 12px; border-radius: 6px; color: #529b2e; font-weight: 600; }
.pc-weight { margin-left: 10px; font-size: 13px; color: #606266; }
.pc-actions { display: flex; flex-direction: column; gap: 6px; }
.pc-action-row { display: flex; gap: 10px; font-size: 13px; line-height: 1.6; }
.pc-action-key { flex: 0 0 96px; font-weight: 600; color: #409eff; }
.pc-action-val { flex: 1; color: #303133; }
</style>
