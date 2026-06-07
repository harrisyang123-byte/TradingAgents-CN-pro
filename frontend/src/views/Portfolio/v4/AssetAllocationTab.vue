<template>
  <div class="asset-allocation-tab">
    <div v-if="loading" class="aat-loading">
      <el-skeleton :rows="4" animated />
    </div>

    <EmptyUnitState
      v-else-if="!overview || !overview.has_data"
      title="尚无 v4 分析数据"
      description="v4 采用分层独立分析：先逐类深析，再做资产配比。请在 CLI 中按需触发。"
      cli-hint="./scripts/run_v4.sh analyze asset:equity"
    />

    <template v-else>
      <!-- 配比总监结论条 -->
      <div class="aat-alloc-head card">
        <div class="aat-alloc-head-row">
          <div class="aat-title">
            资产配比决策
            <UnitStatusBadge
              :status="overview.allocation.status"
              :stale-reason="overview.allocation.stale_reason"
              :cli-hint="overview.allocation.cli_hint"
              :meta="overview.allocation"
            />
          </div>
          <div class="aat-quota">
            权益额度 equity_quota：
            <b :class="{ 'aat-quota-zero': overview.equity_disabled }">
              {{ overview.equity_quota != null ? overview.equity_quota + '%' : '--' }}
            </b>
            <el-tag v-if="overview.equity_disabled" type="info" size="small" effect="plain">
              本期不配置权益
            </el-tag>
          </div>
        </div>

        <div v-if="overview.allocation.summary" class="aat-summary">
          {{ overview.allocation.summary }}
        </div>

        <!-- Σ 校验 + 缺失/过时软提醒 -->
        <div class="aat-warnings">
          <el-tag
            v-if="overview.allocation.sum_check != null"
            :type="sumOk ? 'success' : 'danger'"
            size="small"
            effect="plain"
          >
            Σ目标 = {{ overview.allocation.sum_check }}%{{ sumOk ? '' : '（≠100，请复核）' }}
          </el-tag>
          <el-tag
            v-for="(w, i) in overview.allocation.input_warnings"
            :key="i"
            type="warning"
            size="small"
            effect="plain"
          >
            {{ classLabel(w.asset_class) }}：{{ w.issue === 'missing' ? '分析缺失' : w.issue === 'stale' ? '分析过时' : w.issue }}
          </el-tag>
        </div>

        <div
          v-if="overview.allocation.status === 'gray'"
          class="aat-no-alloc"
        >
          ⚠️ 尚未生成资产配比。各大类分析就绪后，在 CLI 运行
          <code>./scripts/run_v4.sh analyze alloc:portfolio</code> 生成七大类目标配比。
        </div>
      </div>

      <!-- 七大类卡片（AC8.1：卡片，状态色+摘要+当前→目标） -->
      <div class="aat-cards">
        <AssetCard
          v-for="card in overview.asset_cards"
          :key="card.asset_class"
          :card="card"
          :clickable="cardClickable(card)"
          @open="$emit('open-asset', $event)"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import AssetCard from './AssetCard.vue'
import UnitStatusBadge from './UnitStatusBadge.vue'
import EmptyUnitState from './EmptyUnitState.vue'
import { classLabel } from './assetClasses'
import { useV4Overview } from './useV4Units'
import type { AssetCardData } from '@/api/portfolioV4'

defineEmits<{ (e: 'open-asset', assetClass: string): void }>()

const { overview, loading, load } = useV4Overview()

const sumOk = computed(() => {
  const s = overview.value?.allocation.sum_check
  return s == null || Math.abs(s - 100) <= 1
})

// 权益若 equity_quota=0 则不可下钻；其余大类只要存在分析/方案即可点
function cardClickable(card: AssetCardData): boolean {
  if (card.asset_class === 'equity') {
    return !(overview.value?.equity_disabled)
  }
  return true
}

onMounted(load)
defineExpose({ reload: load })
</script>

<style scoped>
.aat-loading {
  padding: 20px;
}
.aat-alloc-head {
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}
.aat-alloc-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
.aat-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 10px;
}
.aat-quota {
  font-size: 13px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 8px;
}
.aat-quota b {
  font-size: 16px;
  color: #409eff;
}
.aat-quota-zero {
  color: #909399 !important;
}
.aat-summary {
  margin-top: 10px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  padding: 8px 12px;
  background: #f4f4f5;
  border-radius: 6px;
}
.aat-warnings {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.aat-no-alloc {
  margin-top: 10px;
  font-size: 13px;
  color: #e6a23c;
  line-height: 1.6;
}
.aat-no-alloc code {
  background: #fdf6ec;
  padding: 2px 6px;
  border-radius: 4px;
  color: #b88230;
}
.aat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
</style>
