<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <view class="icon-btn" @tap="goBack">
        <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
      </view>
      <text class="header-title">离线缓存</text>
      <view class="icon-btn" @tap="toggleEdit">
        <text class="edit-text">{{ editing ? '完成' : '编辑' }}</text>
      </view>
    </view>

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <view v-if="list.length" class="cache-list">
        <!-- 清空全部（编辑模式下显示） -->
        <view v-if="editing" class="clear-all" @tap="clearAll">
          <text class="clear-all-text">清空全部缓存</text>
        </view>
        <view
          v-for="item in list"
          :key="item.id"
          class="cache-card"
          @tap="!editing && goDetail(item)"
        >
          <view class="poster">
            <image class="poster-img" :src="item.cover" mode="aspectFill" />
            <view class="poster-mask"></view>
            <!-- 下载中/已完成 badge -->
            <view v-if="item.status === 'downloading'" class="status-badge downloading">
              <text class="status-text">下载中 {{ item.progress }}%</text>
            </view>
            <view v-else class="status-badge done">
              <text class="status-text">已缓存</text>
            </view>
          </view>
          <view class="info">
            <view class="info-top">
              <text class="title ellipsis">{{ item.title }}</text>
              <text class="meta-text" v-if="item.meta">{{ item.meta }}</text>
            </view>
            <!-- 下载进度条 -->
            <view v-if="item.status === 'downloading'" class="progress-wrap">
              <view class="progress">
                <view class="progress-fill" :style="{ width: item.progress + '%' }"></view>
              </view>
              <text class="progress-text">{{ item.progress }}%</text>
            </view>
            <text class="size-text">{{ item.size }} · {{ item.time }}</text>
          </view>
          <view v-if="editing" class="del-btn" @tap.stop="removeItem(item.id)">
            <VmkIcon name="trash-2" :size="36" color="#EF4444" />
          </view>
        </view>
      </view>

      <view v-else class="empty">
        <view class="empty-icon">
          <VmkIcon name="download" :size="80" color="#2A2A35" />
        </view>
        <text class="empty-text">暂无离线缓存</text>
        <text class="empty-hint">在详情页点击缓存按钮即可离线观看</text>
      </view>

      <view class="bottom-spacer"></view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchOfflineList, removeOfflineItem, updateOfflineProgress } from '@/api/index.js'

export default {
  name: 'Cache',
  components: { StatusBar, VmkIcon },
  data() {
    return {
      list: [],
      editing: false
    }
  },
  async onShow() {
    await this.loadList()
    this.simulateDownload()
  },
  methods: {
    async loadList() {
      this.list = await fetchOfflineList()
    },
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/profile/profile' })
    },
    toggleEdit() {
      this.editing = !this.editing
    },
    async removeItem(id) {
      await removeOfflineItem(id)
      this.list = this.list.filter(i => i.id !== id)
    },
    async clearAll() {
      uni.showModal({
        title: '提示',
        content: '确定清空所有离线缓存吗？',
        success: async (res) => {
          if (res.confirm) {
            for (const item of [...this.list]) {
              await removeOfflineItem(item.id)
            }
            this.list = []
            uni.showToast({ title: '已清空', icon: 'none' })
          }
        }
      })
    },
    goDetail(item) {
      if (!item) return
      // 已缓存的视频点击后跳转播放页
      if (item.status !== 'done') {
        uni.showToast({ title: '缓存尚未完成', icon: 'none' })
        return
      }
      const params = [
        'vodId=' + encodeURIComponent(item.id),
        'title=' + encodeURIComponent(item.title || '')
      ]
      if (item.cover) params.push('poster=' + encodeURIComponent(item.cover))
      if (item.contentType) params.push('contentType=' + encodeURIComponent(item.contentType))
      uni.navigateTo({ url: '/pages/player/player?' + params.join('&') })
    },
    // 模拟下载进度（H5 环境无法真正下载视频文件）
    simulateDownload() {
      const downloading = this.list.filter(i => i.status === 'downloading')
      if (!downloading.length) return
      this._downloadTimer = setInterval(async () => {
        let needUpdate = false
        for (const item of this.list) {
          if (item.status === 'downloading') {
            item.progress = Math.min(100, (item.progress || 0) + Math.floor(Math.random() * 15 + 5))
            if (item.progress >= 100) {
              item.status = 'done'
            }
            await updateOfflineProgress(item.id, item.progress, item.status)
            needUpdate = true
          }
        }
        if (needUpdate) {
          // 强制更新视图
          this.list = [...this.list]
          // 全部下载完成则停止定时器
          if (!this.list.some(i => i.status === 'downloading')) {
            clearInterval(this._downloadTimer)
            uni.showToast({ title: '缓存完成', icon: 'success' })
          }
        }
      }, 2000)
    }
  },
  onUnload() {
    if (this._downloadTimer) clearInterval(this._downloadTimer)
  },
  onHide() {
    if (this._downloadTimer) clearInterval(this._downloadTimer)
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

.cache-list {
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

.cache-card {
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

.status-badge {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 6rpx 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-badge.downloading {
  background-color: rgba(43, 127, 255, 0.9);
}

.status-badge.done {
  background-color: rgba(34, 197, 94, 0.9);
}

.status-text {
  font-size: 20rpx;
  color: #FFFFFF;
  font-weight: 600;
}

.info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12rpx;
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

.meta-text {
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

.size-text {
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
  gap: 16rpx;
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

.empty-hint {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
  opacity: 0.6;
}

.bottom-spacer {
  height: 32rpx;
}
</style>
