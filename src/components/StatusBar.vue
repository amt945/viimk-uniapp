<template>
  <view class="vmk-status-wrap">
    <!-- APP/MP 端：真实状态栏高度占位（H5 为 0） -->
    <view class="vmk-status-safe"></view>
  </view>
</template>

<script>
export default {
  name: 'StatusBar'
}
</script>

<style scoped>
.vmk-status-wrap {
  width: 100%;
  background-color: transparent;
}

/* 原生平台 (APP/小程序) 状态栏高度占位，H5 下为 0 */
.vmk-status-safe {
  height: var(--status-bar-height, 0px);
}
</style>
