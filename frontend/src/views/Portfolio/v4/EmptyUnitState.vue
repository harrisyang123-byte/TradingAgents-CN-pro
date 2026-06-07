<template>
  <div class="empty-unit-state">
    <div class="eus-icon">{{ icon }}</div>
    <div class="eus-title">{{ title }}</div>
    <div v-if="description" class="eus-desc">{{ description }}</div>
    <div v-if="cliHint" class="eus-cli">
      <div class="eus-cli-label">在 CLI 对话中触发分析：</div>
      <code class="eus-cli-cmd">{{ cliHint }}</code>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    description?: string
    cliHint?: string
    icon?: string
  }>(),
  {
    title: '尚未分析',
    description: '',
    cliHint: '',
    icon: '🗂',
  },
)
</script>

<style scoped>
.empty-unit-state {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
}
.eus-icon {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.7;
}
.eus-title {
  font-size: 15px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 6px;
}
.eus-desc {
  font-size: 13px;
  margin-bottom: 12px;
}
.eus-cli {
  display: inline-block;
  text-align: left;
  background: #f4f4f5;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 10px 14px;
  margin-top: 4px;
}
.eus-cli-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.eus-cli-cmd {
  font-size: 13px;
  color: #409eff;
  word-break: break-all;
}
</style>
