<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <text class="header-title">我的</text>
      <view class="icon-btn" @tap="onSetting">
        <VmkIcon name="settings" :size="40" color="#FFFFFF" />
      </view>
    </view>

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <!-- Stats row -->
      <view class="card stats-card">
        <view class="stats-row">
          <view class="stat-item" v-for="(s, i) in profileStats" :key="s.label">
            <text class="stat-num">{{ s.value }}</text>
            <text class="stat-label">{{ s.label }}</text>
          </view>
        </view>
      </view>

      <!-- Settings menu -->
      <view class="card menu-card">
        <view
          v-for="(item, idx) in profileMenu"
          :key="item.id"
          class="menu-item"
          :class="{ 'no-border': idx === profileMenu.length - 1 }"
          @tap="onMenu(item)"
        >
          <view class="menu-icon">
            <VmkIcon :name="item.icon" :size="36" color="#9CA3AF" />
          </view>
          <text class="menu-text">{{ item.text }}</text>
          <view class="menu-right">
            <view v-if="item.badge" class="badge"></view>
            <VmkIcon name="chevron-right" :size="28" color="#9CA3AF" />
          </view>
        </view>
      </view>

      <view class="bottom-spacer"></view>
    </scroll-view>

    <BottomNav current="profile" />
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import BottomNav from '@/components/BottomNav.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchUserStats, fetchUserMenu } from '@/api/index.js'

export default {
  name: 'Profile',
  components: { StatusBar, BottomNav, VmkIcon },
  data() {
    return {
      profileStats: [],
      profileMenu: []
    }
  },
  async onShow() {
    const [stats, menu] = await Promise.all([
      fetchUserStats(),
      fetchUserMenu()
    ])
    this.profileStats = stats
    this.profileMenu = menu
  },
  methods: {
    onSetting() {
      uni.showToast({ title: '设置功能开发中', icon: 'none' })
    },
    onMenu(item) {
      const routeMap = {
        history: '/pages/history/history',
        favorite: '/pages/favorite/favorite',
        cache: '/pages/cache/cache',
        about: '/pages/about/about'
      }
      const route = routeMap[item.id]
      if (route) {
        uni.navigateTo({ url: route })
      } else {
        uni.showToast({ title: item.text, icon: 'none' })
      }
    }
  }
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background-color: var(--vmk-background);
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 112rpx;
  padding: 0 32rpx;
}

.header-title {
  font-size: var(--vmk-text-xl);
  font-weight: 700;
  color: var(--vmk-foreground);
}

.icon-btn {
  width: 80rpx;
  height: 80rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.page-content {
  flex: 1;
  padding: 0 32rpx;
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
  display: flex;
  flex-direction: column;
  gap: 32rpx;
}

.card {
  background-color: var(--vmk-card);
  border-radius: var(--vmk-radius-lg);
  overflow: hidden;
}

/* Stats */
.stats-card {
  padding: 32rpx;
}

.stats-row {
  display: flex;
  align-items: center;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.stat-item:not(:last-child)::after {
  content: '';
  position: absolute;
  right: 0;
  top: 10%;
  bottom: 10%;
  width: 1px;
  background-color: var(--vmk-border);
}

.stat-num {
  font-size: 40rpx;
  font-weight: 700;
  color: var(--vmk-foreground);
  line-height: 1.2;
}

.stat-label {
  margin-top: 8rpx;
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}

/* Menu */
.menu-card {
  /* nothing extra */
}

.menu-item {
  height: 104rpx;
  padding: 0 32rpx;
  display: flex;
  align-items: center;
  gap: 24rpx;
  border-bottom: 1px solid var(--vmk-border);
}

.menu-item.no-border {
  border-bottom: none;
}

.menu-icon {
  width: 40rpx;
  height: 40rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.menu-text {
  flex: 1;
  font-size: var(--vmk-text-base);
  color: var(--vmk-foreground);
}

.menu-right {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.badge {
  width: 16rpx;
  height: 16rpx;
  border-radius: 9999rpx;
  background-color: var(--vmk-error);
}

.bottom-spacer {
  height: 32rpx;
}
</style>
