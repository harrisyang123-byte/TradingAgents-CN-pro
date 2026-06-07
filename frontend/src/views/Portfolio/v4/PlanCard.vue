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
    </template>
  </div>
</template>

<script setup lang="ts">
import EmptyUnitState from './EmptyUnitState.vue'
import type { AssetPlan } from '@/api/portfolioV4'

defineProps<{
  plan: AssetPlan | null | undefined
  assetClass: string
  label: string
}>()

function fmtPct(v: number | null | undefined): string {
  if (v == null) return '--'
  return `${Number(v).toFixed(1)}%`
}
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
</style>
