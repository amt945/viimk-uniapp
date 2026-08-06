<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <view class="icon-btn" @tap="goBack">
        <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
      </view>
      <text class="header-title">历史记录</text>
      <view class="icon-btn" @tap="toggleEdit">
        <text class="edit-text">{{ editing ? '完成' : '编辑' }}</text>
      </view>
    </view>

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <view v-if="list.length" class="history-list">
        <!-- 清空全部（编辑模式下显示） -->
        <view v-if="editing" class="clear-all" @tap="clearAll">
          <text class="clear-all-text">清空全部记录</text>
        </view>
        <view
          v-for="item in list"
          :key="item.id"
          class="history-card"
          @tap="!editing && goDetail(item)"
        >
          <view class="poster">
            <image class="poster-img" :src="item.cover" mode="aspectFill" />
            <view class="poster-mask"></view>
            <view class="play-badge">
              <VmkIcon name="play" :size="24" color="#FFFFFF" />
            </view>
          </view>
          <view class="info">
            <view class="info-top">
              <text class="title ellipsis">{{ item.title }}</text>
              <text class="episode" v-if="item.episode">看到第 {{ item.episode }} 集</text>
              <text class="episode" v-else-if="item.remarks">{{ item.remarks }}</text>
            </view>
            <view class="progress-wrap" v-if="item.progress">
              <view class="progress">
                <view class="progress-fill" :style="{ width: item.progress + '%' }"></view>
              </view>
              <text class="progress-text">{{ item.progress }}%</text>
            </view>
            <text class="time">{{ item.time }}</text>
          </view>
          <view v-if="editing" class="del-btn" @tap.stop="removeItem(item.id)">
            <VmkIcon name="trash-2" :size="36" color="#EF4444" />
          </view>
        </view>
      </view>

      <view v-else class="empty">
        <view class="empty-icon">
          <VmkIcon name="history" :size="80" color="#2A2A35" />
        </view>
        <text class="empty-text">暂无观看记录</text>
      </view>

      <view class="bottom-spacer"></view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchHistoryList, deleteHistoryItem, clearHistory, navigateToPlayer } from '@/api/index.js'

export default {
  name: 'History',
  components: { StatusBar, VmkIcon },
  data() {
    return {
      list: [],
      editing: false
    }
  },
  async onShow() {
    await this.loadList()
  },
  methods: {
    async loadList() {
      this.list = await fetchHistoryList()
    },
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/profile/profile' })
    },
    async goDetail(item) {
      if (!item) return
      try {
        uni.showLoading({ title: '加载中…', mask: true })
        await navigateToPlayer(item)
      } finally {
        uni.hideLoading()
      }
    },
    toggleEdit() {
      this.editing = !this.editing
    },
    async removeItem(id) {
      await deleteHistoryItem(id)
      this.list = this.list.filter(i => i.id !== id)
    },
    async clearAll() {
      uni.showModal({
        title: '提示',
        content: '确定清空所有历史记录吗？',
        success: async (res) => {
          if (res.confirm) {
            await clearHistory()
            this.list = []
            uni.showToast({ title: '已清空', icon: 'none' })
          }
        }
      })
    }
  }
}
</script>

<style scoped>
.app-shell {
  height: 100vh;
  background-color: var(--vmk-background);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 24rpx;
  flex-shrink: 0;
}

.header-title {
  font-size: var(--vmk-text-lg);
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

.edit-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-primary);
}

.page-content {
  flex: 1 1 auto;
  height: 0;
  min-height: 0;
  padding: 16rpx 32rpx;
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.clear-all {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 72rpx;
  border-radius: var(--vmk-radius-md);
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.clear-all-text {
  font-size: var(--vmk-text-sm);
  color: #EF4444;
}

.history-card {
  display: flex;
  gap: 24rpx;
  background-color: var(--vmk-card);
  border-radius: var(--vmk-radius-lg);
  padding: 24rpx;
  align-items: center;
}

.poster {
  position: relative;
  width: 160rpx;
  aspect-ratio: 3 / 4;
  border-radius: var(--vmk-radius-md);
  overflow: hidden;
  background-color: var(--vmk-muted-bg);
  flex-shrink: 0;
}

.poster-img {
  width: 100%;
  height: 100%;
}

.poster-mask {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.25);
}

.play-badge {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 56rpx;
  height: 56rpx;
  border-radius: 9999rpx;
  background-color: rgba(43, 127, 255, 0.9);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.info-top {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.title {
  font-size: var(--vmk-text-lg);
  font-weight: 700;
  color: var(--vmk-foreground);
}

.episode {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
}

.progress-wrap {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.progress {
  flex: 1;
  height: 6rpx;
  border-radius: 9999rpx;
  background-color: var(--vmk-muted-bg);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 9999rpx;
  background-color: var(--vmk-primary);
}

.progress-text {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
  white-space: nowrap;
}

.time {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
}

.del-btn {
  width: 64rpx;
  height: 64rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.empty {
  padding: 200rpx 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24rpx;
}

.empty-icon {
  width: 120rpx;
  height: 120rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.empty-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}

.bottom-spacer {
  height: 32rpx;
}
</style>
