# 大巴赛博盲盒 · Daba Cyber Blind Box

原创 IP「大巴」的第一套潮玩盲盒：8 款公仔（7 常规 + 1 隐藏）+ 彩蛋「超能大巴」。主题：**下班后，我在偷偷变强**。

![大巴全款](docs/images/lineup.jpg)

## 一键安装 Skill：IP 盲盒快捷工作流

把任意 IP 形象做成盲盒全套：2D 款式设计 → 混元3D 建模 → 盒面设计 → Blender 渲染 → 可开盒的盲盒网页 → 产品介绍。装好后对 Claude 说「帮我把我的 IP 做成盲盒」就会按这套流程走。skill 自带 3 个 Blender 渲染脚本和一键生成开盒网页的脚本，只要改一下项目文件夹路径就能用。

**Claude Code（macOS / Linux）**，复制到终端回车：

```bash
mkdir -p ~/.claude/skills && curl -fsSL https://github.com/bigchen316/daba-cyber-blindbox/raw/main/ip-blindbox-pipeline.zip -o /tmp/ip-blindbox-pipeline.zip && unzip -oq /tmp/ip-blindbox-pipeline.zip -d ~/.claude/skills
```

**Claude Code（Windows PowerShell）**，复制到 PowerShell 回车：

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null; Invoke-WebRequest https://github.com/bigchen316/daba-cyber-blindbox/raw/main/ip-blindbox-pipeline.zip -OutFile "$env:TEMP\ip-blindbox-pipeline.zip"; Expand-Archive -Force "$env:TEMP\ip-blindbox-pipeline.zip" "$HOME\.claude\skills"
```

**Claude Code 插件方式**，在 Claude Code 里依次输入：

```
/plugin marketplace add bigchen316/daba-cyber-blindbox
/plugin install ip-blindbox-pipeline@daba-skills
```

**Claude 网页版 / 桌面版**：下载 [`ip-blindbox-pipeline.zip`](https://github.com/bigchen316/daba-cyber-blindbox/raw/main/ip-blindbox-pipeline.zip)，在 Claude 的设置里找到 Skills（技能），上传这个 zip 即可。

## 仓库内容

| 路径 | 是什么 |
| --- | --- |
| [`docs/产品介绍.md`](docs/产品介绍.md) | 产品介绍：IP 形象、款式表、包装、开盒体验、制作方式、规格 |
| [`site/index.html`](site/index.html) | 产品介绍展示网页，在线看：https://bigchen316.github.io/daba-cyber-blindbox/site/ |
| [`skills/ip-blindbox-pipeline/`](skills/ip-blindbox-pipeline/) | 工作流 skill：`SKILL.md` + 3 个 Blender 渲染脚本 + 一键生成开盒网页的 `build_site.py` |
| [`ip-blindbox-pipeline.zip`](ip-blindbox-pipeline.zip) | skill 打包，给 Claude 网页版 / 桌面版上传用 |

## 制作流程

1. 2D 形象设计（AI 生图）
2. 3D 建模（混元3D）
3. 盒面设计（HTML 排版导出 PNG）
4. Blender 渲染（产品图、盒子 72 帧转盘、公仔 24 帧转盘）
5. 盲盒网页（拖动看盒、开盒星星炸开、公仔可转、集齐 8 款召唤彩蛋）

## 授权

- `skills/` 里的工作流：MIT，随便用、随便改。
- 「大巴」IP 形象、公仔图、盒面等设计素材为原创作品，保留所有权利，未经许可请勿商用。
