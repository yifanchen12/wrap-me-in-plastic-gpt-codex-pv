# Wrap Me In Plastic · GPT × Codex 像素 PV

如果 GPT 是她，Codex 就是承载她的代码世界。

这是基于 [MisakaZentai/world-execute-me-dsh-pv](https://github.com/MisakaZentai/world-execute-me-dsh-pv) 的个人非商业二创。保留原项目的代码动画、镜头组织和前端截图方式，将角色与界面改为 GPT 白龙娘 / 6-Astra / Codex，并适配 CHROMANCE 的《Wrap Me In Plastic》。本项目没有调用即梦视频生成服务；角色动作由 AI 生成的关键姿势图、像素拼帧及代码变形组成。

![封面](docs/gpt-cover.png)

## 原作者署名

- 原视频 UP：**西西弗斯的风车**。
- 原视频标题：**〖4K〗如果聊天窗口就是她的整个世界 —— world.execute(me)**。
- 原视频：[BV1xCai6aE9g](https://www.bilibili.com/video/BV1xCai6aE9g/)。
- 原 PV 开源项目作者：**MisakaZentai**；代码按 MIT 使用，完整原作者版权声明保留在 [LICENSE](LICENSE)。
- 原作简介注明的灵感来源：野生大K《GPT6-Astra眼中的world.execute(me)》（BV1Jwhy6BEMJ）。
- 本版改编与发布：[yifanchen12](https://github.com/yifanchen12)。

原视频 UP 与代码作者分别署名；这里不推断两者是否为同一人。本版配乐为 CHROMANCE《Wrap Me In Plastic》，原作的 Mili 配乐没有被混入本版。

## 本版改动

- GPT 白龙娘角色、白龙字符轮廓和灰白终端配色。
- GPT 风格输入框、折叠思考状态和 6-Astra 模型标识。
- 头像由随机像素逐级细化为清晰的角色轮廓。
- 7 张角色动作图经镜像与编排组成 12 个关键姿势槽位，呈现踏步、摆臂、侧身转动、伸手和安静收尾；动作帧同时供点云、样本格、特征图、字符人物等镜头使用。
- 使用目标歌曲与自备 LRC 生成底部歌词条；原作镜头时钟线性映射到目标歌曲时长。
- 片尾文案：让想象成为现实。

画面中的训练、参数、模型规格和代码日志均为剧情视觉，不代表 OpenAI 的内部实现。全片镜头仍沿用原作叙事框架；本版不是每个镜头都按新歌词重新创作。

## 快速开始

环境：Python 3.12+、Node 20+、FFmpeg / FFprobe、Windows 字体。其他系统的字体替代方式见 [docs/FONTS.md](docs/FONTS.md)。

```powershell
pip install -r requirements.txt
npm install
npx playwright install chromium
# 将自己的完整歌曲放到 input/song.mp3
# 将与歌曲对应的 UTF-8 LRC 放到 input/lyrics.lrc
python build_gpt.py --workers 4
```

FFmpeg 和 FFprobe 需要在 PATH 中，或自行放到 `tools/ffmpeg/bin/`。本仓库不分发这些可执行程序。

默认输出：`out/publish/投稿成片-GPT-Codex-动画增强版.mp4`，1920×1080、24 fps。场景按 1280×720 渲染，再上采样到 1080p；这不等同于原生 4K。

```powershell
# 只制作 12 秒预览，预览镜头和正式版使用相同的时钟映射
python build_gpt.py --duration 12 --output out/preview.mp4
# 已有截图和角色缓存时，只重新渲染
python build_gpt.py --skip-pages --skip-dancer
```

原作的镜头编排依赖其逐词时间，首次构建会通过上游工具从 LRCLIB 下载原作 LRC 到 `input/source-world-execute.lrc`，只在本机重建时间缓存。目标歌曲的 LRC 保存在 `input/lyrics.lrc`，两份文件不会互相替换，也不随本仓库分发。

## 角色动作如何制作

`assets/gpt-dance-atlas.png` 是 4 列 × 3 行的透明角色动作图集，由 7 张角色图组成，来源及镜像配置见 `assets/gpt-dance-atlas.sources.json`。`tools/gpt_sprite_dance.py` 拆分并对齐脚底位置，按动作编排拼接关键姿势，逐像素切换形状，加上节拍起伏、衣摆和头发的变形，再沿用原项目的描线工具生成 70×45 字符网格及 420×540 RGBA 帧。这是为像素终端画面设计的关键帧动画，不等同于完整三维骨骼舞蹈。

生成的 27 个动作缓存沿用上游的文件名和帧数，因此 `pv_full.py`、`h3_full.py` 及后续点云 / 卷积 / 采样等效果可以直接读取。原版未公开的 MMD 舞蹈帧不包含在本项目里。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `build_gpt.py` | 本版构建入口 |
| `tools/gpt_sprite_dance.py` | 图片关键帧拼接、像素舞者和缓存生成 |
| `tools/wrap_me_project.py` | 目标歌曲时钟、歌词条和整片渲染 |
| `assets/` | GPT 角色参考派生图、动作图集 |
| `film/pv_dsh_frontend_20260927/` | GPT 聊天窗口、HTML 页面和截图合成 |
| `film/tui_pv_world_execute_20260926/` | 保留并改编的原项目场景、像素效果和转场代码 |
| `film/vendor/` | 保留原许可的 dsh 前端文件 |
| `docs/` | 原项目原理、字体说明与本版构建说明 |

歌曲、歌词、渲染输出、生成缓存、浏览器、FFmpeg、账号配置和令牌均不随代码仓库分发。

## 许可与素材说明

- 代码：MIT。保留 MisakaZentai 与其他代码来源的版权及许可声明。
- 保留的上游鲸鱼娘素材：CC BY-NC-SA 4.0，署名链见 [NOTICE.md](NOTICE.md)；本版角色渲染不使用这些素材。
- dsh 前端：MIT，Copyright (c) 2026 DeepSeek；React 及字体等原许可保留。
- GPT 角色素材与封面：由本版提供的可用参考经 AI 辅助生成，不适用代码的 MIT 许可，未授予额外的美术再许可。需要再使用角色素材时请联系本版作者确认。
- 音乐与歌词：权益归各自权利人，本仓库不提供音频、歌词或相关授权。

本版含 AI 生成内容，为个人非商业、非官方同人作品，与 OpenAI、DeepSeek、CHROMANCE、Mili 官方无从属或合作关系。
