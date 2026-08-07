<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <view class="icon-btn" @tap="goBack">
        <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
      </view>
      <text class="header-title">我的收藏</text>
      <view class="icon-btn" @tap="toggleEdit">
        <text class="edit-text">{{ editing ? '完成' : '编辑' }}</text>
      </view>
    </view>

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <view v-if="list.length" class="grid">
        <view
          v-for="item in list"
          :key="item.id"
          class="thumb-card"
          @tap="!editing && goDetail(item)"
        >
          <view class="thumb-img">
            <image class="thumb-img-inner" :src="item.cover" mode="aspectFill" />
            <view v-if="editing" class="unfav-mask" @tap.stop="removeItem(item.id)">
              <view class="unfav-circle">
                <VmkIcon name="heart" :size="40" color="#EF4444" />
              </view>
            </view>
          </view>
          <text class="thumb-title ellipsis">{{ item.title }}</text>
          <text class="thumb-meta ellipsis">{{ item.meta }}</text>
        </view>
      </view>

      <view v-else class="empty">
        <view class="empty-icon">
          <VmkIcon name="heart" :size="80" color="#2A2A35" />
        </view>
        <text class="empty-text">还没有收藏内容</text>
      </view>

      <view class="bottom-spacer"></view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchFavoriteList, removeFavorite, navigateToPlayer } from '@/api/index.js'

export default {
  name: 'Favorite',
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
      this.list = await fetchFavoriteList()
    },
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/profile/profile' })
    },
    goDetail(item) {
      if (!item) return
      navigateToPlayer(item)
    },
    toggleEdit() {
      this.editing = !this.editing
    },
    async removeItem(id) {
      await removeFavorite(id)
      this.list = this.list.filter(i => i.id !== id)
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
  padding: 24rpx 32rpx;
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
}

.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}

.thumb-card {
  width: calc((100% - 48rpx) / 3);
  display: flex;
  flex-direction: column;
}

.thumb-img {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: var(--vmk-radius-md);
  overflow: hidden;
  background-color: var(--vmk-card);
}

.thumb-img-inner {
  width: 100%;
  height: 100%;
}

.unfav-mask {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.unfav-circle {
  width: 80rpx;
  height: 80rpx;
  border-radius: 9999rpx;
  background-color: rgba(239, 68, 68, 0.9);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.thumb-title {
  margin-top: 16rpx;
  font-size: 26rpx;
  font-weight: 600;
  line-height: 1.3;
  color: var(--vmk-foreground);
}

.thumb-meta {
  margin-top: 8rpx;
  font-size: var(--vmk-text-xs);
  line-height: 1.4;
  color: var(--vmk-muted);
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
