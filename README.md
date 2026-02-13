## 使用说明

1. 点击 Fork 创建你自己的仓库分支。
2. 在分支中修改 `languages/chinese.lua`（基准语言文件）。
3. 提交并推送到 `master` 后，GitHub Actions 会自动触发 `Lang Parser Auto PR`。
4. 自动同步完成后，检查生成的语言变更与格式是否正确。

## 玩家翻译与提交流程

1. 先 Fork 本仓库，并在你自己的仓库创建一个新分支（例如 `translate-russian-2026`）。
2. 打开你要翻译的语言文件，例如 `languages/english.lua`、`languages/russian.lua`。
3. 查找以 `-- ` 开头的缺失占位行（由同步脚本生成），把它们改为正式翻译：
	- 只改右侧文本内容，不要改 key 路径结构。
	- 保留占位符和格式符号（如 `%s`、`%d`、`\n`）。
	- 保持 Lua 语法有效（引号、逗号、括号不要丢）。
4. 保存后提交到你的分支，提交信息建议写清楚语言和范围（例如：`feat(lang): translate russian role descriptions`）。
5. 在 GitHub 发起 Pull Request 到本仓库 `master`，说明你翻译了哪些文件/条目。
6. 等待维护者 review；如有修改意见，继续在同一分支追加提交即可自动更新 PR。

## Usage

1. Click Fork to create your branch.
2. Modify `languages/chinese.lua` (base language file).
3. After pushing to `master`, GitHub Actions will trigger `Lang Parser Auto PR` automatically.
4. Review the generated language changes and formatting.

总结：就翻译除chinese和bilbil特供版的就好了其他就不用管了
