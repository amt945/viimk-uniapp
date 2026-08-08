/**
 * VIIMK 版本更新检查
 *
 * 使用：
 *   import { checkUpdate } from '@/utils/update.js'
 *   checkUpdate()
 */

import { APP_VERSION, UPDATE_CHECK_URL } from '@/config/app.js'

/**
 * 比较版本号
 * @returns {boolean} 是否有新版本
 */
function hasNewVersion(remoteCode) {
  return remoteCode > APP_VERSION.versionCode
}

/**
 * 检查更新并弹出提示
 */
export function checkUpdate() {
  // #ifdef H5
  // H5 端通过 uni.request 请求远程 API
  uni.request({
    url: UPDATE_CHECK_URL,
    method: 'GET',
    timeout: 10000,
    success: (res) => {
      if (res.statusCode === 200 && res.data && res.data.code === 0) {
        const info = res.data.data
        if (info && hasNewVersion(info.versionCode)) {
          showUpdateDialog(info)
        }
      }
    },
    fail: () => {
      // 静默失败，不打扰用户
    }
  })
  // #endif

  // #ifdef APP-PLUS
  // App 端使用 plus.runtime 获取版本
  try {
    plus.runtime.getProperty(plus.runtime.appid, (widgetInfo) => {
      const currentCode = parseInt(widgetInfo.versionCode) || APP_VERSION.versionCode
      const currentName = widgetInfo.version || APP_VERSION.versionName

      uni.request({
        url: UPDATE_CHECK_URL,
        method: 'GET',
        timeout: 10000,
        success: (res) => {
          if (res.statusCode === 200 && res.data && res.data.code === 0) {
            const info = res.data.data
            if (info && info.versionCode > currentCode) {
              showUpdateDialog(info, info.forceUpdate)
            }
          }
        },
        fail: () => {}
      })
    })
  } catch (e) {
    // WebView H5 模式下退回 H5 版本
    uni.request({
      url: UPDATE_CHECK_URL,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.code === 0) {
          const info = res.data.data
          if (info && hasNewVersion(info.versionCode)) {
            showUpdateDialog(info)
          }
        }
      },
      fail: () => {}
    })
  }
  // #endif
}

/**
 * 显示更新对话框
 */
function showUpdateDialog(info, force = false) {
  const log = info.updateLog ? info.updateLog.replace(/\n/g, '\n') : '修复已知问题，优化用户体验'

  uni.showModal({
    title: `发现新版本 v${info.versionName}`,
    content: log,
    confirmText: '立即更新',
    cancelText: force ? '退出应用' : '稍后再说',
    showCancel: !force,
    success: (res) => {
      if (res.confirm) {
        downloadAndInstall(info.downloadUrl)
      } else if (force) {
        // 强制更新：退出应用
        // #ifdef APP-PLUS
        plus.runtime.quit()
        // #endif
        // #ifdef H5
        window.close()
        // #endif
      }
    }
  })
}

/**
 * 下载并安装新 APK
 */
function downloadAndInstall(url) {
  if (!url) {
    uni.showToast({ title: '更新包地址无效', icon: 'none' })
    return
  }

  uni.showLoading({ title: '准备下载...', mask: true })

  // #ifdef APP-PLUS
  // App 端：使用 plus.runtime.openURL 打开浏览器下载
  uni.hideLoading()
  uni.showModal({
    title: '开始下载',
    content: '将跳转到浏览器下载新版本，下载完成后点击安装包进行安装。',
    showCancel: false,
    confirmText: '前往下载',
    success: () => {
      // #ifdef APP-PLUS
      plus.runtime.openURL(url)
      // #endif
    }
  })
  // #endif

  // #ifdef H5
  // H5 端：直接打开下载链接
  uni.hideLoading()
  uni.showModal({
    title: '开始下载',
    content: '将跳转到浏览器下载新版本，下载完成后点击安装包进行安装。',
    showCancel: false,
    confirmText: '前往下载',
    success: () => {
      window.location.href = url
    }
  })
  // #endif
}
