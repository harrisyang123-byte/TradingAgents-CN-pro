<template>
  <div class="industry-table-wrap">
    <div class="it-head">
      <span class="it-title">
        行业间资金配比
        <UnitStatusBadge
          v-if="allocUnit"
          :status="allocUnit.status"
          :stale-reason="allocUnit.stale_reason"
          :cli-hint="allocUnit.cli_hint"
          :meta="allocUnit"
        />
      </span>
      <span v-if="equityQuota != null" class="it-quota">
        权益额度上限 {{ equityQuota }}% · 已分配
        <b :class="{ 'it-over': sumWeight > equityQuota + 0.5 }">{{ sumWeight.toFixed(1) }}%</b>
      </span>
    </div>

    <EmptyUnitState
      v-if="!industries || !industries.length"
      title="尚未生成行业配比"
      description="权益深链顺序：先逐个行业深辩定方向，再做行业间配比。"
      cli-hint="./scripts/run_v4.sh analyze alloc:equity_industries"
    />

    <el-table v-else :data="industries" border size="default" @row-click="onRowClick">
      <el-table-column prop="industry" label="行业" min-width="140">
        <template #default="{ row }">
          <span class="it-link">{{ row.industry }}</span>
        </template>
      </el-table-column>
      <el-table-column label="目标权重" width="120" align="center" sortable :sort-by="(r: any) => r.target_weight">
        <template #default="{ row }">
          <b class="it-weight">{{ fmtPct(row.target_weight) }}</b>
        </template>
      </el-table-column>
      <el-table-column prop="reasoning" label="配置理由" min-width="240" show-overflow-tooltip />
      <el-table-column label="操作" width="100" align="center">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click.stop="$emit('open-industry', row.industry)">
            查看个股 →
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import UnitStatusBadge from './UnitStatusBadge.vue'
import EmptyUnitState from './EmptyUnitState.vue'
import type { IndustryAllocationRow, UnitMeta } from '@/api/portfolioV4'

const props = defineProps<{
  industries: IndustryAllocationRow[]
  allocUnit?: UnitMeta | null
  equityQuota?: number | null
}>()

const emit = defineEmits<{ (e: 'open-industry', name: string): void }>()

const sumWeight = computed(() =>
  (props.industries || []).reduce((acc, r) => acc + (Number(r.target_weight) || 0), 0),
)

function onRowClick(row: IndustryAllocationRow) {
  emit('open-industry', row.industry)
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return '--'
  return `${Number(v).toFixed(1)}%`
}
</script>

<style scoped>
.it-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}
.it-title {
  font-size: 15px;
  font-weight: 700;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 10px;
}
.it-quota {
  font-size: 13px;
  color: #606266;
}
.it-quota b {
  color: #409eff;
}
.it-over {
  color: #f56c6c !important;
}
.it-link {
  color: #409eff;
  cursor: pointer;
}
.it-weight {
  color: #409eff;
}
</style>
