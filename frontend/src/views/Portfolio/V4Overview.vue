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
      <!-- Tab0 我的持仓 — 组合完整体检（统一完整报告样式，钻取大类/行业/个股进各自完整报告页）-->
      <el-tab-pane label="我的持仓" name="holdings">
        <HoldingsFullReport />
      </el-tab-pane>

      <!-- Tab1 选股池 & 产业链瓶颈（自下而上进攻链产出：alpha 清单/瓶颈深挖/错杀龙头）-->
      <el-tab-pane label="🌿 选股池 / 产业链瓶颈" name="alpha">
        <AlphaScanTab @open-stock="openStock" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import HoldingsFullReport from './v4/HoldingsFullReport.vue'
import AlphaScanTab from './v4/AlphaScanTab.vue'

const router = useRouter()
const activeTab = ref('holdings')

// 选股池里点个股 → 跳个股完整报告页
function openStock(code: string) {
  router.push(`/portfolio/v4/stock/${code}`)
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
