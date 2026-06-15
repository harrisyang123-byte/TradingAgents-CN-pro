<template>
  <div class="v4-overview page-content">
    <div class="v4-banner">
      <div class="v4-banner-title">
        组合总揽 <span class="v4-tag">v4 · 分层独立深度投研</span>
      </div>
      <div class="v4-banner-sub">
        从「我的持仓」看每项持仓的分析结论与处理动作；或自上而下按 七大类 → 行业 → 个股 逐层钻取。
      </div>
    </div>

    <el-tabs v-model="activeTab" class="v4-tabs" type="border-card">
      <!-- Tab0 我的持仓（首页，唯一入口：大类→行业→持仓 全在这一页, 大类首行点"大类分析→"进 Tab2）-->
      <el-tab-pane label="我的持仓" name="holdings">
        <HoldingsReviewTab @open-stock="openStock" @open-asset="openAsset" @open-industry="openIndustry" />
      </el-tab-pane>

      <!-- Tab1 选股池 & 产业链瓶颈（自下而上进攻链产出：alpha 清单/瓶颈深挖/错杀龙头）-->
      <el-tab-pane label="🌿 选股池 / 产业链瓶颈" name="alpha">
        <AlphaScanTab @open-stock="openStock" />
      </el-tab-pane>

      <!-- Tab2 大类详情（动态, 从持仓页大类首行点击进入） -->
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
import AssetDetailTab from './v4/AssetDetailTab.vue'
import IndustryDetailTab from './v4/IndustryDetailTab.vue'
import StockDetailTab from './v4/StockDetailTab.vue'
import HoldingsReviewTab from './v4/HoldingsReviewTab.vue'
import AlphaScanTab from './v4/AlphaScanTab.vue'
import { classLabel } from './v4/assetClasses'
import { useV4Overview } from './v4/useV4Units'

const activeTab = ref('holdings')
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

</style>
