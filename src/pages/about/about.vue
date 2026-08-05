<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <view class="icon-btn" @tap="goBack">
        <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
      </view>
      <text class="header-title">关于</text>
      <view class="icon-btn"></view>
    </view>

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <!-- 品牌 -->
      <view class="brand-block">
        <view class="logo-card">
          <text class="logo-text">VIIMK</text>
        </view>
        <text class="app-name">{{ info.appName }}</text>
        <text class="slogan">{{ info.slogan }}</text>
        <view class="version-tag">
          <text class="version-text">v{{ info.version }}</text>
        </view>
      </view>

      <!-- 简介 -->
      <view class="card desc-card">
        <text class="desc-title">应用介绍</text>
        <text class="desc-text">{{ info.description }}</text>
      </view>

      <!-- 信息 -->
      <view class="card info-card">
        <view class="info-item">
          <text class="info-label">版本号</text>
          <text class="info-value">v{{ info.version }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">构建号</text>
          <text class="info-value">{{ info.build }}</text>
        </view>
        <view class="info-item no-border">
          <text class="info-label">微信号</text>
          <text class="info-value">QIMAIKE</text>
        </view>
      </view>

      <!-- 菜单 -->
      <view class="card menu-card">
        <view
          v-for="(item, idx) in aboutMenu"
          :key="item.id"
          class="menu-item"
          :class="{ 'no-border': idx === aboutMenu.length - 1 }"
          @tap="onMenu(item)"
        >
          <text class="menu-text">{{ item.text }}</text>
          <VmkIcon name="chevron-right" :size="28" color="#9CA3AF" />
        </view>
      </view>

      <!-- 版权 -->
      <view class="copyright">
        <text class="copyright-text">Copyright © 2024-2026 VIIMK</text>
        <text class="copyright-text">All Rights Reserved</text>
      </view>

      <view class="bottom-spacer"></view>
    </scroll-view>

    <!-- 更新弹窗 -->
    <view v-if="updateDialog.show" class="update-mask" @tap="onMaskTap">
      <view class="update-box" @tap.stop>
        <text class="update-title">发现新版本</text>
        <text class="update-version">v{{ updateDialog.versionName }}</text>
        <scroll-view class="update-log" scroll-y>
          <text class="update-log-text">{{ updateDialog.updateLog }}</text>
        </scroll-view>
        <view class="update-progress" v-if="updateDialog.downloading">
          <view class="progress-bar" :style="{ width: updateDialog.progress + '%' }"></view>
          <text class="progress-text">{{ updateDialog.progress }}%</text>
        </view>
        <view class="update-actions">
          <view
            v-if="!updateDialog.forceUpdate && !updateDialog.downloading"
            class="update-btn update-btn-ghost"
            @tap="closeUpdateDialog"
          >
            <text class="update-btn-text">稍后再说</text>
          </view>
          <view
            class="update-btn update-btn-primary"
            :class="{ 'update-btn-disabled': updateDialog.downloading }"
            @tap="onConfirmUpdate"
          >
            <text class="update-btn-text-primary">
              {{ updateDialog.downloading ? '下载中...' : '立即更新' }}
            </text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchAboutInfo, fetchAboutMenu, fetchAppVersion } from '@/api/index.js'

export default {
  name: 'About',
  components: { StatusBar, VmkIcon },
  data() {
    return {
      info: { appName: '', slogan: '', version: '', build: '', description: '' },
      aboutMenu: [],
      // 更新弹窗状态
      updateDialog: {
        show: false,
        versionName: '',
        updateLog: '',
        apkUrl: '',
        apkUrlType: 'direct',
        forceUpdate: false,
        downloading: false,
        progress: 0
      },
      _dtask: null   // plus.downloader 实例引用
    }
  },
  async onShow() {
    const [info, menu] = await Promise.all([
      fetchAboutInfo(),
      fetchAboutMenu()
    ])
    this.info = info
    this.aboutMenu = menu
  },
  methods: {
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/profile/profile' })
    },
    onMenu(item) {
      if (item.id === 'update') {
        this.checkUpdate()
      } else if (item.id === 'agreement') {
        uni.navigateTo({ url: '/pages/legal/agreement' })
      } else if (item.id === 'privacy') {
        uni.navigateTo({ url: '/pages/legal/privacy' })
      } else {
        uni.showToast({ title: item.text, icon: 'none' })
      }
    },
    /** 检查更新 */
    async checkUpdate() {
      // #ifdef APP-PLUS
      uni.showLoading({ title: '检查中...', mask: true })
      const v = await fetchAppVersion()
      uni.hideLoading()
      if (!v) {
        uni.showToast({ title: '检查更新失败，请稍后重试', icon: 'none' })
        return
      }
      const currentCode = parseInt(plus.runtime.versionCode, 10) || 0
      const serverCode = parseInt(v.versionCode, 10) || 0
      // 低于最低支持版本 → 强制更新
      const forceByMinSupport = currentCode < (parseInt(v.minSupport, 10) || 0)
      if (serverCode > currentCode) {
        this.updateDialog = {
          show: true,
          versionName: v.versionName,
          updateLog: v.updateLog || '优化体验，修复已知问题',
          apkUrl: v.apkUrl,
          apkUrlType: v.apkUrlType,
          forceUpdate: !!v.forceUpdate || forceByMinSupport,
          downloading: false,
          progress: 0
        }
      } else {
        uni.showToast({ title: '已是最新版本', icon: 'none' })
      }
      // #endif
      // #ifndef APP-PLUS
      uni.showToast({ title: '请在 App 内检查更新', icon: 'none' })
      // #endif
    },
    /** 点遮罩：非强制更新时可关闭 */
    onMaskTap() {
      if (!this.updateDialog.forceUpdate && !this.updateDialog.downloading) {
        this.closeUpdateDialog()
      }
    },
    closeUpdateDialog() {
      this.updateDialog.show = false
    },
    /** 确认更新：开始下载 */
    onConfirmUpdate() {
      if (this.updateDialog.downloading) return
      // #ifdef APP-PLUS
      const url = this.updateDialog.apkUrl
      if (!url) {
        uni.showToast({ title: '下载地址无效', icon: 'none' })
        return
      }
      // share 类型：无法直接下载，打开系统浏览器
      if (this.updateDialog.apkUrlType === 'share') {
        plus.runtime.openURL(url)
        return
      }
      // direct 类型：plus.downloader 下载 + install
      this.updateDialog.downloading = true
      this.updateDialog.progress = 0
      const savePath = '_doc/viimk-update.apk'
      const dtask = plus.downloader.createDownload(url, { filename: savePath }, (d, status) => {
        this.updateDialog.downloading = false
        if (status === 200) {
          // 安装 APK
          plus.runtime.install(d.filename, { force: true }, () => {
            // 安装成功后重启应用
            plus.runtime.restart()
          }, (err) => {
            uni.showModal({
              title: '安装失败',
              content: '无法安装更新包，请稍后重试',
              showCancel: false
            })
          })
        } else {
          uni.showModal({
            title: '下载失败',
            content: '更新包下载失败（状态码 ' + status + '），请稍后重试',
            showCancel: false
          })
        }
      })
      // 监听下载进度
      dtask.addEventListener('statechanged', (task) => {
        if (task.downloadedSize > 0 && task.totalSize > 0) {
          const p = Math.floor(task.downloadedSize * 100 / task.totalSize)
          if (p !== this.updateDialog.progress) {
            this.updateDialog.progress = p
          }
        }
      })
      this._dtask = dtask
      dtask.start()
      // #endif
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
  height: 88rpx;
  padding: 0 24rpx;
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

.page-content {
  flex: 1;
  padding: 32rpx;
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
  display: flex;
  flex-direction: column;
  gap: 32rpx;
}

/* 品牌区 */
.brand-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32rpx 0;
}

.logo-card {
  width: 160rpx;
  height: 160rpx;
  border-radius: 32rpx;
  background: linear-gradient(180deg, #2B7FFF 0%, #1A6DE5 100%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 40rpx rgba(43, 127, 255, 0.35);
  margin-bottom: 24rpx;
}

.logo-text {
  font-size: 40rpx;
  font-weight: 700;
  color: #FFFFFF;
  letter-spacing: -1rpx;
}

.app-name {
  font-size: var(--vmk-text-xl);
  font-weight: 700;
  color: var(--vmk-foreground);
  margin-bottom: 8rpx;
}

.slogan {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
  margin-bottom: 20rpx;
}

.version-tag {
  height: 44rpx;
  padding: 0 20rpx;
  border-radius: var(--vmk-radius-full);
  background-color: var(--vmk-muted-bg);
  border: 1px solid var(--vmk-border);
  display: inline-flex;
  align-items: center;
}

.version-text {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
}

.card {
  background-color: var(--vmk-card);
  border-radius: var(--vmk-radius-lg);
  overflow: hidden;
}

/* 简介 */
.desc-card {
  padding: 32rpx;
}

.desc-title {
  display: block;
  font-size: var(--vmk-text-base);
  font-weight: 600;
  color: var(--vmk-foreground);
  margin-bottom: 16rpx;
}

.desc-text {
  font-size: var(--vmk-text-sm);
  line-height: 1.7;
  color: var(--vmk-muted);
}

/* 信息 */
.info-card {
  padding: 0 32rpx;
}

.info-item {
  height: 96rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--vmk-border);
}

.info-item.no-border {
  border-bottom: none;
}

.info-label {
  font-size: var(--vmk-text-base);
  color: var(--vmk-muted);
}

.info-value {
  font-size: var(--vmk-text-base);
  color: var(--vmk-foreground);
}

/* 菜单 */
.menu-item {
  height: 104rpx;
  padding: 0 32rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--vmk-border);
}

.menu-item.no-border {
  border-bottom: none;
}

.menu-text {
  font-size: var(--vmk-text-base);
  color: var(--vmk-foreground);
}

/* 版权 */
.copyright {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
  padding: 32rpx 0;
}

.copyright-text {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
}

.bottom-spacer {
  height: 32rpx;
}

/* ============ 更新弹窗 ============ */
.update-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.update-box {
  width: 600rpx;
  background-color: var(--vmk-card);
  border-radius: var(--vmk-radius-lg);
  padding: 48rpx 40rpx 32rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.update-title {
  font-size: 36rpx;
  font-weight: 700;
  color: var(--vmk-foreground);
  margin-bottom: 8rpx;
}

.update-version {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
  margin-bottom: 24rpx;
}

.update-log {
  width: 100%;
  max-height: 240rpx;
  padding: 24rpx;
  background-color: var(--vmk-muted-bg);
  border-radius: var(--vmk-radius-md);
  margin-bottom: 32rpx;
  box-sizing: border-box;
}

.update-log-text {
  font-size: var(--vmk-text-sm);
  line-height: 1.7;
  color: var(--vmk-muted);
  white-space: pre-wrap;
  word-break: break-word;
}

/* 进度条 */
.update-progress {
  width: 100%;
  height: 48rpx;
  background-color: var(--vmk-muted-bg);
  border-radius: var(--vmk-radius-full);
  position: relative;
  margin-bottom: 32rpx;
  overflow: hidden;
}

.progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  background: linear-gradient(90deg, #2B7FFF 0%, #1A6DE5 100%);
  border-radius: var(--vmk-radius-full);
  transition: width 0.2s ease;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: var(--vmk-text-xs);
  color: var(--vmk-foreground);
  font-weight: 600;
}

/* 按钮 */
.update-actions {
  width: 100%;
  display: flex;
  gap: 24rpx;
}

.update-btn {
  flex: 1;
  height: 88rpx;
  border-radius: var(--vmk-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.update-btn-ghost {
  background-color: var(--vmk-muted-bg);
}

.update-btn-text {
  font-size: var(--vmk-text-base);
  color: var(--vmk-muted);
}

.update-btn-primary {
  background: linear-gradient(180deg, #2B7FFF 0%, #1A6DE5 100%);
}

.update-btn-primary.update-btn-disabled {
  opacity: 0.6;
}

.update-btn-text-primary {
  font-size: var(--vmk-text-base);
  color: #FFFFFF;
  font-weight: 600;
}
</style>
