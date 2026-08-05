<template>
  <view class="vmk-bottom-nav">
    <view
      v-for="item in tabs"
      :key="item.path"
      class="vmk-nav-item"
      :class="{ active: current === item.key }"
      @tap="onTap(item)"
    >
      <view class="vmk-nav-inner">
        <view class="vmk-nav-icon">
          <VmkIcon :name="item.icon" :size="40" :color="current === item.key ? '#FFFFFF' : '#9CA3AF'" />
        </view>
        <text class="vmk-nav-label">{{ item.label }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import VmkIcon from './VmkIcon.vue'

export default {
  name: 'BottomNav',
  components: { VmkIcon },
  props: {
    current: { type: String, required: true }
  },
  data() {
    return {
      tabs: [
        { key: 'home', label: '首页', icon: 'home', path: '/pages/home/home' },
        { key: 'shorts', label: '短剧', icon: 'play-square', path: '/pages/shorts/shorts' },
        { key: 'library', label: '片库', icon: 'grid-2x2', path: '/pages/library/library' },
        { key: 'profile', label: '我的', icon: 'user', path: '/pages/profile/profile' }
      ]
    }
  },
  methods: {
    onTap(item) {
      if (item.key === this.current) return
      uni.redirectTo({ url: item.path })
    }
  }
}
</script>

<style scoped>
.vmk-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--vmk-bottom-nav);
  background-color: rgba(13, 13, 18, 0.96);
  /* #ifdef H5 */
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  /* #endif */
  border-top: 1px solid var(--vmk-border);
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0 16rpx;
  z-index: 50;
  /* 适配 iPhone 底部安全区 */
  padding-bottom: env(safe-area-inset-bottom);
  padding-bottom: constant(safe-area-inset-bottom);
}

.vmk-nav-item {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.vmk-nav-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rpx;
}

.vmk-nav-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56rpx;
  height: 56rpx;
  border-radius: var(--vmk-radius-full);
  transition: background-color 0.2s ease;
}

.vmk-nav-item.active .vmk-nav-icon {
  background-color: var(--vmk-primary);
}

.vmk-nav-label {
  font-size: var(--vmk-text-xs);
  line-height: 1.2;
  color: var(--vmk-muted);
}

.vmk-nav-item.active .vmk-nav-label {
  color: var(--vmk-foreground);
}
</style>
