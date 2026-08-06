/**
 * VIIMK 应用配置
 */

// 当前版本信息（与 manifest.json 保持一致）
export const APP_VERSION = {
  versionName: '1.0.0',
  versionCode: 100
}

// 更新检查接口地址
// 将此地址替换为你实际的版本检查 API
// 返回格式: { code: 0, data: { versionCode, versionName, downloadUrl, updateLog, forceUpdate } }
export const UPDATE_CHECK_URL = 'https://api.viimk.com/app/check-update'
