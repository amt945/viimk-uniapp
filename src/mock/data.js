// VIIMK 模拟数据
// 图片资源 (static 目录)
const IMG = {
  santi: '/static/images/image_0_yi19x4.jpg',
  kuangbiao: '/static/images/image_1_yi19x4.jpg',
  manchang: '/static/images/image_2_yi19x4.jpg',
  fanhua: '/static/images/image_3_yi19x4.jpg',
  santi2: '/static/images/image_4_yi19x4.jpg',
  liulang: '/static/images/image_5_yi19x4.jpg',
  qingyu: '/static/images/image_6_yi19x4.jpg',
  yishan: '/static/images/image_7_yi19x4.jpg',
  shanai: '/static/images/image_8_yi19x4.jpg',
  qingyu2: '/static/images/image_9_yi19x4.jpg'
}

export { IMG }

// 首页轮播 / 热门 banner
export const heroBanner = {
  id: 1,
  title: '三体',
  cover: IMG.santi,
  year: '2024',
  genre: '剧情 / 科幻',
  region: '中国大陆',
  score: '9.4',
  tag: '热门'
}

// 首页分类
export const homeCategories = ['推荐', '热播', '都市', '古装', '悬疑']

// 热门推荐 (3列网格)
export const hotRecommend = [
  { id: 1, title: '狂飙', cover: IMG.kuangbiao, tag: '扫黑除恶' },
  { id: 2, title: '漫长的季节', cover: IMG.manchang, tag: '悬疑追凶' },
  { id: 3, title: '繁花', cover: IMG.fanhua, tag: '年代情感' }
]

// 为您推荐 (横向卡片)
export const forYou = [
  { id: 1, title: '三体', cover: IMG.santi2, desc: '地球文明与三体文明的首次接触，开启人类命运的宏大篇章。', tag: '科幻', score: '9.4分' },
  { id: 2, title: '流浪地球2', cover: IMG.liulang, desc: '太阳即将毁灭，人类在地球表面建造出巨大的推进器，寻找新的家园。', tag: '灾难', score: '9.1分' },
  { id: 3, title: '庆余年', cover: IMG.qingyu, desc: '身世神秘的少年范闲，历经家族、江湖、庙堂的种种考验与锤炼。', tag: '古装', score: '8.8分' }
]

// 短剧-推荐 tab
export const shortsRecommendTabs = ['推荐', '热门', '都市', '古装', '悬疑', '玄幻', '甜宠', '复仇']

export const shortsRecommendList = [
  { id: 1, title: '三体', cover: IMG.kuangbiao, meta: '科幻 · 12集 · 8.9分' },
  { id: 2, title: '狂飙', cover: IMG.yishan, meta: '都市 · 24集 · 9.1分' },
  { id: 3, title: '一闪一闪亮星星', cover: IMG.manchang, meta: '爱情 · 16集 · 8.5分' },
  { id: 4, title: '重生之巅峰', cover: IMG.santi2, meta: '玄幻 · 30集 · 8.2分' },
  { id: 5, title: '繁花', cover: IMG.shanai, meta: '年代 · 20集 · 8.8分' },
  { id: 6, title: '流浪地球2', cover: IMG.liulang, meta: '科幻 · 18集 · 8.7分' },
  { id: 7, title: '漫长的季节', cover: IMG.qingyu, meta: '悬疑 · 14集 · 9.0分' },
  { id: 8, title: '庆余年', cover: IMG.qingyu2, meta: '古装 · 28集 · 8.6分' },
  { id: 9, title: '偷偷藏不住', cover: IMG.fanhua, meta: '甜宠 · 22集 · 8.3分' }
]

// 短剧-关注 tab
export const shortsFollowTabs = ['关注', '都市', '甜宠', '逆袭', '穿越', '古装']

export const shortsFollowRegions = ['全部', '大陆', '港台', '日韩']

export const shortsFollowList = [
  { id: 1, title: '闪婚厚爱', cover: IMG.shanai, rating: '9.2', meta: '都市 · 2024' },
  { id: 2, title: '重生之巅峰', cover: IMG.kuangbiao, rating: '8.8', meta: '逆袭 · 2024' },
  { id: 3, title: '甜蜜契约', cover: IMG.manchang, rating: '9.0', meta: '甜宠 · 2024' },
  { id: 4, title: '穿越之王者', cover: IMG.santi2, rating: '8.5', meta: '穿越 · 2023' },
  { id: 5, title: '宫墙柳', cover: IMG.qingyu, rating: '9.1', meta: '古装 · 2023' },
  { id: 6, title: '都市风云', cover: IMG.yishan, rating: '8.6', meta: '都市 · 2024' },
  { id: 7, title: '沙漠玫瑰', cover: IMG.qingyu2, rating: '8.9', meta: '逆袭 · 2023' },
  { id: 8, title: '爱在黎明前', cover: IMG.fanhua, rating: '9.3', meta: '甜宠 · 2024' }
]

// 我的页面
export const profileStats = [
  { label: '历史记录', value: 12 },
  { label: '我的收藏', value: 5 },
  { label: '离线缓存', value: 3 }
]

export const profileMenu = [
  { id: 'history', icon: 'history', text: '历史记录', badge: false },
  { id: 'favorite', icon: 'heart', text: '我的收藏', badge: false },
  { id: 'cache', icon: 'download', text: '离线缓存', badge: false },
  { id: 'parse', icon: 'play-square', text: 'VIP 视频解析', badge: false },
  { id: 'notify', icon: 'bell', text: '消息通知', badge: true },
  { id: 'setting', icon: 'settings-2', text: '设置', badge: false },
  { id: 'about', icon: 'info', text: '关于', badge: false }
]

// 历史记录
export const historyList = [
  { id: 1, title: '三体', cover: IMG.santi2, episode: 8, totalEpisode: 30, progress: 62, time: '今天 21:30' },
  { id: 2, title: '狂飙', cover: IMG.kuangbiao, episode: 15, totalEpisode: 39, progress: 38, time: '昨天 22:10' },
  { id: 3, title: '漫长的季节', cover: IMG.manchang, episode: 3, totalEpisode: 12, progress: 85, time: '2天前' },
  { id: 4, title: '繁花', cover: IMG.fanhua, episode: 20, totalEpisode: 30, progress: 12, time: '3天前' },
  { id: 5, title: '庆余年', cover: IMG.qingyu, episode: 6, totalEpisode: 46, progress: 55, time: '5天前' },
  { id: 6, title: '流浪地球2', cover: IMG.liulang, episode: 1, totalEpisode: 1, progress: 90, time: '1周前' }
]

// 我的收藏
export const favoriteList = [
  { id: 1, title: '三体', cover: IMG.santi2, meta: '科幻 · 9.4分', rating: '9.4' },
  { id: 2, title: '狂飙', cover: IMG.kuangbiao, meta: '扫黑除恶 · 9.1分', rating: '9.1' },
  { id: 3, title: '漫长的季节', cover: IMG.manchang, meta: '悬疑追凶 · 9.0分', rating: '9.0' },
  { id: 4, title: '繁花', cover: IMG.fanhua, meta: '年代情感 · 8.8分', rating: '8.8' },
  { id: 5, title: '庆余年', cover: IMG.qingyu, meta: '古装 · 8.8分', rating: '8.8' },
  { id: 6, title: '流浪地球2', cover: IMG.liulang, meta: '灾难 · 9.1分', rating: '9.1' }
]

// 关于
export const aboutInfo = {
  appName: 'VIIMK',
  slogan: '看见每一部热爱',
  version: '1.0.1',
  build: '20260807',
  description: 'VIIMK 是一款专注于优质短剧与影视内容的流媒体应用，致力于为用户提供沉浸式的观影体验，发现每一部值得热爱的作品。'
}

export const aboutMenu = [
  { id: 'agreement', text: '用户协议' },
  { id: 'privacy', text: '隐私政策' },
  { id: 'update', text: '检查更新' }
]
