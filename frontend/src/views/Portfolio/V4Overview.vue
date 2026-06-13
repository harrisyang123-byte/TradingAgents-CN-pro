<template>
  <div class="v4-overview page-content">
    <div class="v4-banner">
      <div class="v4-banner-title">
        组合总揽 <span class="v4-tag">v4 · 分层独立深度投研</span>
      </div>
      <div class="v4-banner-sub">
        七大类资产 → 大类内行业 → 行业内个股，逐层独立分析、独立缓存。
        分析在 CLI 触发（重计算不经 Web），此处只读展示状态与结论。
      </div>
    </div>

    <!-- D0-6 基金穿透体检卡 (2026-06-13) -->
    <div v-if="overview?.fund_passthrough" class="v4-fund-card">
      <div class="v4-fund-head">
        🪙 基金穿透体检
        <span class="v4-fund-cov">穿透覆盖 {{ overview.fund_passthrough.summary?.passthrough_coverage_pct ?? 0 }}%</span>
        <span class="v4-fund-mv">权益总暴露 ¥{{ fmtMoney(overview.fund_passthrough.style_factors?.total_fund_mv ?? 0) }}</span>
      </div>
      <div class="v4-fund-grid">
        <!-- 重叠主题告警 -->
        <div v-if="overview.fund_passthrough.overlap_analysis?.theme_overlaps?.length" class="v4-fund-block">
          <div class="v4-fund-block-title">⚠️ 同主题重复暴露 ({{ overview.fund_passthrough.overlap_analysis.theme_overlaps.length }} 个,合计 ¥{{ fmtMoney(overview.fund_passthrough.overlap_analysis.summary.theme_overlap_total_mv) }})</div>
          <ul class="v4-fund-list">
            <li v-for="(t, i) in overview.fund_passthrough.overlap_analysis.theme_overlaps.slice(0, 5)" :key="i">
              <b>{{ t.theme }}</b> {{ t.fund_count }} 只 ¥{{ fmtMoney(t.total_mv) }}
              <span class="v4-fund-advice">{{ t.advice.replace(/^⚠️\s*/, '') }}</span>
            </li>
          </ul>
        </div>

        <!-- 间接持仓 top 10 -->
        <div v-if="overview.fund_passthrough.indirect_concentration_top10?.length" class="v4-fund-block">
          <div class="v4-fund-block-title">📊 间接持仓 top 10 (基金穿透到底层股票)</div>
          <table class="v4-fund-table">
            <tr v-for="(s, i) in overview.fund_passthrough.indirect_concentration_top10" :key="i">
              <td><b>{{ s.code }}</b></td>
              <td>{{ s.name }}</td>
              <td>¥{{ fmtMoney(s.total_indirect_value) }}</td>
              <td>经 {{ s.fund_count }} 只</td>
            </tr>
          </table>
        </div>

        <!-- 风格因子 -->
        <div v-if="overview.fund_passthrough.style_factors" class="v4-fund-block">
          <div class="v4-fund-block-title">📈 风格因子 (基于 _fund_passthrough.style)</div>
          <div class="v4-fund-style-row">
            <span><b>规模:</b> {{ formatDist(overview.fund_passthrough.style_factors.size) }}</span>
          </div>
          <div class="v4-fund-style-row">
            <span><b>成长价值:</b> {{ formatDist(overview.fund_passthrough.style_factors.growth_value) }}</span>
          </div>
          <div class="v4-fund-style-row">
            <span><b>地区:</b> {{ formatDist(overview.fund_passthrough.style_factors.region) }}</span>
          </div>
          <div class="v4-fund-style-row">
            <span><b>类型:</b> {{ formatDist(overview.fund_passthrough.style_factors.fund_type) }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="v4-tabs" type="border-card">
      <!-- Tab1 资产配置 -->
      <el-tab-pane label="资产配置" name="allocation">
        <AssetAllocationTab ref="allocTabRef" @open-asset="openAsset" />
      </el-tab-pane>

      <!-- Tab2 大类详情（动态） -->
      <el-tab-pane :disabled="!currentAsset" name="asset">
        <template #label>
          <span>{{ currentAsset ? `大类：${currentAssetLabel}` : '大类详情' }}</span>
        </template>
        <div v-if="!currentAsset" class="v4-hint">请在「资产配置」中点击某大类卡片进入详情。</div>
        <AssetDetailTab
          v-else
          :asset-class="currentAsset"
          :equity-quota="equityQuota"
          @open-industry="openIndustry"
        />
      </el-tab-pane>

      <!-- Tab3 行业/个股（动态） -->
      <el-tab-pane :disabled="!currentIndustry" name="industry">
        <template #label>
          <span>{{ currentIndustry ? `行业：${currentIndustry}` : '行业 / 个股' }}</span>
        </template>
        <div v-if="!currentIndustry" class="v4-hint">请在权益大类详情中点击某行业进入。</div>
        <IndustryDetailTab v-else :industry="currentIndustry" @open-stock="openStock" />
      </el-tab-pane>

      <!-- Tab4 个股详情（动态，D0-3） -->
      <el-tab-pane :disabled="!currentStock" name="stock">
        <template #label>
          <span>{{ currentStock ? `个股：${currentStock}` : '个股详情' }}</span>
        </template>
        <div v-if="!currentStock" class="v4-hint">请在行业详情的「投资地图」中点击某个股「查看 →」进入。</div>
        <StockDetailTab v-else :code="currentStock" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AssetAllocationTab from './v4/AssetAllocationTab.vue'
import AssetDetailTab from './v4/AssetDetailTab.vue'
import IndustryDetailTab from './v4/IndustryDetailTab.vue'
import StockDetailTab from './v4/StockDetailTab.vue'
import { classLabel } from './v4/assetClasses'
import { useV4Overview } from './v4/useV4Units'

const activeTab = ref('allocation')
const currentAsset = ref<string>('')
const currentAssetLabel = ref<string>('')
const currentIndustry = ref<string>('')
const currentStock = ref<string>('')

// 用于把 equity_quota 透传给 Tab2 行业表格
const { overview, load: loadOverview } = useV4Overview()
loadOverview()
const equityQuota = ref<number | null>(null)

function openAsset(assetClass: string) {
  currentAsset.value = assetClass
  currentAssetLabel.value = classLabel(assetClass)
  currentIndustry.value = '' // 切换大类时清空行业
  equityQuota.value = overview.value?.equity_quota ?? null
  activeTab.value = 'asset'
}

function openIndustry(name: string) {
  currentIndustry.value = name
  activeTab.value = 'industry'
}
function openStock(code: string) {
  currentStock.value = code
  activeTab.value = 'stock'
}

// D0-6 基金穿透 utils
function fmtMoney(v?: number): string {
  if (v == null) return '0'
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(2) + '万'
  return v.toFixed(0)
}
function formatDist(d?: Record<string, number>): string {
  if (!d) return '-'
  const total = Object.values(d).reduce((a, b) => a + b, 0)
  if (total <= 0) return '-'
  return Object.entries(d)
    .map(([k, v]) => `${k} ${(v / total * 100).toFixed(1)}%`)
    .join(' / ')
}
</script>

<style scoped>
.v4-banner {
  margin-bottom: 16px;
}
.v4-banner-title {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 10px;
}
.v4-tag {
  font-size: 12px;
  font-weight: 500;
  color: #409eff;
  background: #ecf5ff;
  padding: 2px 10px;
  border-radius: 10px;
}
.v4-banner-sub {
  font-size: 13px;
  color: #909399;
  margin-top: 6px;
  line-height: 1.5;
}
.v4-tabs {
  border-radius: 8px;
}
.v4-hint {
  text-align: center;
  padding: 40px;
  color: #909399;
  font-size: 14px;
}

/* D0-6 基金穿透体检卡 */
.v4-fund-card {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  border-left: 4px solid #faad14;
  box-shadow: 0 2px 6px rgba(250, 173, 20, 0.08);
  padding: 16px;
  margin-bottom: 16px;
}
.v4-fund-head {
  font-size: 16px;
  font-weight: 700;
  color: #d46b08;
  margin-bottom: 12px;
}
.v4-fund-cov {
  background: #f6ffed;
  color: #67c23a;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
  margin-left: 10px;
}
.v4-fund-mv {
  background: #fff7e6;
  color: #d46b08;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
  margin-left: 8px;
}
.v4-fund-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(330px, 1fr));
  gap: 14px;
}
.v4-fund-block {
  background: #fafafa;
  padding: 12px;
  border-radius: 6px;
}
.v4-fund-block-title {
  font-weight: 600;
  color: #303133;
  font-size: 13.5px;
  margin-bottom: 8px;
}
.v4-fund-list {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 12.5px;
  line-height: 1.8;
}
.v4-fund-list li {
  padding: 4px 0;
  border-bottom: 1px dashed #ebeef5;
  color: #4e5969;
}
.v4-fund-list b {
  color: #303133;
  margin-right: 6px;
}
.v4-fund-advice {
  display: block;
  color: #c45656;
  font-size: 11.5px;
  margin-top: 2px;
}
.v4-fund-table {
  width: 100%;
  font-size: 12.5px;
}
.v4-fund-table td {
  padding: 4px 6px;
  border-bottom: 1px dashed #f0f0f0;
}
.v4-fund-style-row {
  font-size: 12.5px;
  line-height: 1.8;
  color: #4e5969;
}
.v4-fund-style-row b {
  color: #303133;
  margin-right: 6px;
}
</style>
