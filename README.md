# Dota 2 装备价值计算器

纯静态网页，使用 GitHub Pages 托管。浏览器只加载本站的 JSON、装备图片与购买音效，无需连接 OpenDota、Valve 或 Wiki 接口。

## 使用

- 右键图标购买，重复右键增加数量；左键查看名称、价格、组件并可点击购买。
- 搜索支持英文名称和原页面已有的中文简称，`/` 聚焦搜索，`Esc` 清空。
- 支持数量调整、撤销、清空和复制 Build。
- 桌面使用紧凑四列分组，完整显示当前 182 件商店道具（含免费侦查守卫）。名称可悬停或点击查看。手机自动改为两列分组并允许滚动。
- 默认播放随站点提供的原版 `Ui_buy` 音效，也保留静音、合成音和本地音频切换。

## 数据更新

`.github/workflows/pages.yml` 在每小时第 17 分钟（UTC）检查 Valve 官方补丁列表，包括字母小版本。

1. 与 `site/data/items.json` 的补丁号比较；没有变化时立即结束，不下载装备数据、商店清单或图片，也不重新部署。
2. 检测到新版本后，先等待 OpenDota 的构建数据和 d2vpkr 的提取仓库出现补丁发布后的提交，再按固定提交读取数据；校验全部 11 个分组及每件道具的价格、名称和图片。
3. 下载新增道具图标，完成全部校验后才替换快照、提交并部署。失败时线上继续使用上一份成功快照，下个周期重试。

页面的“重新载入”只读取已发布快照。原版购买音效已经存入仓库，不参与定时下载。

官方补丁号用于触发快照，价格仍来自 OpenDota；这些社区数据源可能晚于游戏更新。更新器会等待上游提交，但提交时间不是官方对每条价格的版本认证。快照包含生成时间与来源，状态文字悬停可查看时间。同一版本的成功快照不会被定时任务重复生成。

GitHub 的定时任务可能延迟。公开仓库 60 天没有活动会自动暂停定时任务，因此工作流在连续 45 天无提交时写入一次空维护提交；它不抓取新装备数据、不改变快照，也不重新部署。可随时在 Actions → Update data and deploy Pages → Run workflow 手动检查。

参考：[GitHub 定时任务规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

## 本地运行

需要 Python 3.10 或以上，无第三方依赖：

```sh
python -m http.server 8000 --directory site
```

打开 `http://localhost:8000`。不要通过 `file://` 打开，因为浏览器会限制读取 JSON。

```sh
python scripts/sync_data.py
python -m unittest discover -s scripts -p 'test_*.py' -v
```

## 部署

GitHub 仓库 Settings → Pages → Source 选择 **GitHub Actions**，推送到 `main` 即可。工作流只上传 `site/`，不上传脚本或测试文件。

## 素材来源

- 版本：[Valve Dota 2 补丁列表](https://www.dota2.com/datafeed/patchnoteslist?language=english)
- 装备名称、价格和组件：[odota/dotaconstants](https://github.com/odota/dotaconstants)
- 商店分组：[dotabuff/d2vpkr shops.txt](https://github.com/dotabuff/d2vpkr/blob/master/dota/scripts/shops.txt)
- 装备图标：Valve / Steam CDN，下载到 `site/assets/items/`。
- 购买音效：[Liquipedia Commons — Ui_buy.mp3](https://liquipedia.net/commons/File:Ui_buy.mp3)，下载到 `site/assets/audio/ui_buy.mp3`。

Dota 2 名称、图标和音效归 Valve Corporation 所有。本项目是非官方工具。
