# AppStore 监控服务

这是一个使用 GitHub Actions 的 AppStore 应用监控服务，它会定期检查指定的 iOS 应用是否在 App Store 上架，并通过方糖推送结果。

## 功能特点

- 在中国时间 8:00-22:00 之间每小时自动检查一次
- 支持手动触发检查
- 通过方糖推送检查结果
- 区分在线和下架的应用
- 使用 JSON 文件管理应用列表，方便维护

## 设置方法

1. Fork 本仓库到你的 GitHub 账号

2. 在仓库设置中添加 Secret:
   - 名称: `FANGTANG_KEY`
   - 值: 你的方糖 SendKey

3. 修改 `app_info.json` 文件，添加你要监控的应用:
   ```json
   [
     {
       "id": "应用ID",
       "name": "应用名称"
     },
     {
       "id": "另一个应用ID",
       "name": "另一个应用名称"
     }
   ]
   ```

4. GitHub Actions 会自动按计划运行，你也可以在 Actions 页面手动触发工作流

## 手动触发

在 GitHub 仓库页面，点击 "Actions" 标签，选择 "AppStore Monitor" 工作流，然后点击 "Run workflow" 按钮。

## 注意事项

- 确保你的方糖 SendKey 正确设置
- GitHub Actions 的计划任务可能会有几分钟的延迟
- 免费的 GitHub Actions 有使用限制，请合理设置检查频率
- 修改 `app_info.json` 文件后，GitHub 会自动使用新的应用列表 