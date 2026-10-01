# world.execute(me); · 大肥鱼眼中的 world.execute(me)

## 本地改编：GPT × Codex

此工作区正在制作个人非商业同人改编：GPT 由用户授权的 GPT 角色形象呈现，Codex 是承载她的代码世界。全身角色源图位于 `assets/gpt-character-fusion.png`，改编渲染不再使用仓库保留的鲸鱼娘美术。角色图由用户提供的授权参考经 AI 辅助融合与去背；发布时请保留这项 AI 创作说明。片中模型参数和训练数据均为剧情示意，不代表 OpenAI 的真实模型规格、内部系统或产品行为。

成片是非官方同人作品，与 OpenAI、Codex、Mili 均无从属或合作关系，也未获其认可。公开发布仍须自备歌曲，并遵守 [Mili 官方指引](https://projectmili.com/copyright-guidelines)；代码许可不覆盖歌曲、歌词、商标或角色美术。

![preview](docs/preview.jpg)

一支用代码逐帧渲染的 TUI 风格 PV，**非官方同人作品**：
- 左边是 GPT 和"你"的聊天窗口；
- 右边是 Codex 承载的代码世界，也是 GPT 的模型化视觉空间。

这个仓库是这支片子的全部出片代码。你自备歌曲，一条命令就能从头渲染出来。

- 成片：[B 站 BV1xCai6aE9g](https://www.bilibili.com/video/BV1xCai6aE9g/)（原舞者版；开源重建差异见下文）
- 作者：MisakaZentai

*English: this local adaptation maps the heroine to GPT and the surrounding code world to Codex. Frames are
rendered from song time: the chat window uses HTML screenshots and the code world uses PIL. The repository retains
upstream DeepSeek-themed source assets and notices, while this adaptation uses the user-authorized GPT character
art. On-screen model details are fictional story props. Bring your own song and run `python build.py all`; see
NOTICE.md for source, art, AI disclosure, and music notes.*

## 快速开始

需要：
- Python 3.12+，装上 `pip install -r requirements.txt`；
- Node 20+；
- ffmpeg（在 PATH 里）；
- Windows 字体。在别的系统上可以换字体，见 [docs/FONTS.md](docs/FONTS.md)。

```
npm install
npx playwright install chromium
# 把歌曲放到 input/song.mp3（见 input/README.md）
python build.py all            # 检查 → 歌词 → 替身舞者 → 页面截图 → 渲染
python build.py all --4k       # 另出 3840×2160 版
```

- **输出**：`out/film.mp4` 是 1280×720 成片；`out/film_master.mp4` 是无损母版；加 `--4k` 时另有 `out/film_4k.mp4`。
- **耗时**：CPU 渲染全片大约十几分钟到半小时，取决于核数。有 CUDA 版 torch 时，加 `--gpu --python <那个 python>` 会快很多。
- **分步**：每一步也可以单独跑，`python build.py <check|lyrics|dancer|pages|render>`。

## 不在仓库里的，以及替代办法

| 东西 | 为什么 | 替代办法 |
|---|---|---|
| 歌曲音频 | Mili 的版权 | 自备，放到 `input/song.mp3`；`build.py check` 用 sha256 核对版本 |
| 歌词原文 | 歌词版权 | `build.py lyrics` 从 LRCLIB 下载到你的本机，再和仓库里的逐词时间（不含文字）合成 |
| 原片的舞者画面 | 涉及第三方 MMD 模型和动作的使用条件；AI 参考与衍生画面分发权限尚未确认 | 构建时用鲸鱼娘立绘生成替身，所以你渲染出的片子在这些地方和原片不同 |
| Consolas、微软雅黑等 Windows 字体 | 不可再分发 | 用本机的；其他系统可以换字体 |

## 重建出的片子和成片的差别

- **舞者**：见上表，用替身。
- **12.5–29 秒的检查点编号**：数字和成片不同。成片用的这段窗口截图，比代码里最后一次改编号公式要早。
- **123.5 秒前后 3 帧**：输入框的发送按钮颜色不同。原因同上。
- **后期差异（原因未核实）**：既有比对在 114.75–114.83 秒发现局部亮度差，在 159–161 秒最左两列发现约 10 级差值。CPU/GPU 后期实现不同是可能原因，尚未做控制变量验证。
- **验证范围**：2026-09-30 的既有 Windows 构建记录包含 4968 张窗口截图和全片母版数值比对，人工抽看 8 个时刻。母版差异筛选条件为“差值超过 8 级的像素占比超过 0.2%”；这不表示每个像素差值都在 8 级以内，也不等于逐帧视觉或音画验收。测试借用了已有 Playwright 环境，尚未证明全新安装及其他系统能复现相同排版。

## 仓库结构

目录名保留了制作时的工作名，代码之间靠相对位置互相找到，请不要改名。

| 路径 | 内容 |
|---|---|
| `build.py` | 一键出片 |
| `tools/` | 歌词合成（`lyrics.py`）、替身舞者（`placeholder_h3.py`） |
| `data/` | 不含文字的逐词时间、歌曲指纹、舞者帧的清单 |
| `film/pv_dsh_frontend_20260927/` | 左边的 dsh 窗口：各组页面脚本 `batch_*.py`、截图脚本 `seg_shot.mjs`、合成与补丁 `dsh_her.py`、`dsh_patch_*.py` |
| `film/tui_pv_world_execute_20260926/` | 右边的 TUI 引擎：`tuikit.py`，第一版镜头 `full/`，第二版连续性和转场 `continuity_full_v2/` 等 |
| `film/mmd_motion_eval_20260927/pv_full.py` | 舞者的时间表 |
| `film/third_party_references/` | 鲸鱼娘立绘和表情（CC BY-NC-SA 4.0） |
| `film/vendor/` | dsh 前端（`dsh-web-frontend`）和 Cordis 组件包（`dsh-client-ui-cordis`）的 CSS 和 JS（MIT，DeepSeek） |
| `docs/` | [制作原理](docs/HOW_IT_WORKS.md)、[字体](docs/FONTS.md) |

## 许可

- **代码**：MIT，见 [LICENSE](LICENSE)。
- **保留的上游美术**：鲸鱼娘立绘、表情及它们的改编部分按 CC BY-NC-SA 4.0 分享；本地 GPT × Codex 改编输出不使用它们。其他使用仍须保留署名链和许可链接，注明改动，不得商用，改编部分按同协议分享。
- **dsh 前端文件**：MIT，Copyright (c) 2026 DeepSeek。
- **字体**：SIL OFL 1.1。

第三方清单见 [NOTICE.md](NOTICE.md)，一手授权来源和核实范围见 [docs/ASSET_SOURCES.md](docs/ASSET_SOURCES.md)。

## 分享视频

- 本项目使用了 AI 生成的角色美术；原片另含 AI 视频画面。发布相应成片时应明确标注包含 AI 生成内容，不能把纯代码渲染误写为全部画面均非 AI。
- Mili 的[官方指引](https://projectmili.com/copyright-guidelines)允许个人非商业二创，并要求 AI 同人内容明确标注。音乐与歌词的权利保留，不适用本仓库代码的 MIT 许可。
- 默认按非商业方式分享，保留完整素材署名和许可链接；商单、付费观看或收益计划等用途需另外确认。
- 原定稿舞者的 AI 参考权限仍有开放问题。开源重建使用替身；替身方案不表示原定稿已获得额外许可。
- 歌词短前缀是定位时间的实现方式；“连续五词扫描”仅是内容检查规则，不能作为版权免责标准。

## 署名

- **音乐**：Mili - world.execute(me);
- **角色**：GPT 角色形象由用户授权参考经 AI 辅助融合处理；来源说明见 [NOTICE.md](NOTICE.md)
- **界面**：改编自开源项目中的 dsh 前端组件，保留其原许可与署名
- **灵感**：野生大K《GPT6-Astra眼中的world.execute(me)》；仓库的组织方式参考了 [pdoom-video](https://github.com/mexicat/pdoom-video)
- **歌词数据**：LRCLIB（构建时下载，不随仓库分发）

这是非官方同人作品，与 OpenAI、Codex、Mili 没有从属或合作关系，也未经他们认可。
