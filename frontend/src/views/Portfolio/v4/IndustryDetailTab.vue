<template>
  <div class="industry-detail-tab">
    <div v-if="loading" class="idt-loading"><el-skeleton :rows="4" animated /></div>

    <template v-else-if="detail">
      <!-- 行业深辩报告头 -->
      <div class="idt-head card">
        <div class="idt-head-row">
          <span class="idt-title">
            {{ detail.industry }}
            <UnitStatusBadge
              :status="detail.industry_unit.status"
              :stale-reason="detail.industry_unit.stale_reason"
              :cli-hint="detail.industry_unit.cli_hint"
              :meta="detail.industry_unit"
            />
          </span>
          <el-tag v-if="detail.verdict?.stance" :type="stanceType" effect="plain">
            {{ stanceLabel }}
          </el-tag>
        </div>

        <div v-if="detail.verdict" class="idt-verdict">
          <p v-if="detail.verdict.situation"><b>景气/形势：</b>{{ detail.verdict.situation }}</p>
          <p v-if="detail.verdict.direction"><b>方向/空间：</b>{{ detail.verdict.direction }}</p>
          <div v-if="detail.verdict.risks?.length" class="idt-risks">
            <b>风险：</b>
            <el-tag v-for="(r, i) in detail.verdict.risks" :key="i" type="danger" size="small" effect="plain">{{ r }}</el-tag>
          </div>
        </div>
        <EmptyUnitState v-else title="尚未深辩此行业" :cli-hint="detail.industry_unit.cli_hint" />
      </div>

      <!-- 辩论历程（折叠） -->
      <div v-if="detail.debate_rounds?.length" class="card idt-debate">
        <el-collapse>
          <el-collapse-item :title="`行业深辩历程（${detail.debate_rounds.length} 轮）`" name="debate">
            <div v-for="rd in detail.debate_rounds" :key="rd.round" class="idt-round">
              <div class="idt-round-no">第 {{ rd.round }} 轮</div>
              <div class="idt-duel">
                <div class="idt-bull">
                  <div class="idt-side-tag idt-tag-bull">多头</div>
                  <p>{{ extractText(rd.bull) }}</p>
                </div>
                <div class="idt-bear">
                  <div class="idt-side-tag idt-tag-bear">空头</div>
                  <p>{{ extractText(rd.bear) }}</p>
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 个股表格 + 行业内配比（AC8.3） -->
      <div class="card idt-body">
        <div class="idt-stocks-head">
          行业内个股分析 + 资金配比
          <UnitStatusBadge
            v-if="detail.intra_alloc_unit"
            :status="detail.intra_alloc_unit.status"
            :stale-reason="detail.intra_alloc_unit.stale_reason"
            :cli-hint="detail.intra_alloc_unit.cli_hint"
            :meta="detail.intra_alloc_unit"
          />
        </div>
        <StockTable :stocks="detail.stocks || []" :stock-weights="detail.stock_weights || []" />
      </div>
    </template>

    <EmptyUnitState v-else title="无数据" />
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import UnitStatusBadge from './UnitStatusBadge.vue'
import EmptyUnitState from './EmptyUnitState.vue'
import StockTable from './StockTable.vue'
import { useIndustryDetail } from './useV4Units'

const props = defineProps<{ industry: string }>()

const { detail, loading, load } = useIndustryDetail()

const stanceLabel = computed(
  () => ({ bullish: '看多', bearish: '看空', neutral: '中性' }[detail.value?.verdict?.stance || ''] || detail.value?.verdict?.stance),
)
const stanceType = computed(
  () => ({ bullish: 'success', bearish: 'danger', neutral: 'info' }[detail.value?.verdict?.stance || ''] || 'info') as 'success' | 'danger' | 'info',
)

function extractText(side: any): string {
  if (!side) return ''
  if (typeof side === 'string') return side
  return side.thesis || side.challenge || side.reasoning || JSON.stringify(side).slice(0, 300)
}

watch(() => props.industry, (n) => { if (n) load(n) }, { immediate: true })
</script>

<style scoped>
.idt-loading { padding: 20px; }
.idt-head, .idt-debate, .idt-body {
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}
.idt-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.idt-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 10px;
}
.idt-verdict p { margin: 6px 0; font-size: 13px; color: #606266; line-height: 1.6; }
.idt-risks { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.idt-round { margin-bottom: 14px; }
.idt-round-no { font-weight: 700; color: #909399; font-size: 12px; margin-bottom: 6px; }
.idt-duel { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.idt-side-tag { display: inline-block; font-size: 11px; padding: 1px 8px; border-radius: 8px; margin-bottom: 4px; }
.idt-tag-bull { background: #f0f9eb; color: #67c23a; }
.idt-tag-bear { background: #fef0f0; color: #f56c6c; }
.idt-duel p { font-size: 12px; color: #606266; line-height: 1.5; margin: 0; }
.idt-stocks-head {
  font-size: 15px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
