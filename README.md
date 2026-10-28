# 阿牧 · Amu

一只机警、亲人、动作柔和的德牧动画宠物。黑棕毛色、琥珀色眼睛和蓝色项圈，陪你安静工作。

A gentle animated German Shepherd companion, with nine animation states and sixteen look directions. AI-generated sticker artwork with transparent sprite assets.

![阿牧的舒缓动作](previews/gentle-actions.gif)

## 直接使用

- [透明精灵图](assets/spritesheet.png)：1536 × 2288 PNG，v2 布局，73 个有效帧。
- [九种动作预览](previews/all-states.gif) · [MP4](previews/all-states.mp4)
- [全部动作图](previews/contact-sheet.png) · [十六方向图](previews/directions.png)
- [动作和帧时长](pet.json) · [精灵图格式](docs/SPRITE_FORMAT.md)

将精灵图作为素材导入支持对应布局的应用。支持 ChatGPT Pets 的环境中，可以把本仓库的 `assets/spritesheet.png` 提供给 Pets 插件，要求验证并创建宠物，然后选择启用。具体导入能力取决于所用客户端；本仓库本身不调用账号 API。

## 动作

| 状态 | 内容 | 帧数 |
| --- | --- | ---: |
| idle | 呼吸、眨眼 | 6 |
| running-right | 向右移动 | 8 |
| running-left | 向左移动 | 8 |
| waving | 低位伸爪、轻轻握手 | 4 |
| jumping | 轻跳、落地 | 5 |
| failed | 垂耳、小失落 | 8 |
| waiting | 抱爪期待、微微歪头 | 6 |
| running | 专注嗅探 | 6 |
| review | 观察、浅浅点头 | 6 |

这里的 `running` 表示工作中的状态。播放时长记录在 `pet.json`，舒缓版本通过减小姿态变化、保持身体稳定来改善衔接。

## 文件

```text
assets/spritesheet.png   最终透明图集
assets/source/           生成源图、动作条和方向条
previews/               GIF、MP4、静帧和动作表
prompts/                生成与修正提示词
validation/             清理本机路径后的验证记录
docs/                   格式与来源说明
pet.json                可移植的布局及播放时长
SHA256SUMS              文件校验值
```

所有动作 GIF 均从最终图集裁切得到。源图含可移除的洋红背景，最终图集背景透明。提示词和源图用于理解或继续创作；随机生成不能保证逐像素复现。[来源、制作过程与已知限制](docs/PROVENANCE.md) 记录了实际验证范围。

## 许可

本仓库内的素材、文档和提示词使用 [MIT License](LICENSE)。图像由 OpenAI 内置 ImageGen 生成，随后进行了背景移除、裁切、排列和边缘清理。仓库不包含 Pets 插件实现或其配套脚本，也不代表 OpenAI 官方作品。
