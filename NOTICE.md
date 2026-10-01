# NOTICE：第三方素材与许可

## GPT × Codex 本地改编使用的角色图

- `assets/gpt-character-fusion.png` 为用户确认由其创作或已获授权的两张参考图，经 AI 辅助融合得到的 GPT 角色图；`assets/gpt_expressions/gpt-*.webp` 为从该图裁切的头像素材。
- `assets/gpt-keypose-reach.png` 和 `assets/gpt-keypose-dance.png` 是本改编以同一张用户授权角色参考图生成的透明动作关键帧，用于全曲 PV 的动态镜头；它们不代表 Live2D/逐部件拆分动画。
- `assets/gpt-keypose-step.png`、`gpt-keypose-cross.png`、`gpt-keypose-turn.png`、`gpt-keypose-settle.png` 是追加的 AI 动作图，与原有三张角色图共同组成 `assets/gpt-dance-atlas.png` 的 12 个姿势槽位；来源与镜像配置见相邻 JSON。`tools/gpt_sprite_dance.py` 将它们制作成像素拼帧及字符动作，替换上游的轻摇替身。生成提示词见 `assets/gpt-dance-prompts.txt`。
- GPT 角色图、动作图、封面及它们的派生素材不适用代码的 MIT 许可；本仓库未为这些美术额外授予再许可。再使用前请联系本版作者确认素材权限。此项不改变下方保留的上游美术许可。
- 该图用于改编 PV 的角色与头像；输出应标注角色图使用了用户授权素材并经 AI 辅助处理。八个表情资源目前共享同一裁切头像；若后续需要不同面部表情，需补充相应表情图层。
- 本地改编的输出不调用下方列出的鲸鱼娘图像及其衍生素材。上游文件仍保留在本仓库中并继续适用原许可；本说明不改变那些文件的许可。
- 片中的 GPT 模型参数、训练过程与 Codex 终端内容是虚构的剧情视觉，不代表 OpenAI 的产品或内部实现。

## 非官方同人声明

本改编为个人非商业作品，与 OpenAI、Codex、CHROMANCE、Mili 及下列素材作者没有从属或合作关系，也未经认可。发布含 AI 辅助素材的版本时应明确说明。本版配乐为 CHROMANCE《Wrap Me In Plastic》，音乐和歌词不在代码许可范围内，也不随仓库分发。下文的 Mili 资料用于保留上游项目的来源与说明。

---

本仓库的代码按 [LICENSE](LICENSE)（MIT）发布。下面这些不属于那份许可，各自保留原来的许可和权利。

This licence covers the code in this repository (the .py, .mjs and .html files
written for this film). It does not cover the third-party material listed in
NOTICE.md, which keeps its own licence: the whale maid artwork and everything
derived from it (CC BY-NC-SA 4.0), the dsh web frontend files (MIT, DeepSeek),
and the fonts (SIL Open Font License). The song and its lyrics are not part of
this repository.

## 鲸鱼娘立绘与表情（CC BY-NC-SA 4.0）

以下保留上游素材的署名与许可范围。已由 GPT 角色图重建的头像、动作帧及封面属于上面的 GPT 素材说明，不属于此处列出的鲸鱼娘派生图。

- **文件**：
  - `film/third_party_references/whale_maid_expanded_20260926/`：`maid-left.webp` 和 `expressions/whale-*.webp`；
  - 由这些图生成的全部画面：`film/pv_dsh_frontend_20260927/avatars/`、`mem_sprites/`；
  - 构建时生成的替身舞者帧；
  - 成片里所有她的形象。
- **署名链**（按 CC BY-NC-SA 4.0 保留完整创作链）：
  1. 角色原作：溟月 © 上善无形（https://www.pixiv.net/users/62155430 ，https://space.bilibili.com/4456176 ）
  2. 女仆版设计：ZipZipPipe（https://www.pixiv.net/users/18604994 ，https://space.bilibili.com/4168597 ）
  3. 立绘：Small-tailqwq / dsh-deep-whale
  4. 八种表情：dsh-whale-galgame（https://github.com/JAdpp/dsh-whale-galgame ）
- **上游原文**：见同目录 `sources/` 里的 NOTICE。许可全文：[LICENSES/CC-BY-NC-SA-4.0.txt](LICENSES/CC-BY-NC-SA-4.0.txt)。
- **作者本人说明**：ZipZipPipe 的 [Pixiv《AI娘化》原帖](https://www.pixiv.net/artworks/148186519)要求署名、非商用，并说明 DeepSeek 娘遵循上善的 CC BY-NC-SA 4.0；2026-09-30 经 Pixiv 公开接口核实。此条款不能推广到该作者其他角色。证据范围见 [docs/ASSET_SOURCES.md](docs/ASSET_SOURCES.md)。
- **本项目的改动**：裁切、缩放、像素化、调色、表情/头像合成、记忆卡片，以及从立绘制作的节拍摆动替身与字符网格。
- **含义**：
  - 使用、改编时保留上面的署名链；
  - 不得商用；
  - 改编作品按同一许可分享。
- 视频中由这些素材改编的部分按 CC BY-NC-SA 4.0 分享。音乐、未包含的 MMD 模型和动作、商标等不因此被重新许可。

## dsh 前端（MIT，Copyright (c) 2026 DeepSeek）

- **文件**：
  - `film/vendor/dsh-web-frontend/`：`@deepseek-ai/dsh-web-frontend` 的两份 CSS 和 index JS，以及它的 `LICENSE`、`package.json`。窗口页面里的图标 SVG 取自这份 JS，`disclosure_map.json` 里的类名也是从它解析出来的。
  - `film/vendor/dsh-client-ui-cordis/`：`@deepseek-ai/dsh-client-ui-cordis` 的 `lib/client.js`，以及它的 `LICENSE`、`package.json`。E 组的 Cordis 行和面板样式从这里读取。
  - `film/pv_dsh_frontend_20260927/dsh_components.css`：从 `@deepseek-ai/dsh-client-ui-*` 的七个包（theme、chat、tool、conversation、message-feedback、deliverables、layout）里抽出的组件样式。这几个包同样是 MIT，Copyright (c) 2026 DeepSeek。
- 这些文件都按各自包的 MIT 许可分发。
- MIT 许可不包括商标：DeepSeek 的名称和标识归其权利人所有。

### 前端 bundle 内的 React 组件

`film/vendor/dsh-web-frontend/dist/assets/index-DuF6ti6g.js` 还包含 React、React JSX runtime、React DOM 和 scheduler 的代码，保留了 Facebook, Inc. and its affiliates 的 MIT 许可标头。对应许可全文另存为 [LICENSES/React-MIT.txt](LICENSES/React-MIT.txt)。DeepSeek 的署名不替代这些上游署名。

## 字体（SIL Open Font License 1.1）

- **文件**：`film/ai_mascot_mv_world_execute_20260926/fonts/`，是 Space Mono Bold 和 Anton Regular。许可文本就在同目录的 `OFL_*.txt`。
- 代码另外用到 Windows 自带的 Consolas、微软雅黑和 Segoe UI Symbol。这些字体**不在**本仓库里，见 [docs/FONTS.md](docs/FONTS.md)。

## 不在本仓库里的

| 东西 | 权利人 | 怎么获得 |
|---|---|---|
| 歌曲 world.execute(me); | Mili | 自备音频，放到 `input/song.mp3`，见 [input/README.md](input/README.md) |
| 歌词 | 歌词作者（Mili） | 构建时由 `tools/lyrics.py fetch` 从 LRCLIB（https://lrclib.net ，条目 36914646）下载到你的本机，或自备 LRC。本仓库只保存不含文字的逐词时间 |
| 原片里的舞者画面 | 基于第三方 MMD 模型和动作生成，AI 参考和衍生画面分发的许可范围尚未确认 | 构建时用鲸鱼娘立绘生成替身帧，见 [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) §舞者 |

音乐按 [Mili 官方使用指引](https://projectmili.com/copyright-guidelines)处理：个人非商业二创可按指引使用；全部或部分含 AI 的同人内容须明确标注。商业用途另行确认。本仓库不授予音乐或歌词的再许可。

## 声明

- 这是非官方同人作品，与 DeepSeek、Mili 及上面列出的各位作者没有从属或合作关系，也未经他们认可。
- 界面致敬 DeepSeek Harness（dsh）的前端。
