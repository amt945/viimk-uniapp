<template>
  <view class="player-page" :class="{ 'shorts-mode': isShorts, 'movie-mode': !isShorts }" @tap="onPageTap">
    <!-- 视频背景 -->
    <view class="video-bg">
      <!-- 统一使用 H5 video slot（App 端 WebView 也支持） -->
      <view id="vmk-video-slot" class="video-el" :class="{ 'video-el-shorts': isShorts }"></view>

      <!-- 加载中 -->
      <view v-if="loading" class="overlay loading-overlay" @tap.stop>
        <view class="spinner"></view>
        <text class="overlay-text">{{ loadingText }}</text>
      </view>

      <!-- 错误 -->
      <view v-if="errMsg" class="overlay error-overlay" @tap.stop>
        <text class="overlay-text error-text">{{ errMsg }}</text>
        <view class="retry-btn" @tap.stop="retry">
          <text class="retry-text">重试</text>
        </view>
      </view>

      <!-- H5 点击播放 / 取消静音 -->
      <!-- #ifdef H5 -->
      <view v-if="needTapPlay && !errMsg" class="overlay tap-play-overlay" @tap.stop="tapToPlay">
        <view class="tap-play-icon">
          <VmkIcon name="play" :size="64" color="#FFFFFF" />
        </view>
        <text class="overlay-text">点击播放</text>
      </view>
      <!-- #endif -->

      <!-- H5 自定义进度条（App 端用原生 video controls） -->
      <!-- #ifdef H5 -->
      <view
        v-if="showTopBar && !loading && !errMsg"
        class="player-progress"
        :class="{ 'shorts-progress': isShorts }"
        @tap.stop
      >
        <text class="progress-time">{{ currentTimeStr }}</text>
        <view
          class="progress-track"
          ref="progressTrack"
          @tap="onSeekProgress"
          @touchstart="onSeekStart"
          @touchmove.prevent="onSeekMove"
          @touchend="onSeekEnd"
        >
          <view class="progress-buffered" :style="{ width: bufferedPercent + '%' }"></view>
          <view class="progress-played" :style="{ width: playedPercent + '%' }"></view>
          <view class="progress-thumb" :style="{ left: playedPercent + '%' }"></view>
        </view>
        <text class="progress-time">{{ durationStr }}</text>
      </view>
      <!-- #endif -->
    </view>

    <!-- ========== 短剧布局（竖屏/短视频风格） ========== -->
    <template v-if="isShorts">
      <!-- 顶部控制栏 -->
      <view v-if="showTopBar" class="shorts-top-bar" :style="{ paddingTop: statusBarHeight + 'px' }" @tap.stop>
        <view class="shorts-top-btn" @tap="goBack">
          <VmkIcon name="chevron-left" :size="44" color="#FFFFFF" />
        </view>
        <view class="shorts-top-info">
          <text class="shorts-top-title ellipsis">{{ headerTitle }}</text>
          <text class="shorts-top-sub" v-if="detail && detail.remarks">{{ detail.remarks }}</text>
        </view>
        <view class="shorts-top-btn" @tap="openMoreMenu">
          <VmkIcon name="more-vertical" :size="40" color="#FFFFFF" />
        </view>
      </view>

      <!-- 右侧操作栏 -->
      <view class="shorts-side-bar" v-if="!showPanel && !showSpeedMenu && !showMoreMenu">
        <view class="shorts-side-item" @tap="toggleFavorite">
          <view class="shorts-side-icon-wrap" :class="{ active: isFavorited }">
            <VmkIcon :name="isFavorited ? 'star-filled' : 'star'" :size="40" :color="isFavorited ? '#FFB800' : '#FFFFFF'" />
          </view>
          <text class="shorts-side-label">{{ isFavorited ? '已收藏' : '收藏' }}</text>
        </view>
        <view class="shorts-side-item" @tap="togglePlay">
          <view class="shorts-side-icon-wrap">
            <VmkIcon :name="isPlaying ? 'pause' : 'play'" :size="40" color="#FFFFFF" />
          </view>
          <text class="shorts-side-label">{{ isPlaying ? '暂停' : '播放' }}</text>
        </view>
        <view class="shorts-side-item" @tap="openSpeedMenu">
          <view class="shorts-side-icon-wrap">
            <text class="shorts-speed-text">{{ currentSpeed }}x</text>
          </view>
          <text class="shorts-side-label">倍速</text>
        </view>
        <view class="shorts-side-item" @tap="toggleFullscreen">
          <view class="shorts-side-icon-wrap">
            <VmkIcon name="fullscreen" :size="40" color="#FFFFFF" />
          </view>
          <text class="shorts-side-label">全屏</text>
        </view>
      </view>

      <!-- 底部选集栏 -->
      <view v-if="!showPanel" class="shorts-bottom-bar" @tap.stop="togglePanel">
        <view class="shorts-ep-scroll">
          <view class="shorts-ep-info">
            <text class="shorts-ep-title">选集</text>
            <text class="shorts-ep-divider">·</text>
            <text class="shorts-ep-status">{{ detail && detail.remarks ? detail.remarks : '已完结' }}</text>
            <text class="shorts-ep-divider">·</text>
            <text class="shorts-ep-count">全{{ episodes.length || '?' }}集</text>
          </view>
          <scroll-view class="shorts-ep-strip" scroll-x :show-scrollbar="false" v-if="episodes.length">
            <view class="shorts-ep-list">
              <view
                v-for="(ep, i) in episodes"
                :key="i"
                class="shorts-ep-chip"
                :class="{ active: currentEpIdx === i }"
                @tap.stop="selectEpisode(i)"
              >
                <text class="shorts-ep-chip-name">{{ ep.name }}</text>
              </view>
            </view>
          </scroll-view>
          <view class="shorts-ep-expand" @tap.stop="togglePanel">
            <text class="shorts-ep-expand-text">展开</text>
            <VmkIcon name="chevron-up" :size="28" color="#FFFFFF" />
          </view>
        </view>
      </view>

      <!-- 底部弹出面板 -->
      <view v-if="showPanel" class="panel-mask" @tap="togglePanel">
        <view class="panel" @tap.stop>
          <view class="panel-handle"></view>

          <view class="work-info">
            <image class="work-cover" :src="detail ? detail.cover : poster" mode="aspectFill" />
            <view class="work-meta">
              <view class="work-title-row">
                <text class="work-title ellipsis">{{ detail ? detail.title : playTitle }}</text>
              </view>
              <text class="work-subtitle ellipsis">{{ workSubtitle }}</text>
              <text v-if="detail && detail.content" class="work-desc ellipsis-2">{{ detail.content }}</text>
            </view>
          </view>

          <view class="panel-tabs">
            <view
              v-for="t in panelTabs"
              :key="t.key"
              class="panel-tab"
              :class="{ active: panelTab === t.key }"
              @tap="panelTab = t.key"
            >
              <text class="panel-tab-text">{{ t.label }}</text>
            </view>
          </view>

          <scroll-view v-if="panelTab === 'episodes'" class="panel-content" scroll-y>
            <view class="ep-grid">
              <view
                v-for="(ep, i) in episodes"
                :key="i"
                class="ep-item"
                :class="{ active: currentEpIdx === i }"
                @tap="selectEpisode(i)"
              >
                <text class="ep-name">{{ ep.name }}</text>
              </view>
            </view>
            <view class="panel-bottom-spacer"></view>
          </scroll-view>

          <scroll-view v-else-if="panelTab === 'intro'" class="panel-content" scroll-y>
            <text class="intro-text">{{ introText }}</text>
            <view class="panel-bottom-spacer"></view>
          </scroll-view>

          <scroll-view v-else class="panel-content" scroll-y>
            <view class="series-list">
              <view
                v-for="(s, i) in seriesList"
                :key="i"
                class="series-item"
                @tap="goSeries(s)"
              >
                <image class="series-cover" :src="s.cover" mode="aspectFill" />
                <text class="series-title ellipsis">{{ s.title }}</text>
              </view>
            </view>
            <view class="panel-bottom-spacer"></view>
          </scroll-view>

          <view class="favorite-btn" @tap="toggleFavorite">
            <VmkIcon :name="isFavorited ? 'star-filled' : 'star'" :size="32" color="#FFB800" />
            <text class="favorite-text">{{ isFavorited ? '已收藏' : '收藏' }}</text>
          </view>
        </view>
      </view>
    </template>

    <!-- ========== 电影/电视剧布局（16:9 视频 + 下方选集） ========== -->
    <template v-else>
      <!-- 视频区顶部控制栏（叠加在 16:9 视频上） -->
      <view v-if="showTopBar" class="movie-top-bar" :style="{ paddingTop: statusBarHeight + 'px' }" @tap.stop>
        <view class="top-btn" @tap="goBack">
          <VmkIcon name="chevron-left" :size="48" color="#FFFFFF" />
        </view>
        <view class="top-title-wrap">
          <text class="top-title ellipsis">{{ headerTitle }}</text>
        </view>
        <view class="top-actions">
          <view class="top-btn" @tap="openSpeedMenu">
            <text class="speed-btn-text">{{ currentSpeed }}x</text>
          </view>
          <view class="top-btn" @tap="toggleFullscreen">
            <VmkIcon name="expand" :size="36" color="#FFFFFF" />
          </view>
          <view class="top-btn" @tap="openMoreMenu">
            <VmkIcon name="more" :size="40" color="#FFFFFF" />
          </view>
        </view>
      </view>

      <!-- 中央播放按钮 -->
      <view v-if="showCenterControl" class="center-control movie-center-control" @tap.stop>
        <view class="center-play-btn" @tap="togglePlay">
          <VmkIcon :name="isPlaying ? 'pause' : 'play'" :size="80" color="#FFFFFF" />
        </view>
      </view>

      <!-- 选集/信息区（视频下方，可滚动） -->
      <scroll-view class="movie-content" scroll-y :show-scrollbar="false" @tap.stop="showTopBar = false">
        <!-- 标题行 -->
        <view class="movie-title-row" v-if="detail">
          <text class="movie-title ellipsis">{{ detail.title }}</text>
          <view class="movie-title-actions">
            <view v-if="detail.score" class="movie-score">
              <text class="movie-score-text">{{ detail.score }}</text>
            </view>
            <view class="movie-fav-btn" @tap="toggleFavorite">
              <VmkIcon :name="isFavorited ? 'star-filled' : 'star'" :size="36" :color="isFavorited ? '#FFB800' : '#FFFFFF'" />
            </view>
          </view>
        </view>

        <!-- 元信息 -->
        <view class="movie-meta" v-if="detail">
          <text class="movie-meta-text" v-if="detail.year">{{ detail.year }}</text>
          <text class="movie-meta-dot" v-if="detail.year && detail.area">·</text>
          <text class="movie-meta-text" v-if="detail.area">{{ detail.area }}</text>
          <text class="movie-meta-dot" v-if="detail.remarks">·</text>
          <text class="movie-meta-text" v-if="detail.remarks">{{ detail.remarks }}</text>
          <text class="movie-meta-dot" v-if="episodes.length">·</text>
          <text class="movie-meta-text" v-if="episodes.length">全{{ episodes.length }}集</text>
        </view>

        <!-- 演职信息 -->
        <view class="movie-credits" v-if="detail && (detail.actor || detail.director)">
          <text class="movie-credit-line" v-if="detail.director">导演：{{ detail.director }}</text>
          <text class="movie-credit-line" v-if="detail.actor">主演：{{ detail.actor }}</text>
        </view>

        <!-- 简介 -->
        <view class="movie-synopsis-section" v-if="detail && detail.content">
          <text class="movie-section-title">简介</text>
          <text class="movie-synopsis" :class="{ expanded: synopsisExpanded }">{{ detail.content }}</text>
          <text class="movie-synopsis-toggle" @tap="synopsisExpanded = !synopsisExpanded">
            {{ synopsisExpanded ? '收起' : '展开' }}
          </text>
        </view>

        <!-- 选集 -->
        <view class="movie-episodes-section" v-if="episodes.length">
          <view class="movie-episodes-head">
            <text class="movie-section-title">选集</text>
            <text class="movie-episodes-count">共 {{ episodes.length }} 集</text>
          </view>
          <view class="movie-ep-grid">
            <view
              v-for="(ep, i) in episodes"
              :key="i"
              class="movie-ep-item"
              :class="{ active: currentEpIdx === i }"
              @tap="selectEpisode(i)"
            >
              <text class="movie-ep-name">{{ ep.name }}</text>
            </view>
          </view>
        </view>

        <!-- 播放线路 -->
        <view class="movie-lines-section" v-if="detail && detail.lines && detail.lines.length > 1">
          <text class="movie-section-title">播放线路</text>
          <view class="movie-line-list">
            <view
              v-for="(line, i) in detail.lines"
              :key="i"
              class="movie-line-chip"
              :class="{ active: lineIdx === i }"
              @tap="switchLine(i)"
            >
              <text class="movie-line-chip-text">{{ line.flag || ('线路' + (i + 1)) }}</text>
            </view>
          </view>
        </view>

        <view class="movie-bottom-spacer"></view>
      </scroll-view>
    </template>

    <!-- 倍速选择弹窗 -->
    <view v-if="showSpeedMenu" class="modal-mask" @tap="showSpeedMenu = false">
      <view class="modal-list" @tap.stop>
        <view
          v-for="s in speedOptions"
          :key="s"
          class="modal-item"
          :class="{ active: currentSpeed === s }"
          @tap="selectSpeed(s)"
        >
          <text class="modal-item-text">{{ s }}x</text>
          <view v-if="currentSpeed === s" class="modal-check">✓</view>
        </view>
      </view>
    </view>

    <!-- 更多操作弹窗 -->
    <view v-if="showMoreMenu" class="modal-mask" @tap="showMoreMenu = false">
      <view class="modal-list" @tap.stop>
        <view class="modal-item" @tap="copyLink">
          <text class="modal-item-text">复制链接</text>
        </view>
        <view class="modal-item" @tap="shareVideo">
          <text class="modal-item-text">分享</text>
        </view>
        <view class="modal-item" @tap="toggleFavorite">
          <text class="modal-item-text">{{ isFavorited ? '取消收藏' : '收藏' }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchOnlineDetail, fetchOnlineResolve, toggleFavorite, isFavorited } from '@/api/index.js'

const IS_H5 = true  // App 端也是 WebView，统一使用 H5 播放方案

export default {
  name: 'Player',
  components: { VmkIcon },
  data() {
    return {
      playTitle: '正在播放',
      poster: '',
      loading: false,
      loadingText: '加载中…',
      errMsg: '',
      statusBarHeight: 20,
      vodId: '',
      siteKey: '',
      rawUrl: '',
      isDirect: false,
      contentType: '',
      detail: null,
      episodes: [],
      currentEpIdx: 0,
      lineIdx: 0,
      _hls: null,
      _h5Video: null,
      _resolved: false,
      mutedAuto: true,
      needTapPlay: false,
      isPlaying: false,
      showTopBar: true,
      showCenterControl: false,
      showPanel: false,
      showSpeedMenu: false,
      showMoreMenu: false,
      currentSpeed: 1.0,
      speedOptions: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
      panelTab: 'episodes',
      panelTabs: [
        { key: 'intro', label: '简介' },
        { key: 'episodes', label: '选集' },
        { key: 'series', label: '系列剧' }
      ],
      isFavorited: false,
      seriesList: [],
      synopsisExpanded: false,
      // 进度条状态（H5 自定义控制）
      currentTime: 0,
      duration: 0,
      buffered: 0,
      _seeking: false
    }
  },
  computed: {
    isShorts() {
      return this.contentType === 'shorts'
    },
    currentLine() {
      if (!this.detail || !this.detail.lines || !this.detail.lines.length) return null
      return this.detail.lines[this.lineIdx] || this.detail.lines[0]
    },
    headerTitle() {
      const ep = this.episodes[this.currentEpIdx]
      if (!this.detail) return this.playTitle
      const epName = ep ? ep.name : ''
      return epName || this.playTitle
    },
    workSubtitle() {
      if (!this.detail) return ''
      const parts = []
      if (this.detail.year) parts.push(this.detail.year)
      if (this.detail.area) parts.push(this.detail.area)
      const count = this.episodes.length
      if (count) parts.push('全' + count + '集')
      return parts.join(' · ')
    },
    introText() {
      if (!this.detail) return '暂无简介'
      return this.detail.content || '暂无简介'
    },
    // 进度条百分比
    playedPercent() {
      if (!this.duration) return 0
      return Math.min(100, Math.max(0, (this.currentTime / this.duration) * 100))
    },
    bufferedPercent() {
      if (!this.duration) return 0
      return Math.min(100, Math.max(0, (this.buffered / this.duration) * 100))
    },
    currentTimeStr() {
      return this._formatTime(this.currentTime)
    },
    durationStr() {
      return this._formatTime(this.duration)
    }
  },
  mounted() {
    if (IS_H5) {
      this.$nextTick(() => this._createH5Video())
    }
  },
  updated() {
    if (IS_H5) this._ensureH5Video()
  },
  async onLoad(options) {
    const q = options || {}
    this.contentType = q.contentType || ''
    this.vodId = q.vodId || q.vod_id || q.id || ''
    this.siteKey = q.site || q.online_site || ''
    const initEp = parseInt(q.epIdx || q.ep || '0', 10)
    this.currentEpIdx = isNaN(initEp) ? 0 : initEp
    if (q.url) {
      try { this.rawUrl = decodeURIComponent(q.url) } catch (e) { this.rawUrl = q.url }
    }
    if (q.title) {
      try { this.playTitle = decodeURIComponent(q.title) } catch (e) { this.playTitle = q.title }
    }
    if (q.poster) {
      try { this.poster = decodeURIComponent(q.poster) } catch (e) { this.poster = q.poster }
    }
    this._initSafeArea()

    if (this.vodId) {
      await this.loadDetail()
      await this.$nextTick()
      await this.playEpisode(this.currentEpIdx)
      this.loadRecommend()
      return
    }
    if (this.rawUrl) {
      this.isDirect = this._isDirectUrl(this.rawUrl)
      this.startPlayUrl(this.rawUrl)
    }
  },
  onUnload() {
    this.destroyHls()
  },
  onHide() {
    this.destroyHls()
  },
  methods: {
    _isDirectUrl(url) {
      if (!url) return false
      return /\.(m3u8|mp4|flv|ts|mov|mkv|avi|webm)(\?|#|$)/i.test(url)
    },
    _initSafeArea() {
      if (IS_H5) {
        this.statusBarHeight = 20
        return
      }
      try {
        const info = uni.getSystemInfoSync()
        this.statusBarHeight = (info.statusBarHeight || 20)
      } catch (e) {}
    },
    onPageTap() {
      this.showTopBar = !this.showTopBar
    },
    togglePanel() {
      this.showPanel = !this.showPanel
      if (this.showPanel) this.showTopBar = false
      else this.showTopBar = true
    },
    openSpeedMenu() {
      this.showSpeedMenu = true
      this.showMoreMenu = false
    },
    openMoreMenu() {
      this.showMoreMenu = true
      this.showSpeedMenu = false
    },
    selectSpeed(s) {
      this.currentSpeed = s
      this.showSpeedMenu = false
      if (this._h5Video) {
        this._h5Video.playbackRate = s
      }
    },
    togglePlay() {
      const v = this._h5Video
      if (!v) return
      if (v.paused) {
        v.play().catch(() => {})
      } else {
        v.pause()
      }
    },
    // 进度条：格式化时间 00:00
    _formatTime(s) {
      if (!s || isNaN(s) || s < 0) return '00:00'
      const total = Math.floor(s)
      const m = Math.floor(total / 60)
      const sec = total % 60
      const mm = m >= 60 ? Math.floor(m / 60) : 0
      const rest = m % 60
      const pad = (n) => String(n).padStart(2, '0')
      if (mm > 0) return pad(mm) + ':' + pad(rest) + ':' + pad(sec)
      return pad(m) + ':' + pad(sec)
    },
    // 进度条：从触摸/点击事件计算 seek 位置
    _updateSeekFromEvent(e) {
      const v = this._h5Video
      if (!v || !this.duration) return
      const trackEl = this.$refs.progressTrack
      if (!trackEl) return
      // H5 端 ref 是 DOM 元素
      const el = trackEl.$el || trackEl
      const rect = el.getBoundingClientRect()
      let x = 0
      const touch = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
      if (touch && typeof touch.clientX === 'number') {
        x = touch.clientX
      } else if (e.detail && typeof e.detail.x === 'number') {
        x = e.detail.x
      }
      const ratio = Math.max(0, Math.min(1, (x - rect.left) / rect.width))
      v.currentTime = ratio * this.duration
      this.currentTime = v.currentTime
    },
    onSeekProgress(e) {
      if (this._seeking) return
      this._updateSeekFromEvent(e)
    },
    onSeekStart(e) {
      this._seeking = true
      this._updateSeekFromEvent(e)
    },
    onSeekMove(e) {
      if (this._seeking) this._updateSeekFromEvent(e)
    },
    onSeekEnd(e) {
      if (this._seeking) {
        this._updateSeekFromEvent(e)
        this._seeking = false
      }
    },
    toggleFullscreen() {
      if (this._h5Video && this._h5Video.requestFullscreen) {
        this._h5Video.requestFullscreen().catch(() => {})
      } else if (this._h5Video && this._h5Video.webkitRequestFullscreen) {
        this._h5Video.webkitRequestFullscreen()
      }
    },
    async toggleFavorite() {
      if (!this.vodId) {
        uni.showToast({ title: '暂无可收藏内容', icon: 'none' })
        return
      }
      const res = await toggleFavorite({
        vodId: this.vodId,
        onlineSite: this.siteKey || 'ffzy',
        title: this.detail ? this.detail.title : this.playTitle,
        cover: this.detail ? this.detail.cover : this.poster,
        meta: this.detail ? this.detail.remarks : ''
      })
      this.isFavorited = !!(res && res.favorited)
      uni.showToast({ title: this.isFavorited ? '已收藏' : '已取消收藏', icon: 'none' })
    },
    copyLink() {
      const url = window.location.href
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
          uni.showToast({ title: '链接已复制', icon: 'none' })
        })
      }
      this.showMoreMenu = false
    },
    shareVideo() {
      uni.showToast({ title: '分享功能开发中', icon: 'none' })
      this.showMoreMenu = false
    },
    goSeries(s) {
      if (!s) return
      const params = [
        'vodId=' + encodeURIComponent(s.vodId || s.id || ''),
        'site=' + encodeURIComponent(s.onlineSite || 'ffzy'),
        'title=' + encodeURIComponent(s.title || '')
      ]
      if (s.cover) params.push('poster=' + encodeURIComponent(s.cover))
      if (this.contentType) params.push('contentType=' + encodeURIComponent(this.contentType))
      uni.redirectTo({ url: '/pages/player/player?' + params.join('&') })
    },
    _createH5Video() {
      if (this._h5Video) return this._h5Video
      const video = document.createElement('video')
      video.id = 'vmk-h5-video'
      video.controls = false
      video.autoplay = true
      video.muted = true
      video.setAttribute('playsinline', '')
      video.setAttribute('webkit-playsinline', '')
      const fit = this.isShorts ? 'cover' : 'contain'
      video.style.cssText = 'width:100%;height:100%;object-fit:' + fit + ';background:#000;'
      if (this.poster) video.poster = this.poster
      video.addEventListener('click', () => {
        if (video.muted) {
          video.muted = false
          this.mutedAuto = false
          video.play().catch(() => {})
        } else {
          this.showCenterControl = true
          setTimeout(() => { this.showCenterControl = false }, 800)
          this.isPlaying = !video.paused
        }
      })
      video.addEventListener('play', () => { this.isPlaying = true })
      video.addEventListener('pause', () => { this.isPlaying = false })
      video.addEventListener('ratechange', () => {})
      // 进度条：监听时间/时长/缓冲
      video.addEventListener('timeupdate', () => {
        if (!this._seeking) this.currentTime = video.currentTime || 0
      })
      video.addEventListener('loadedmetadata', () => {
        this.duration = video.duration || 0
      })
      video.addEventListener('durationchange', () => {
        this.duration = video.duration || 0
      })
      video.addEventListener('progress', () => {
        try {
          if (video.buffered && video.buffered.length > 0) {
            this.buffered = video.buffered.end(video.buffered.length - 1) || 0
          }
        } catch (e) {}
      })
      const slot = document.getElementById('vmk-video-slot')
      if (slot) slot.appendChild(video)
      this._h5Video = video
      return video
    },
    _ensureH5Video() {
      if (!this._h5Video) return
      if (!this._h5Video.parentNode) {
        const slot = document.getElementById('vmk-video-slot')
        if (slot) slot.appendChild(this._h5Video)
      }
    },
    async loadDetail() {
      this.loading = true
      this.loadingText = '加载详情…'
      try {
        const d = await fetchOnlineDetail(this.vodId, this.siteKey)
        if (d) {
          this.detail = d
          this.playTitle = d.title || this.playTitle
          this.poster = d.cover || this.poster
          const line = this.currentLine
          this.episodes = (line && line.eps) || []
          this.isFavorited = isFavorited(this.vodId, this.siteKey)
        } else {
          this.errMsg = '加载详情失败'
        }
      } catch (e) {
        this.errMsg = '加载详情失败'
      } finally {
        this.loading = false
      }
    },
    async loadRecommend() {
      if (this.detail && this.detail.lines && this.detail.lines.length) {
        this.seriesList = this.detail.lines.map((l, i) => ({
          vodId: this.vodId,
          title: this.detail.title,
          cover: this.detail.cover,
          onlineSite: this.siteKey,
          lineIndex: i,
          flag: l.flag
        }))
      }
    },
    switchLine(i) {
      if (i === this.lineIdx || !this.detail || !this.detail.lines) return
      this.lineIdx = i
      const line = this.detail.lines[i]
      this.episodes = (line && line.eps) || []
      this.currentEpIdx = 0
      this._resolved = false
      this.needTapPlay = false
      this.errMsg = ''
      this.playEpisode(0)
    },
    async playEpisode(idx) {
      if (!this.episodes.length || idx < 0 || idx >= this.episodes.length) return
      this.currentEpIdx = idx
      const ep = this.episodes[idx]
      if (!ep || !ep.url) {
        this.errMsg = '选集无效'
        return
      }
      const line = this.currentLine
      const flag = (line && line.flag) || ''
      this.playTitle = ((this.detail && this.detail.title) || '正在播放') + (flag ? ' · ' + flag : '') + ' · ' + ep.name
      await this.$nextTick()
      this.startPlayUrl(ep.url)
    },
    async startPlayUrl(url) {
      if (!url) {
        this.errMsg = '播放地址为空'
        return
      }
      this.loading = true
      this.loadingText = '加载中…'
      this.errMsg = ''
      // 重置进度条
      this.currentTime = 0
      this.duration = 0
      this.buffered = 0
      let m3u8Url = url
      if (!this._isDirectUrl(url) && !this._resolved) {
        this.loadingText = '解析播放地址…'
        try {
          const resolved = await fetchOnlineResolve(url)
          if (resolved) {
            m3u8Url = resolved
            this._resolved = true
          } else {
            this.loading = false
            this.errMsg = '无法解析视频地址，请重试或更换线路'
            return
          }
        } catch (e) {
          this.loading = false
          this.errMsg = '解析失败'
          return
        }
      }
      // 统一使用 H5/HLS 播放方案（App 端 WebView 也支持）
      this._playH5(m3u8Url)
    },
    _playH5(m3u8Url) {
      const proxiedUrl = this._toStreamUrl(m3u8Url)
      let video = this._createH5Video()
      this._ensureH5Video()

      // 非 m3u8 直接用 video.src 播放
      if (!proxiedUrl.includes('.m3u8')) {
        video.src = proxiedUrl
        this.loading = false
        video.play().catch((e) => {
          if (e && (e.name === 'NotAllowedError' || e.name === 'AbortError')) {
            this.needTapPlay = true
          }
        })
        return
      }

      // m3u8 用 HLS.js 播放
      this._loadHls().then((Hls) => {
        if (!Hls) {
          this.loading = false
          this.errMsg = 'HLS 加载失败'
          return
        }

        // 如果原生支持 HLS（iOS Safari），直接设 src
        if (video.canPlayType('application/vnd.apple.mpegurl')) {
          video.src = proxiedUrl
          this.loading = false
          video.addEventListener('loadedmetadata', () => {
            video.play().catch(() => {
              this.needTapPlay = true
            })
          }, { once: true })
          return
        }

        if (Hls.isSupported()) {
          this.destroyHls()
          video = this._createH5Video()
          this._ensureH5Video()
          // file:// 环境下 Web Worker 不可用，必须禁用
          const isFileProtocol = typeof window !== 'undefined' && window.location && window.location.protocol === 'file:'
          const hls = new Hls({
            enableWorker: !isFileProtocol,
            lowLatencyMode: false,
            maxBufferLength: 30,
            maxMaxBufferLength: 60,
            fragLoadingTimeOut: 60000,
            manifestLoadingTimeOut: 30000,
            levelLoadingTimeOut: 30000,
            fragLoadingMaxRetry: 6,
            manifestLoadingMaxRetry: 4,
            levelLoadingMaxRetry: 4
          })
          this._hls = hls
          hls.loadSource(proxiedUrl)
          hls.attachMedia(video)
          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            this.loading = false
            video.play().catch((e) => {
              if (e && (e.name === 'NotAllowedError' || e.name === 'AbortError')) {
                this.needTapPlay = true
              }
            })
          })
          hls.on(Hls.Events.ERROR, (_, data) => {
            console.error('[player] HLS error:', data)
            if (data && data.fatal) {
              if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                hls.startLoad()
              } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                hls.recoverMediaError()
              } else {
                this.loading = false
                this.errMsg = '播放错误: ' + (data.details || 'unknown')
              }
            }
          })
        } else {
          this.loading = false
          this.errMsg = '当前浏览器不支持 HLS 播放'
        }
      }).catch((err) => {
        console.error('[player] HLS.js load failed:', err)
        this.loading = false
        this.errMsg = '视频解码器加载失败'
      })
    },
    _toStreamUrl(url) {
      // 非 m3u8/video 格式直接返回
      if (/\.(mp4|flv|ts|mov|mkv|avi|webm)(\?|#|$)/i.test(url)) return url
      // 运行时检测：file:// 环境（App WebView）用远程代理，http(s):// 环境用本地代理
      const REMOTE = 'https://1302446649-7terr1rghd.ap-guangzhou.tencentscf.com'
      let base
      if (typeof window !== 'undefined' && window.location && window.location.protocol === 'file:') {
        // App WebView (file://) — 直连远程流代理
        base = REMOTE
      } else if (typeof window !== 'undefined' && window.location && window.location.hostname === 'localhost') {
        // 本地开发 — 走 Vite 代理
        base = '/__pyapi'
      } else {
        // H5 部署 — 直连远程
        base = REMOTE
      }
      return base + '/api/stream?url=' + encodeURIComponent(url) + '&prefix=' + encodeURIComponent(base)
    },
    _loadHls() {
      // file:// 环境（App WebView）下 import() 不可用，优先用 script 标签加载
      if (typeof window !== 'undefined' && window.location && window.location.protocol === 'file:') {
        return new Promise((resolve, reject) => {
          if (window.Hls) return resolve(window.Hls)
          const s = document.createElement('script')
          s.src = './static/hls.min.js'
          s.onload = () => {
            if (window.Hls) resolve(window.Hls)
            else reject(new Error('Hls not found after load'))
          }
          s.onerror = () => reject(new Error('hls.js script load failed'))
          document.head.appendChild(s)
        })
      }
      // 正常 web 环境用 ES module
      return import('hls.js').then((m) => m.default || m.Hls || window.Hls).catch(() => {
        return new Promise((resolve, reject) => {
          if (window.Hls) return resolve(window.Hls)
          const s = document.createElement('script')
          s.src = './static/hls.min.js'
          s.onload = () => resolve(window.Hls)
          s.onerror = () => reject(new Error('hls.js load failed'))
          document.head.appendChild(s)
        })
      })
    },
    destroyHls() {
      if (this._hls) {
        try { this._hls.destroy() } catch (e) {}
        this._hls = null
      }
      if (this._h5Video) {
        if (this._h5Video.parentNode) {
          this._h5Video.parentNode.removeChild(this._h5Video)
        }
        this._h5Video = null
      }
    },
    selectEpisode(i) {
      if (i === this.currentEpIdx) {
        this.showPanel = false
        return
      }
      this._resolved = false
      this.needTapPlay = false
      this.errMsg = ''
      this.playEpisode(i)
      this.showPanel = false
    },
    onLoaded() {
      this.loading = false
    },
    onVideoError(e) {
      this.loading = false
      this.errMsg = '播放失败'
    },
    tapToPlay() {
      this.needTapPlay = false
      const video = this._h5Video
      if (!video) return
      video.muted = false
      this.mutedAuto = false
      video.play().catch(() => {
        video.muted = true
        this.mutedAuto = true
        video.play().catch(() => {})
      })
    },
    retry() {
      this.errMsg = ''
      this.needTapPlay = false
      this._resolved = false
      if (this.vodId && this.episodes.length) {
        this.playEpisode(this.currentEpIdx)
      } else if (this.rawUrl) {
        this.startPlayUrl(this.rawUrl)
      }
    },
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/home/home' })
    }
  }
}
</script>

<style scoped>
.player-page {
  position: fixed;
  inset: 0;
  background-color: #000;
  overflow: hidden;
}
.video-bg {
  position: absolute;
  inset: 0;
  background-color: #000;
}
.video-el {
  width: 100%;
  height: 100%;
  background-color: #000;
  object-fit: contain;
}
.video-el-shorts {
  object-fit: cover;
}

/* ================ 电影/电视剧模式：16:9 视频 + 下方选集 ================ */
.player-page.movie-mode {
  display: flex;
  flex-direction: column;
  background-color: #1a1a1a;
}
.movie-mode .video-bg {
  position: relative;
  width: 100%;
  height: 56.25vw; /* 16:9 比例 */
  flex-shrink: 0;
}
.movie-mode .video-el {
  height: 100%;
}

/* 通用遮罩层 */
.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
  z-index: 5;
}
.loading-overlay { background-color: rgba(0, 0, 0, 0.5); }
.error-overlay { background-color: rgba(0, 0, 0, 0.85); }
.tap-play-overlay {
  background-color: rgba(0, 0, 0, 0.5);
  cursor: pointer;
}
.spinner {
  width: 72rpx;
  height: 72rpx;
  border: 6rpx solid rgba(255, 255, 255, 0.2);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.overlay-text {
  font-size: 26rpx;
  color: #FFFFFF;
  text-align: center;
}
.error-text { color: #FF6B6B; }
.retry-btn {
  height: 72rpx;
  padding: 0 48rpx;
  border-radius: 36rpx;
  background-color: #2B7FFF;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.retry-text { font-size: 26rpx; color: #FFFFFF; font-weight: 600; }
.tap-play-icon {
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding-left: 10rpx;
}

/* ================ H5 自定义进度条 ================ */
.player-progress {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 64rpx;
  display: flex;
  align-items: center;
  padding: 0 20rpx;
  padding-bottom: calc(8rpx + env(safe-area-inset-bottom));
  background: linear-gradient(0deg, rgba(0,0,0,0.7) 0%, transparent 100%);
  z-index: 25;
  gap: 16rpx;
}
/* 短剧模式：进度条避开底部选集栏 */
.shorts-progress {
  bottom: calc(200rpx + env(safe-area-inset-bottom));
  background: none;
  padding-bottom: 0;
}
.progress-time {
  font-size: 22rpx;
  color: #FFFFFF;
  font-variant-numeric: tabular-nums;
  min-width: 64rpx;
  text-align: center;
  flex-shrink: 0;
}
.progress-track {
  position: relative;
  flex: 1;
  height: 6rpx;
  border-radius: 3rpx;
  background-color: rgba(255, 255, 255, 0.25);
  cursor: pointer;
}
.progress-buffered {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 3rpx;
  background-color: rgba(255, 255, 255, 0.4);
  transition: width 0.2s;
}
.progress-played {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 3rpx;
  background-color: #FFB800;
}
.progress-thumb {
  position: absolute;
  top: 50%;
  width: 22rpx;
  height: 22rpx;
  border-radius: 50%;
  background-color: #FFFFFF;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 6rpx rgba(0, 0, 0, 0.5);
  pointer-events: none;
}

/* ================ 电影/电视剧布局 ================ */
/* 视频区顶部控制栏（叠加在 16:9 视频上） */
.movie-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
  background: linear-gradient(180deg, rgba(0,0,0,0.6) 0%, transparent 100%);
  z-index: 20;
}
.top-btn {
  width: 64rpx;
  height: 64rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.top-title-wrap {
  flex: 1;
  margin: 0 16rpx;
  text-align: center;
}
.top-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #FFFFFF;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.speed-btn-text {
  font-size: 28rpx;
  color: #FFFFFF;
  font-weight: 500;
}

/* 中央播放按钮（仅覆盖视频区） */
.center-control {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
}
.movie-center-control {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 56.25vw; /* 只覆盖 16:9 视频区 */
}
.center-play-btn {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.5);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

/* 选集/信息区（视频下方，可滚动） */
.movie-content {
  flex: 1;
  overflow-y: auto;
  background-color: #1a1a1a;
  padding: 24rpx 32rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
}
.movie-title-row {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 16rpx;
}
.movie-title {
  flex: 1;
  min-width: 0;
  font-size: 36rpx;
  font-weight: 700;
  color: #FFFFFF;
}
.movie-title-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-shrink: 0;
}
.movie-score {
  height: 44rpx;
  padding: 0 16rpx;
  border-radius: 8rpx;
  background-color: #FFB800;
  display: inline-flex;
  align-items: center;
}
.movie-score-text {
  font-size: 24rpx;
  font-weight: 700;
  color: #1C1C1E;
}
.movie-fav-btn {
  width: 72rpx;
  height: 72rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999rpx;
  background-color: rgba(255, 255, 255, 0.1);
}
.movie-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8rpx;
  margin-bottom: 20rpx;
}
.movie-meta-text {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.7);
}
.movie-meta-dot {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.4);
}
.movie-credits {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  margin-bottom: 24rpx;
}
.movie-credit-line {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}
.movie-synopsis-section {
  margin-bottom: 32rpx;
}
.movie-section-title {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: #FFFFFF;
  margin-bottom: 16rpx;
}
.movie-synopsis {
  font-size: 26rpx;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.7);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}
.movie-synopsis.expanded {
  -webkit-line-clamp: 99;
}
.movie-synopsis-toggle {
  display: inline-block;
  margin-top: 12rpx;
  font-size: 26rpx;
  color: #FFB800;
}
.movie-episodes-section {
  margin-bottom: 32rpx;
}
.movie-episodes-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 20rpx;
}
.movie-episodes-head .movie-section-title {
  margin-bottom: 0;
}
.movie-episodes-count {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.5);
}
.movie-ep-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
}
.movie-ep-item {
  min-width: calc((100% - 80rpx) / 5);
  height: 80rpx;
  padding: 0 16rpx;
  border-radius: 12rpx;
  background-color: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}
.movie-ep-item.active {
  background-color: #FFB800;
}
.movie-ep-name {
  font-size: 26rpx;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}
.movie-ep-item.active .movie-ep-name {
  color: #1C1C1E;
  font-weight: 700;
}
.movie-lines-section {
  margin-bottom: 32rpx;
}
.movie-line-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.movie-line-chip {
  height: 56rpx;
  padding: 0 28rpx;
  border-radius: 9999rpx;
  background-color: rgba(255, 255, 255, 0.08);
  display: inline-flex;
  align-items: center;
}
.movie-line-chip.active {
  background-color: #FFB800;
}
.movie-line-chip-text {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
}
.movie-line-chip.active .movie-line-chip-text {
  color: #1C1C1E;
  font-weight: 600;
}
.movie-bottom-spacer {
  height: 32rpx;
}

/* ================ 短剧布局（竖屏风格） ================ */
.shorts-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 140rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
  background: linear-gradient(180deg, rgba(0,0,0,0.7) 0%, transparent 100%);
  z-index: 20;
}
.shorts-top-btn {
  width: 72rpx;
  height: 72rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.4);
  flex-shrink: 0;
}
.shorts-top-info {
  flex: 1;
  margin: 0 20rpx;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.shorts-top-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #FFFFFF;
}
.shorts-top-sub {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.7);
}

/* 右侧操作栏 */
.shorts-side-bar {
  position: absolute;
  right: 20rpx;
  bottom: 320rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 36rpx;
  z-index: 15;
}
.shorts-side-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}
.shorts-side-icon-wrap {
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.45);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.shorts-side-icon-wrap.active {
  background-color: rgba(255, 184, 0, 0.25);
}
.shorts-speed-text {
  font-size: 28rpx;
  font-weight: 600;
  color: #FFFFFF;
}
.shorts-side-label {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.85);
}

/* 底部选集栏 */
.shorts-bottom-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 32rpx 24rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
  background: linear-gradient(0deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 70%, transparent 100%);
  z-index: 20;
}
.shorts-ep-scroll {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.shorts-ep-info {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.shorts-ep-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #FFFFFF;
}
.shorts-ep-divider {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.5);
}
.shorts-ep-status {
  font-size: 26rpx;
  color: #FFB800;
  font-weight: 500;
}
.shorts-ep-count {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.7);
}
.shorts-ep-strip {
  white-space: nowrap;
  margin: 0 -24rpx;
  padding: 0 24rpx;
}
.shorts-ep-list {
  display: inline-flex;
  gap: 16rpx;
  padding-right: 120rpx;
}
.shorts-ep-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 112rpx;
  height: 72rpx;
  padding: 0 24rpx;
  border-radius: 36rpx;
  background-color: rgba(255, 255, 255, 0.12);
  flex-shrink: 0;
}
.shorts-ep-chip.active {
  background-color: #FFB800;
}
.shorts-ep-chip-name {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
}
.shorts-ep-chip.active .shorts-ep-chip-name {
  color: #1C1C1E;
  font-weight: 700;
}
.shorts-ep-expand {
  position: absolute;
  right: 24rpx;
  bottom: calc(32rpx + env(safe-area-inset-bottom));
  height: 72rpx;
  padding: 0 20rpx;
  display: inline-flex;
  align-items: center;
  gap: 4rpx;
  border-radius: 36rpx;
  background-color: rgba(255, 184, 0, 0.9);
}
.shorts-ep-expand-text {
  font-size: 26rpx;
  color: #1C1C1E;
  font-weight: 600;
}

/* ================ 底部弹出面板（共用） ================ */
.panel-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  z-index: 30;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.panel {
  background-color: #1C1C1E;
  border-radius: 32rpx 32rpx 0 0;
  max-height: 75vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel-handle {
  width: 64rpx;
  height: 8rpx;
  border-radius: 4rpx;
  background-color: rgba(255, 255, 255, 0.2);
  margin: 16rpx auto 0;
}

.work-info {
  display: flex;
  gap: 20rpx;
  padding: 24rpx 32rpx 20rpx;
}
.work-cover {
  width: 120rpx;
  height: 160rpx;
  border-radius: 12rpx;
  background-color: #333;
  flex-shrink: 0;
}
.work-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8rpx;
}
.work-title-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.work-title {
  font-size: 34rpx;
  font-weight: 700;
  color: #FFFFFF;
  flex: 1;
}
.work-subtitle {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.5);
}
.work-desc {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

.ellipsis-2 {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.panel-tabs {
  display: flex;
  gap: 48rpx;
  padding: 0 32rpx;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.1);
}
.panel-tab {
  padding: 20rpx 0;
  position: relative;
}
.panel-tab.active .panel-tab-text {
  color: #FFFFFF;
  font-weight: 600;
}
.panel-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 40rpx;
  height: 6rpx;
  border-radius: 3rpx;
  background-color: #FFB800;
}
.panel-tab-text {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.5);
}

.panel-content {
  flex: 1;
  max-height: 50vh;
  padding: 24rpx 32rpx;
}
.intro-text {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}
.ep-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.ep-item {
  width: calc((100% - 80rpx) / 6);
  height: 80rpx;
  border-radius: 12rpx;
  background-color: rgba(255, 255, 255, 0.08);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.ep-item.active {
  background-color: #FFB800;
}
.ep-item .ep-name {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
}
.ep-item.active .ep-name {
  color: #1C1C1E;
  font-weight: 700;
}

.series-list {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}
.series-item {
  width: calc((100% - 48rpx) / 4);
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.series-cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 12rpx;
  background-color: #333;
}
.series-title {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}

.panel-bottom-spacer {
  height: 16rpx;
}

.favorite-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  padding: 24rpx 32rpx;
  border-top: 1rpx solid rgba(255, 255, 255, 0.1);
  background-color: #1C1C1E;
}
.favorite-text {
  font-size: 30rpx;
  font-weight: 600;
  color: #FFB800;
}

/* Modal */
.modal-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.7);
  z-index: 40;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
.modal-list {
  background-color: #2C2C2E;
  border-radius: 24rpx;
  min-width: 300rpx;
  overflow: hidden;
}
.modal-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 48rpx;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.08);
}
.modal-item:last-child { border-bottom: none; }
.modal-item.active .modal-item-text { color: #FFB800; }
.modal-item-text {
  font-size: 30rpx;
  color: #FFFFFF;
}
.modal-check {
  font-size: 28rpx;
  color: #FFB800;
}
</style>
