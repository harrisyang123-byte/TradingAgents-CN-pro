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

      <!-- D0-2 投资地图：产业链瓶颈 → 推荐个股（置顶,一进页面就看"买什么"） -->
      <div v-if="detail.investment_map?.length" class="card idt-invmap idt-invmap-prime">
        <div class="idt-section-title">🎯 投资地图：瓶颈环节 → 买哪只（卡位排序）</div>
        <p v-if="detail.verdict?.investment_conclusion" class="idt-inv-concl">
          <b>结论：</b>{{ detail.verdict.investment_conclusion }}
        </p>
        <table class="idt-inv-table">
          <thead>
            <tr><th>排序</th><th>瓶颈环节</th><th>推荐个股</th><th>最新评级</th><th>目标价</th><th>为什么是它</th><th>详情</th></tr>
          </thead>
          <tbody>
            <tr v-for="(m, i) in sortedInvMap" :key="i">
              <td><span class="idt-rank">#{{ m.rank }}</span></td>
              <td>{{ m.chokepoint }}</td>
              <td><b>{{ m.recommended }}</b></td>
              <td>
                <el-tag size="small" :type="m.rating && /增持|买入/.test(m.rating) ? 'success' : (m.rating && /减|卖出/.test(m.rating) ? 'danger' : 'info')" effect="plain">{{ m.rating }}</el-tag>
                <el-tooltip v-if="m.rating_source === 'stock_unit_latest'" content="已同步最新个股单元" placement="top">
                  <el-icon class="idt-sync-ico"><Refresh /></el-icon>
                </el-tooltip>
              </td>
              <td><b v-if="m.target_price_live != null" class="idt-target">¥{{ m.target_price_live }}</b><span v-else class="idt-pending">-</span></td>
              <td class="idt-inv-why">{{ m.why }}</td>
              <td>
                <el-button v-if="m.analyzed && extractCode(m.recommended)" link type="primary" size="small"
                  @click="$emit('open-stock', extractCode(m.recommended))">查看 →</el-button>
                <span v-else class="idt-pending">待分析</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 基金不穿透(用户拍板): 基金作为整体标的展示 — 主题基金归对应行业作推荐标的、宽基/债基归大类底仓, 不再拆解穿透到本行业 -->

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

      <!-- 产业链瓶颈地图 Chokepoint Map（折叠收起 - 支撑分析） -->
      <div v-if="detail.chokepoint_map?.length" class="card idt-chokepoint">
        <el-collapse>
          <el-collapse-item name="cp">
            <template #title>
              <span class="idt-section-title">
                🔗 产业链瓶颈地图（Chokepoint 四维 + 五力支撑分析）
                <span v-if="detail.top_chokepoints?.length" class="idt-cp-top-inline">最窄咽喉：{{ detail.top_chokepoints.join('；') }}</span>
              </span>
            </template>
            <div class="idt-cp-table">
              <div class="idt-cp-row idt-cp-thead">
                <span class="idt-cp-c-node">环节 / 层级</span>
                <span>不可替代</span>
                <span>供给集中</span>
                <span>产能刚性</span>
                <span>价值卡位</span>
                <span class="idt-cp-c-wide">替代路径风险</span>
                <span class="idt-cp-c-wide">可投标的（A股 / QDII）</span>
              </div>
              <div
                v-for="(cp, i) in detail.chokepoint_map"
                :key="i"
                class="idt-cp-row"
                :class="{ 'idt-cp-istop': cp.is_top }"
              >
                <span class="idt-cp-c-node">
                  <b>{{ cp.node }}</b><em>{{ cp.layer }}</em>
                  <el-tag v-if="cp.is_top" type="danger" size="small" effect="dark">TOP</el-tag>
                </span>
                <span :class="dimCls(cp.irreplaceability)">{{ cp.irreplaceability }}</span>
                <span :class="dimCls(cp.supply_concentration)">{{ cp.supply_concentration }}</span>
                <span :class="dimCls(cp.capacity_rigidity)">{{ cp.capacity_rigidity }}</span>
                <span :class="dimCls(cp.value_capture)">{{ cp.value_capture }}</span>
                <span class="idt-cp-c-wide idt-cp-sub">{{ cp.substitution_risk }}</span>
                <span class="idt-cp-c-wide idt-cp-plays">
                  <span v-if="(cp.beneficiaries_a || []).length" class="idt-cp-a">A股：{{ (cp.beneficiaries_a || []).join('、') }}</span>
                  <span v-if="(cp.beneficiaries_qdii || []).length" class="idt-cp-q">QDII：{{ (cp.beneficiaries_qdii || []).join('、') }}</span>
                </span>
              </div>
            </div>
            <div v-if="detail.verdict?.chokepoint_conclusion" class="idt-cp-concl">
              <b>瓶颈落地结论：</b>{{ detail.verdict.chokepoint_conclusion }}
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 辩论历程（折叠 - 支撑分析） -->
      <div v-if="detail.debate_rounds?.length" class="card idt-debate">
        <el-collapse>
          <el-collapse-item :title="`行业深辩历程（${detail.debate_rounds.length} 轮 - 多空攻防过程）`" name="debate">
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
    </template>

    <EmptyUnitState v-else title="无数据" />
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import UnitStatusBadge from './UnitStatusBadge.vue'
import EmptyUnitState from './EmptyUnitState.vue'
import StockTable from './StockTable.vue'
import { useIndustryDetail } from './useV4Units'

const props = defineProps<{ industry: string }>()
defineEmits<{ (e: 'open-stock', code: string): void }>()

const { detail, loading, load } = useIndustryDetail()

// D0-2 投资地图: 按 rank 排序 + 从"300502 新易盛"提取代码
const sortedInvMap = computed(() =>
  [...(detail.value?.investment_map || [])].sort((a: any, b: any) => (a.rank || 99) - (b.rank || 99)),
)
function extractCode(rec?: string): string {
  if (!rec) return ''
  const m = rec.match(/(\d{5,6}|[0-9]{5})/)
  return m ? m[1] : ''
}

const stanceLabel = computed(
  () => ({ bullish: '看多', bearish: '看空', neutral: '中性', go: '看好(Go)', nogo: '回避' }[detail.value?.verdict?.stance || ''] || detail.value?.verdict?.stance),
)
const stanceType = computed(
  () => ({ bullish: 'success', bearish: 'danger', neutral: 'info', go: 'success', nogo: 'danger' }[detail.value?.verdict?.stance || ''] || 'info') as 'success' | 'danger' | 'info',
)

// 四维强弱着色：含"高/极高/强"=红(强瓶颈), "中"=橙, 其余灰
function dimCls(v?: string): string {
  if (!v) return 'idt-cp-dim'
  if (/极高|高|强/.test(v)) return 'idt-cp-dim idt-cp-strong'
  if (/中/.test(v)) return 'idt-cp-dim idt-cp-mid'
  return 'idt-cp-dim'
}

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
/* Chokepoint 瓶颈地图 */
.idt-chokepoint { padding: 16px; margin-bottom: 16px; border: 1px solid #ebeef5; border-radius: 8px; background: #fff; }
.idt-cp-head { font-size: 15px; font-weight: 700; color: #303133; margin-bottom: 12px; }
.idt-cp-top { display: block; font-size: 12px; font-weight: 400; color: #f56c6c; margin-top: 4px; }
.idt-cp-table { font-size: 12px; }
.idt-cp-row { display: grid; grid-template-columns: 1.4fr 0.7fr 0.8fr 0.7fr 0.7fr 2fr 2fr; gap: 8px; padding: 8px 6px; border-bottom: 1px solid #f0f2f5; align-items: start; }
.idt-cp-thead { font-weight: 700; color: #909399; background: #fafafa; border-bottom: 2px solid #ebeef5; }
.idt-cp-istop { background: #fef6f6; }
.idt-cp-c-node { display: flex; flex-direction: column; gap: 2px; }
.idt-cp-c-node b { color: #303133; font-size: 13px; }
.idt-cp-c-node em { color: #909399; font-style: normal; font-size: 11px; }
.idt-cp-dim { font-weight: 600; }
.idt-cp-strong { color: #f56c6c; }
.idt-cp-mid { color: #e6a23c; }
.idt-cp-sub { color: #606266; line-height: 1.4; }
.idt-cp-plays { display: flex; flex-direction: column; gap: 3px; line-height: 1.4; }
.idt-cp-a { color: #409eff; }
.idt-cp-q { color: #909399; }
.idt-cp-concl { margin-top: 12px; padding: 10px; background: #ecf5ff; border-radius: 6px; font-size: 13px; color: #606266; line-height: 1.6; }
/* D0-2 投资地图 */
.idt-invmap { border: 1px solid #ebeef5; border-radius: 8px; background: #fff; padding: 16px; margin-bottom: 14px; }
.idt-section-title { font-weight: 600; color: #2f4f8f; margin-bottom: 8px; font-size: 14px; }
.idt-inv-concl { font-size: 13px; background: #f0f9eb; padding: 8px; border-radius: 4px; margin-bottom: 10px; color: #5a6a4f; }
.idt-inv-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.idt-inv-table th, .idt-inv-table td { border: 1px solid #ebeef5; padding: 6px 8px; text-align: left; vertical-align: top; }
.idt-inv-table th { background: #f5f7fa; font-weight: 600; }
.idt-rank { display: inline-block; background: #2f4f8f; color: #fff; border-radius: 10px; padding: 1px 7px; font-size: 11px; }
.idt-inv-why { color: #606266; max-width: 280px; }
.idt-pending { color: #c0c4cc; font-size: 12px; }

/* 投资地图置顶强调样式（"买什么"先于"为什么"） */
.idt-invmap-prime { border-left: 4px solid #2f4f8f; box-shadow: 0 2px 6px rgba(47, 79, 143, 0.08); }
.idt-target { color: #2f4f8f; font-size: 14px; }
.idt-sync-ico { color: #67c23a; font-size: 12px; margin-left: 4px; vertical-align: middle; }
.idt-cp-top-inline { font-size: 12px; color: #c45656; font-weight: normal; margin-left: 8px; }

/* D0-6 基金间接持仓卡 */
.idt-indirect { border-left: 4px solid #faad14; box-shadow: 0 2px 6px rgba(250, 173, 20, 0.08); }
.idt-cov-tag { margin-left: 8px; font-weight: normal; }
.idt-indirect-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 10px 0 14px 0; }
.idt-indirect-cell { padding: 10px 12px; background: #fafafa; border-radius: 6px; display: flex; flex-direction: column; align-items: center; }
.idt-indirect-cell.idt-cell-emphasize { background: #fff7e6; border: 1px solid #ffd591; }
.idt-cell-label { font-size: 12px; color: #909399; margin-bottom: 6px; }
.idt-cell-val { font-size: 17px; color: #303133; font-weight: 700; }
.idt-cell-emphasize .idt-cell-val { color: #d46b08; }
.idt-fund-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.idt-fund-table th { background: #fafafa; padding: 8px 10px; text-align: left; border-bottom: 1px solid #ebeef5; font-weight: 600; color: #909399; font-size: 12px; }
.idt-fund-table td { padding: 8px 10px; border-bottom: 1px solid #f5f7fa; }
.idt-empty { color: #c0c4cc; font-style: italic; padding: 8px; }

</style>
