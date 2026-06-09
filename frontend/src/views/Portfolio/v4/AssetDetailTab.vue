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

          <!-- §5.9 B：较上次 / 自检（结果闭环反思 Layer 1），首跑或无历史不显示 -->
          <div
            v-if="detail.verdict.reflection && detail.verdict.reflection.self_check !== 'first_run'"
            class="adt-reflection"
          >
            <div class="adt-reflection-tag">较上次 / 自检</div>
            <p v-if="detail.verdict.reflection.prev_stance">
              <b>上次结论：</b>{{ stanceText(detail.verdict.reflection.prev_stance) }}
              <span v-if="detail.verdict.reflection.prev_date" class="adt-reflection-date">
                （{{ detail.verdict.reflection.prev_date }}）
              </span>
            </p>
            <p v-if="detail.verdict.reflection.what_changed"><b>变化：</b>{{ detail.verdict.reflection.what_changed }}</p>
            <p v-if="detail.verdict.reflection.why_changed"><b>改判原因：</b>{{ detail.verdict.reflection.why_changed }}</p>
            <p v-if="detail.verdict.reflection.self_check"><b>自检：</b>{{ detail.verdict.reflection.self_check }}</p>
          </div>
        </div>
        <EmptyUnitState
          v-else
          title="尚未深析此大类"
          :cli-hint="detail.asset_unit.cli_hint"
        />
      </div>

      <!-- §5.9 A：大类深辩历程（折叠）+ 三专项分析师 -->
      <div v-if="detail.debate_rounds?.length" class="card adt-debate">
        <el-collapse>
          <el-collapse-item :title="`大类深辩历程（${detail.debate_rounds.length} 轮 多空辩论）`" name="debate">
            <div v-for="rd in detail.debate_rounds" :key="rd.round" class="adt-round">
              <div class="adt-round-no">第 {{ rd.round }} 轮</div>
              <div class="adt-duel">
                <div class="adt-bull">
                  <div class="adt-side-tag adt-tag-bull">多头</div>
                  <p>{{ extractText(rd.bull) }}</p>
                </div>
                <div class="adt-bear">
                  <div class="adt-side-tag adt-tag-bear">空头</div>
                  <p>{{ extractText(rd.bear) }}</p>
                </div>
              </div>
            </div>
          </el-collapse-item>

          <el-collapse-item
            v-if="analystList.length"
            :title="`专项分析师视角（${analystList.length} 位）`"
            name="analysts"
          >
            <div v-for="a in analystList" :key="a.key" class="adt-analyst">
              <div class="adt-analyst-tag">{{ a.label }}</div>
              <p>{{ a.text }}</p>
            </div>
          </el-collapse-item>
        </el-collapse>
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

const STANCE_ZH: Record<string, string> = { bullish: '看多', bearish: '看空', neutral: '中性', neutral_hold: '中性', unclassified_hold: '待归类' }

const stanceLabel = computed(
  () => STANCE_ZH[detail.value?.verdict?.stance || ''] || detail.value?.verdict?.stance,
)
const stanceType = computed(
  () => ({ bullish: 'success', bearish: 'danger', neutral: 'info', neutral_hold: 'info', unclassified_hold: 'info' }[detail.value?.verdict?.stance || ''] || 'info') as 'success' | 'danger' | 'info',
)

function stanceText(s?: string | null): string {
  if (!s) return ''
  return STANCE_ZH[s] || s
}

// 照搬行业层：辩论 side 可能是字符串或对象，统一抽文本
function extractText(side: any): string {
  if (!side) return ''
  if (typeof side === 'string') return side
  return side.thesis || side.challenge || side.reasoning || JSON.stringify(side).slice(0, 300)
}

// 三专项分析师（macro/flow/policy）→ 展示用列表
const ANALYST_LABEL: Record<string, string> = { macro: '宏观', flow: '资金', policy: '政策' }
const analystList = computed(() => {
  const a = detail.value?.analysts || {}
  return Object.keys(a).map((key) => ({
    key,
    label: ANALYST_LABEL[key] || key,
    text: a[key]?.reasoning || extractText(a[key]),
  }))
})

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
.adt-reflection {
  margin-top: 14px;
  padding: 10px 12px;
  border-left: 3px solid #409eff;
  background: #f4f8ff;
  border-radius: 4px;
}
.adt-reflection-tag {
  font-size: 12px;
  font-weight: 700;
  color: #409eff;
  margin-bottom: 6px;
}
.adt-reflection p {
  margin: 4px 0;
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}
.adt-reflection-date { color: #909399; }
.adt-debate {
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}
.adt-round { margin-bottom: 14px; }
.adt-round-no { font-weight: 700; color: #909399; font-size: 12px; margin-bottom: 6px; }
.adt-duel { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.adt-side-tag { display: inline-block; font-size: 11px; padding: 1px 8px; border-radius: 8px; margin-bottom: 4px; }
.adt-tag-bull { background: #f0f9eb; color: #67c23a; }
.adt-tag-bear { background: #fef0f0; color: #f56c6c; }
.adt-duel p { font-size: 12px; color: #606266; line-height: 1.5; margin: 0; }
.adt-analyst { margin-bottom: 12px; }
.adt-analyst-tag {
  display: inline-block;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 8px;
  margin-bottom: 4px;
  background: #ecf5ff;
  color: #409eff;
}
.adt-analyst p { font-size: 12px; color: #606266; line-height: 1.5; margin: 0; }
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
