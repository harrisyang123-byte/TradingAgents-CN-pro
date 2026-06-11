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

      <!-- 前瞻视野 forward_view（A/B 测试落地：11 维内化前瞻能力） -->
      <div v-if="detail.verdict?.forward_view" class="card adt-forward">
        <el-collapse>
          <el-collapse-item name="forward">
            <template #title>
              <span class="adt-forward-title">🔭 前瞻视野（未来 4 周日历 + 三情景 + 触发监控）</span>
            </template>

            <!-- 触发监控 (置顶,最可执行) -->
            <div v-if="fv.trigger_monitor?.length" class="fv-section fv-trigger">
              <div class="fv-section-title">⚡ 触发监控（看到 X 就 Y · 绝对阈值）</div>
              <ol class="fv-list">
                <li v-for="(t, i) in fv.trigger_monitor" :key="i">{{ t }}</li>
              </ol>
            </div>

            <!-- 近期日历 -->
            <div v-if="fv.near_term_calendar?.length" class="fv-section">
              <div class="fv-section-title">📅 未来 4 周事件日历（共识 vs 我方 + gap）</div>
              <table class="fv-table">
                <thead>
                  <tr><th>日期</th><th>事件</th><th>共识</th><th>我方</th><th>gap</th><th>对本类影响</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(e, i) in fv.near_term_calendar" :key="i">
                    <td>{{ e.date }}</td><td>{{ e.event }}</td><td>{{ e.consensus }}</td>
                    <td>{{ e.our_view }}</td>
                    <td><el-tag size="small" :type="gapType(e.gap)" effect="plain">{{ e.gap }}</el-tag></td>
                    <td>{{ e.impact_on_class }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 三情景 -->
            <div v-if="fv.path_scenarios?.length" class="fv-section">
              <div class="fv-section-title">🎯 三情景路径（base/bull/bear · 概率+触发+影响）</div>
              <div class="fv-scenarios">
                <div v-for="(s, i) in fv.path_scenarios" :key="i" class="fv-scenario" :class="`fv-scn-${s.name}`">
                  <div class="fv-scn-head">
                    <span class="fv-scn-name">{{ scenarioLabel(s.name) }}</span>
                    <span class="fv-scn-prob">{{ Math.round((s.prob || 0) * 100) }}%</span>
                  </div>
                  <p><b>触发条件：</b>{{ s.trigger }}</p>
                  <p v-if="s.macro_outcome"><b>宏观结果：</b>{{ s.macro_outcome }}</p>
                  <p><b>对本类影响：</b>{{ s.asset_impact }}</p>
                </div>
              </div>
            </div>

            <!-- 中长期路径 -->
            <p v-if="fv.mid_term_path" class="fv-line"><b>📈 中长期路径：</b>{{ fv.mid_term_path }}</p>

            <!-- 仓位拥挤度 + IV/skew -->
            <div class="fv-grid">
              <p v-if="fv.positioning_view"><b>🪙 仓位拥挤：</b>{{ fv.positioning_view }}</p>
              <p v-if="fv.iv_skew_view"><b>📊 期权恐慌：</b>{{ fv.iv_skew_view }}</p>
              <p v-if="fv.cross_market_leading" class="fv-cross"><b>🌐 跨市场领先：</b>{{ fv.cross_market_leading }}</p>
            </div>

            <!-- 核心假设 + 证伪 -->
            <div v-if="fv.key_assumptions?.length" class="fv-section">
              <div class="fv-section-title">🧬 核心假设 + 证伪信号</div>
              <ul class="fv-list">
                <li v-for="(a, i) in fv.key_assumptions" :key="i">
                  <b>{{ a.assumption }}</b> → <span class="fv-falsify">{{ a.falsification_signal }}</span>
                </li>
              </ul>
            </div>

            <!-- 尾部风险 -->
            <div v-if="fv.tail_risks?.length" class="fv-section fv-tail">
              <div class="fv-section-title">⚠️ 尾部风险（已知未知 + 早期预警 + 对冲动作）</div>
              <table class="fv-table">
                <thead><tr><th>事件</th><th>概率</th><th>早期预警</th><th>影响</th><th>对冲</th></tr></thead>
                <tbody>
                  <tr v-for="(r, i) in fv.tail_risks" :key="i">
                    <td>{{ r.event }}</td>
                    <td>{{ Math.round((r.prob || 0) * 100) }}%</td>
                    <td>{{ r.early_warning }}</td>
                    <td>{{ r.impact }}</td>
                    <td class="fv-hedge">{{ r.hedge_action }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </el-collapse-item>
        </el-collapse>
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

// 前瞻 forward_view 展示
const fv = computed(() => detail.value?.verdict?.forward_view || {})
function gapType(g?: string): 'success' | 'danger' | 'warning' | 'info' {
  if (!g) return 'info'
  if (g.includes('hawkish')) return 'danger'
  if (g.includes('dovish')) return 'success'
  if (g.includes('inline')) return 'warning'
  return 'info'
}
function scenarioLabel(name?: string): string {
  if (!name) return ''
  return ({ base: '基准', bull: '乐观', bear: '悲观' } as Record<string, string>)[name] || name
}

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
/* 前瞻视野 forward_view */
.adt-forward { padding: 0 16px; margin-bottom: 16px; border: 1px solid #ebeef5; border-radius: 8px; background: #fff; }
.adt-forward-title { font-weight: 600; color: #2f4f8f; }
.fv-section { margin-bottom: 14px; }
.fv-section-title { font-weight: 600; color: #303133; margin-bottom: 6px; font-size: 13px; }
.fv-trigger { background: #fef3e6; padding: 10px; border-radius: 6px; border-left: 3px solid #e6a23c; }
.fv-trigger .fv-section-title { color: #c95f1c; }
.fv-list { padding-left: 22px; margin: 0; line-height: 1.8; font-size: 13px; }
.fv-list li { margin: 2px 0; }
.fv-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.fv-table th, .fv-table td { border: 1px solid #ebeef5; padding: 6px 8px; text-align: left; }
.fv-table th { background: #f5f7fa; font-weight: 600; }
.fv-scenarios { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.fv-scenario { padding: 10px; border-radius: 6px; border: 1px solid #ebeef5; font-size: 12px; }
.fv-scn-base { background: #f5f7fa; border-left: 3px solid #909399; }
.fv-scn-bull { background: #e8f5e9; border-left: 3px solid #67c23a; }
.fv-scn-bear { background: #fef0f0; border-left: 3px solid #f56c6c; }
.fv-scn-head { display: flex; justify-content: space-between; font-weight: 600; margin-bottom: 4px; }
.fv-scn-prob { color: #2f4f8f; }
.fv-line { font-size: 13px; line-height: 1.6; margin: 8px 0; }
.fv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px; line-height: 1.6; margin: 8px 0; }
.fv-cross { grid-column: span 2; }
.fv-falsify { color: #c95f1c; font-style: italic; }
.fv-tail .fv-table { background: #fef0f0; }
.fv-hedge { color: #67c23a; font-weight: 500; }

</style>
