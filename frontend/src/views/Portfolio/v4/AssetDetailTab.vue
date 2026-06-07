<template>
  <div class="asset-detail-tab">
    <div v-if="loading" class="adt-loading"><el-skeleton :rows="4" animated /></div>

    <template v-else-if="detail">
      <!-- 头部：大类研判 verdict -->
      <div class="adt-head card">
        <div class="adt-head-row">
          <span class="adt-title">
            {{ detail.label }}
            <UnitStatusBadge
              :status="detail.asset_unit.status"
              :stale-reason="detail.asset_unit.stale_reason"
              :cli-hint="detail.asset_unit.cli_hint"
              :meta="detail.asset_unit"
            />
          </span>
          <el-tag v-if="detail.verdict?.stance" :type="stanceType" effect="plain">
            {{ stanceLabel }}
          </el-tag>
        </div>

        <div v-if="detail.verdict" class="adt-verdict">
          <p v-if="detail.verdict.situation"><b>形势：</b>{{ detail.verdict.situation }}</p>
          <p v-if="detail.verdict.direction"><b>方向：</b>{{ detail.verdict.direction }}</p>
          <p v-if="detail.verdict.trend"><b>趋势：</b>{{ detail.verdict.trend }}</p>
          <div v-if="detail.verdict.risks?.length" class="adt-risks">
            <b>主要风险：</b>
            <el-tag v-for="(r, i) in detail.verdict.risks" :key="i" type="danger" size="small" effect="plain">
              {{ r }}
            </el-tag>
          </div>
        </div>
        <EmptyUnitState
          v-else
          title="尚未深析此大类"
          :cli-hint="detail.asset_unit.cli_hint"
        />
      </div>

      <!-- 权益：行业表格（AC8.2 权益） -->
      <div v-if="detail.is_equity" class="card adt-body">
        <IndustryTable
          :industries="detail.industries || []"
          :alloc-unit="detail.equity_industries_unit"
          :equity-quota="equityQuota"
          @open-industry="$emit('open-industry', $event)"
        />
      </div>

      <!-- 非权益：差异化方案（AC8.2 非权益，FR-007） -->
      <div v-else class="card adt-body">
        <div class="adt-plan-head">
          投资方案
          <UnitStatusBadge
            v-if="detail.plan_unit"
            :status="detail.plan_unit.status"
            :stale-reason="detail.plan_unit.stale_reason"
            :cli-hint="detail.plan_unit.cli_hint"
            :meta="detail.plan_unit"
          />
        </div>
        <PlanCard :plan="detail.plan" :asset-class="detail.asset_class" :label="detail.label" />

        <!-- 持有型敞口 -->
        <div v-if="detail.holding_only_exposure" class="adt-exposure">
          持有型敞口（仅记录，不推荐标的）：<b>{{ detail.holding_only_exposure }}</b>
        </div>
      </div>
    </template>

    <EmptyUnitState v-else title="无数据" />
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import UnitStatusBadge from './UnitStatusBadge.vue'
import EmptyUnitState from './EmptyUnitState.vue'
import IndustryTable from './IndustryTable.vue'
import PlanCard from './PlanCard.vue'
import { useAssetDetail } from './useV4Units'

const props = defineProps<{
  assetClass: string
  equityQuota?: number | null
}>()

defineEmits<{ (e: 'open-industry', name: string): void }>()

const { detail, loading, load } = useAssetDetail()

const stanceLabel = computed(
  () => ({ bullish: '看多', bearish: '看空', neutral: '中性' }[detail.value?.verdict?.stance || ''] || detail.value?.verdict?.stance),
)
const stanceType = computed(
  () => ({ bullish: 'success', bearish: 'danger', neutral: 'info' }[detail.value?.verdict?.stance || ''] || 'info') as 'success' | 'danger' | 'info',
)

watch(() => props.assetClass, (c) => { if (c) load(c) }, { immediate: true })
</script>

<style scoped>
.adt-loading { padding: 20px; }
.adt-head {
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}
.adt-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.adt-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 10px;
}
.adt-verdict p {
  margin: 6px 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
.adt-risks {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.adt-body {
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}
.adt-plan-head {
  font-size: 15px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.adt-exposure {
  margin-top: 14px;
  font-size: 13px;
  color: #909399;
}
</style>
