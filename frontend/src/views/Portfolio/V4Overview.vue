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
        <IndustryDetailTab v-else :industry="currentIndustry" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AssetAllocationTab from './v4/AssetAllocationTab.vue'
import AssetDetailTab from './v4/AssetDetailTab.vue'
import IndustryDetailTab from './v4/IndustryDetailTab.vue'
import { classLabel } from './v4/assetClasses'
import { useV4Overview } from './v4/useV4Units'

const activeTab = ref('allocation')
const currentAsset = ref<string>('')
const currentAssetLabel = ref<string>('')
const currentIndustry = ref<string>('')

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
