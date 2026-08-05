<template>
  <view class="app-shell">
    <StatusBar />

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <!-- Header -->
      <view class="header">
        <view class="icon-btn" @tap="goBack">
          <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
        </view>
        <text class="brand">详情</text>
        <view class="icon-btn" @tap="onShare">
          <VmkIcon name="share-2" :size="36" color="#FFFFFF" />
        </view>
      </view>

      <!-- Loading -->
      <view v-if="loading" class="loading-wrap">
        <view class="spinner"></view>
        <text class="loading-text">加载中…</text>
      </view>

      <!-- Error -->
      <view v-else-if="errMsg" class="error-wrap">
        <text class="error-text">{{ errMsg }}</text>
        <view class="retry-btn" @tap="loadDetail"><text class="retry-text">重试</text></view>
      </view>

      <!-- Content -->
      <template v-else-if="detail">
        <!-- Hero -->
        <view class="hero">
          <image class="hero-img" :src="detail.cover || poster" mode="aspectFill" />
          <view class="hero-mask"></view>
          <view class="hero-info">
            <text class="hero-title">{{ detail.title }}</text>
            <view class="hero-meta">
              <text class="hero-meta-text" v-if="detail.year">{{ detail.year }}</text>
              <view v-if="detail.year && detail.area" class="dot"></view>
              <text class="hero-meta-text" v-if="detail.area">{{ detail.area }}</text>
              <view v-if="detail.area && detail.remarks" class="dot"></view>
              <text class="hero-meta-text" v-if="detail.remarks">{{ detail.remarks }}</text>
            </view>
          </view>
        </view>

        <!-- Title row -->
        <view class="title-row">
          <text class="title-text ellipsis">{{ detail.title }}</text>
          <view class="title-actions">
            <view v-if="detail.score" class="score-badge">
              <text class="score-badge-text">{{ detail.score }}</text>
            </view>
            <view class="icon-btn" @tap="toggleFav">
              <VmkIcon name="heart" :size="36" :color="isFav ? '#EF4444' : '#FFFFFF'" />
            </view>
          </view>
        </view>

        <!-- Meta info -->
        <view v-if="detail.actor || detail.director" class="meta-section">
          <text v-if="detail.director" class="meta-line">导演：{{ detail.director }}</text>
          <text v-if="detail.actor" class="meta-line">主演：{{ detail.actor }}</text>
        </view>

        <!-- Play CTA + Cache -->
        <view class="action-row">
          <view class="play-cta" @tap="goPlayer">
            <VmkIcon name="play" :size="36" color="#FFFFFF" />
            <text class="play-cta-text">立即播放</text>
          </view>
          <view class="cache-cta" @tap="onCache">
            <VmkIcon name="download" :size="36" color="#FFFFFF" />
            <text class="cache-cta-text">缓存</text>
          </view>
        </view>

        <!-- Synopsis -->
        <view v-if="detail.content" class="section">
          <text class="section-title">剧情简介</text>
          <text class="synopsis" :class="{ expanded: synopsisExpanded }">{{ detail.content }}</text>
          <text class="synopsis-toggle" @tap="synopsisExpanded = !synopsisExpanded">
            {{ synopsisExpanded ? '收起' : '展开' }}
          </text>
        </view>

        <!-- Episodes -->
        <view v-if="episodes.length" class="section">
          <view class="episodes-head">
            <text class="section-title">选集</text>
            <text class="episodes-count">共 {{ episodes.length }} 集</text>
          </view>
          <view class="episode-grid">
            <view
              v-for="(ep, i) in episodes"
              :key="i"
              class="episode-card"
              :class="{ active: activeEpisode === i }"
              @tap="playEpisode(i)"
            >
              <text class="episode-num">{{ ep.name }}</text>
            </view>
          </view>
        </view>

        <!-- Lines (播放线路) -->
        <view v-if="lines.length > 1" class="section">
          <text class="section-title">播放线路</text>
          <view class="line-list">
            <view
              v-for="(line, i) in lines"
              :key="i"
              class="line-chip"
              :class="{ active: activeLine === i }"
              @tap="switchLine(i)"
            >
              <text class="line-chip-text">{{ line.flag || ('线路' + (i + 1)) }}</text>
            </view>
          </view>
        </view>
      </template>

      <view class="bottom-spacer"></view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchOnlineDetail, toggleFavorite, updateHistory, addOfflineItem, isFavorited } from '@/api/index.js'

export default {
  name: 'Detail',
  components: { StatusBar, VmkIcon },
  data() {
    return {
      vodId: '',
      siteKey: '',
      contentType: '',
      poster: '',
      detail: null,
      lines: [],
      episodes: [],
      activeLine: 0,
      activeEpisode: 0,
      isFav: false,
      synopsisExpanded: false,
      loading: true,
      errMsg: ''
    }
  },
  async onLoad(options) {
    const q = options || {}
    this.vodId = q.vodId || q.vod_id || q.id || ''
    this.siteKey = q.site || q.online_site || ''
    this.contentType = q.contentType || ''
    if (q.title) {
      try { this._initTitle = decodeURIComponent(q.title) } catch (e) { this._initTitle = q.title }
    }
    if (q.poster) {
      try { this.poster = decodeURIComponent(q.poster) } catch (e) { this.poster = q.poster }
    }
    await this.loadDetail()
  },
  methods: {
    async loadDetail() {
      if (!this.vodId) {
        this.errMsg = '缺少视频 ID'
        this.loading = false
        return
      }
      this.loading = true
      this.errMsg = ''
      try {
        const d = await fetchOnlineDetail(this.vodId, this.siteKey)
        if (!d) {
          this.errMsg = '加载详情失败，请重试'
          return
        }
        this.detail = d
        this.lines = (d.lines && d.lines.length) ? d.lines : []
        if (this.lines.length) {
          this.activeLine = 0
          this.episodes = this.lines[0].eps || []
        } else {
          this.episodes = []
        }
        this.isFav = isFavorited(this.vodId, this.siteKey)
        uni.setNavigationBarTitle({ title: d.title || this._initTitle || '详情' })
      } catch (e) {
        this.errMsg = '加载详情失败'
      } finally {
        this.loading = false
      }
    },
    switchLine(i) {
      if (i === this.activeLine) return
      this.activeLine = i
      this.episodes = this.lines[i].eps || []
      this.activeEpisode = 0
    },
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/home/home' })
    },
    async goPlayer() {
      // 记录到历史记录
      if (this.detail) {
        updateHistory({
          id: this.vodId,
          title: this.detail.title,
          cover: this.detail.cover || this.poster,
          episode: this.activeEpisode + 1,
          remarks: this.detail.remarks || '',
          progress: 0
        })
      }
      const params = [
        'vodId=' + encodeURIComponent(this.vodId),
        'site=' + encodeURIComponent(this.siteKey),
        'title=' + encodeURIComponent(this.detail ? this.detail.title : ''),
        'epIdx=' + this.activeEpisode
      ]
      if (this.detail && this.detail.cover) params.push('poster=' + encodeURIComponent(this.detail.cover))
      else if (this.poster) params.push('poster=' + encodeURIComponent(this.poster))
      if (this.contentType) params.push('contentType=' + encodeURIComponent(this.contentType))
      uni.navigateTo({ url: '/pages/player/player?' + params.join('&') })
    },
    playEpisode(i) {
      this.activeEpisode = i
      this.goPlayer()
    },
    async onCache() {
      if (!this.detail) return
      await addOfflineItem({
        id: this.vodId,
        title: this.detail.title,
        cover: this.detail.cover || this.poster,
        meta: this.detail.remarks || '',
        size: '约 280MB',
        contentType: this.contentType
      })
      uni.showToast({ title: '已加入缓存队列', icon: 'success' })
    },
    async toggleFav() {
      await toggleFavorite({
        vodId: this.vodId,
        onlineSite: this.siteKey || 'ffzy',
        title: this.detail ? this.detail.title : '',
        cover: this.detail ? this.detail.cover : this.poster,
        meta: this.detail ? this.detail.remarks : ''
      })
      this.isFav = !this.isFav
      uni.showToast({ title: this.isFav ? '已收藏' : '已取消收藏', icon: 'none' })
    },
    onShare() {
      uni.showToast({ title: '分享功能开发中', icon: 'none' })
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
.page-content {
  flex: 1 1 auto;
  height: 0;
  min-height: 0;
  padding: 0 32rpx;
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  margin-bottom: 24rpx;
}
.brand {
  font-size: var(--vmk-text-base);
  font-weight: 700;
  letter-spacing: 2rpx;
  color: var(--vmk-foreground);
}
.icon-btn {
  width: 80rpx;
  height: 80rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--vmk-radius-full);
  background-color: var(--vmk-card);
  border: 1px solid var(--vmk-border);
}
/* Hero */
.hero {
  position: relative;
  width: 100%;
  height: 360rpx;
  border-radius: var(--vmk-radius-lg);
  overflow: hidden;
  margin-bottom: 24rpx;
}
.hero-img {
  width: 100%;
  height: 100%;
}
.hero-mask {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,0.6) 100%);
}
.hero-info {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 32rpx;
}
.hero-title {
  font-size: 40rpx;
  font-weight: 700;
  line-height: 1.2;
  color: #FFFFFF;
  margin-bottom: 12rpx;
}
.hero-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12rpx;
}
.hero-meta-text {
  font-size: var(--vmk-text-xs);
  color: rgba(255,255,255,0.8);
}
.dot {
  width: 6rpx;
  height: 6rpx;
  border-radius: 9999rpx;
  background-color: rgba(255,255,255,0.5);
}
/* Title row */
.title-row {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 16rpx;
}
.title-text {
  flex: 1;
  min-width: 0;
  font-size: var(--vmk-text-xl);
  font-weight: 700;
  color: var(--vmk-foreground);
}
.title-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-shrink: 0;
}
.score-badge {
  height: 44rpx;
  padding: 0 16rpx;
  background-color: var(--vmk-warning);
  border-radius: var(--vmk-radius-sm);
  display: inline-flex;
  align-items: center;
}
.score-badge-text {
  font-size: var(--vmk-text-xs);
  font-weight: 700;
  color: var(--vmk-background);
}
/* Meta section */
.meta-section {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  margin-bottom: 24rpx;
}
.meta-line {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
  line-height: 1.5;
}
/* Action row: play + cache */
.action-row {
  display: flex;
  gap: 16rpx;
  margin-bottom: 32rpx;
}
.play-cta {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  height: 88rpx;
  border-radius: var(--vmk-radius-xl);
  background-color: var(--vmk-primary);
}
.play-cta-text {
  font-size: var(--vmk-text-base);
  font-weight: 600;
  color: #FFFFFF;
}
.cache-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  width: 160rpx;
  height: 88rpx;
  border-radius: var(--vmk-radius-xl);
  background-color: var(--vmk-muted-bg);
  border: 1px solid var(--vmk-border);
}
.cache-cta-text {
  font-size: var(--vmk-text-base);
  font-weight: 600;
  color: var(--vmk-foreground);
}
/* Section */
.section {
  margin-bottom: 32rpx;
}
.section-title {
  display: block;
  font-size: var(--vmk-text-lg);
  font-weight: 700;
  color: var(--vmk-foreground);
  margin-bottom: 16rpx;
}
.synopsis {
  font-size: var(--vmk-text-sm);
  line-height: 1.6;
  color: var(--vmk-muted);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  overflow: hidden;
}
.synopsis.expanded {
  -webkit-line-clamp: 99;
}
.synopsis-toggle {
  display: inline-block;
  margin-top: 12rpx;
  font-size: var(--vmk-text-sm);
  color: var(--vmk-primary);
}
/* Episodes */
.episodes-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 24rpx;
}
.episodes-head .section-title {
  margin-bottom: 0;
}
.episodes-count {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
}
.episode-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}
.episode-card {
  position: relative;
  min-width: calc((100% - 96rpx) / 5);
  height: 80rpx;
  padding: 0 16rpx;
  border-radius: var(--vmk-radius-md);
  background-color: var(--vmk-muted-bg);
  border: 1px solid var(--vmk-border);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.episode-card.active {
  background-color: var(--vmk-primary);
  border-color: var(--vmk-primary);
}
.episode-num {
  font-size: var(--vmk-text-sm);
  font-weight: 600;
  color: var(--vmk-foreground);
}
.episode-card.active .episode-num {
  color: #FFFFFF;
}
/* Lines */
.line-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.line-chip {
  height: 56rpx;
  padding: 0 28rpx;
  border-radius: var(--vmk-radius-full);
  background-color: var(--vmk-muted-bg);
  border: 1px solid var(--vmk-border);
  display: inline-flex;
  align-items: center;
}
.line-chip.active {
  background-color: var(--vmk-primary);
  border-color: var(--vmk-primary);
}
.line-chip-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-foreground);
}
.line-chip.active .line-chip-text {
  color: #FFFFFF;
}
/* Loading / Error */
.loading-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 200rpx 0;
  gap: 24rpx;
}
.spinner {
  width: 64rpx;
  height: 64rpx;
  border: 6rpx solid rgba(255,255,255,0.1);
  border-top-color: var(--vmk-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}
.error-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 200rpx 0;
  gap: 24rpx;
}
.error-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}
.retry-btn {
  height: 72rpx;
  padding: 0 48rpx;
  border-radius: 36rpx;
  background-color: var(--vmk-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.retry-text {
  font-size: 26rpx;
  color: #FFFFFF;
  font-weight: 600;
}
.bottom-spacer {
  height: 32rpx;
}
</style>
