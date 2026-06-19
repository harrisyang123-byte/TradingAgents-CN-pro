<template>
  <el-menu
    :default-active="activeMenu"
    :collapse="appStore.sidebarCollapsed"
    :unique-opened="true"
    router
    class="sidebar-menu"
  >
    <!-- ====== 持仓（顶层直达，不用子菜单包） ====== -->
    <el-menu-item index="/portfolio/holdings">
      <el-icon><Wallet /></el-icon>
      <template #title>持仓明细</template>
    </el-menu-item>
    <el-menu-item index="/portfolio/v4-overview">
      <el-icon><DataAnalysis /></el-icon>
      <template #title>组合总揽 v4</template>
    </el-menu-item>

    <el-sub-menu index="/settings">
      <template #title>
        <el-icon><Setting /></el-icon>
        <span>设置</span>
      </template>
      <el-sub-menu index="/settings-personal">
        <template #title>个人设置</template>
        <el-menu-item index="/settings">通用设置</el-menu-item>
        <el-menu-item index="/settings?tab=appearance">外观设置</el-menu-item>
        <el-menu-item index="/settings?tab=analysis">分析偏好</el-menu-item>
        <el-menu-item index="/settings?tab=notifications">通知设置</el-menu-item>
        <el-menu-item index="/settings?tab=security">安全设置</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="/settings-config">
        <template #title>系统配置</template>
        <el-menu-item index="/settings/config">配置管理</el-menu-item>
        <el-menu-item index="/settings/cache">缓存管理</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="/settings-admin">
        <template #title>系统管理</template>
        <el-menu-item index="/settings/database">数据库管理</el-menu-item>
        <el-menu-item index="/settings/logs">操作日志</el-menu-item>
        <el-menu-item index="/settings/system-logs">系统日志</el-menu-item>
        <el-menu-item index="/settings/sync">多数据源同步</el-menu-item>
        <el-menu-item index="/settings/scheduler">定时任务</el-menu-item>
        <el-menu-item index="/settings/usage">使用统计</el-menu-item>
      </el-sub-menu>
    </el-sub-menu>
  </el-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import {
  Setting,
  Wallet,
  DataAnalysis
} from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()

const activeMenu = computed(() => route.path)
</script>

<style lang="scss" scoped>
.sidebar-menu {
  border: none;
  height: 100%;

  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 48px;
    line-height: 48px;
  }

  :deep(.el-menu-item.is-active) {
    background-color: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
  }
}
</style>
