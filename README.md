# 成峰 Fish 配音 chengfeng-video-fish

> 写好的中文口播稿，交给 AI 用 Fish Audio 配成声音：一段一段配，对上每个字的时间，查吞字，压停顿、查语速，交出能直接放进视频的口播和时间线。

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

用 AI 配讲解视频的口播，配出来往往不能直接用：整段念会吞字，停顿偏长，语速偏慢；画面要卡到字上，还得知道每个字在第几秒。

成峰 Fish 配音是一个给 Claude Code / Codex 等 Agent 用的 Skill。AI 把口播稿拆成一段一段，调 Fish Audio 官方接口配音；再用本机的 whisper 识别出每个字的时间，跟原稿逐字对齐，顺手查出可能吞掉、多念的地方；然后拼成一条，长停顿按标点压短、整体加速，查一遍语速。最后交给你一条成品口播，和一份逐句逐字的时间线。

## 来源

- **配音**：调的是 Fish Audio 官方 TTS 接口（`POST https://api.fish.audio/v1/tts`），写法照官方文档：<https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech>。用你自己的 Fish Audio 账号和 API key，费用按 Fish Audio 官方价格：<https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits>。作者平时在 Fish 网页上配音，接口这一步没有用作者的账号实测过。
- **对时间**：用 [whisper.cpp](https://github.com/ggml-org/whisper.cpp) 在本机识别，取它的 DTW 逐字时间。
- **分段、对齐、压停顿、查语速**：作者自己做讲解视频的做法，拿作者真实的 Fish 配音测过。

## 需要什么

- `python3` 3.8 以上（只用标准库）
- `ffmpeg` / `ffprobe`、`whisper-cli`（macOS：`brew install ffmpeg whisper-cpp`）
- whisper 模型 `ggml-small.bin`：

  ```sh
  mkdir -p ~/.cache/whisper && curl -L -o ~/.cache/whisper/ggml-small.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
  ```

- 一把 Fish Audio 的 API key（在 <https://fish.audio/app/developers/get-started/> 开，API 余额在 <https://fish.audio/app/developers/billing/> 充），和一个声音 ID（在 fish.audio 上挑好的声音，或你自己克隆的）
- Node.js 18+（只有一键安装要用）

## 安装

最简单的方式：把这句发给你的 AI，它会照着命令装好：

```text
帮我运行这条命令，安装成峰 Fish 配音 Skill：npx -y github:Agentchengfeng/chengfeng-video-fish install
```

自己在终端装也行：

```sh
npx -y github:Agentchengfeng/chengfeng-video-fish install
```

再配好 key 和声音：

```sh
mkdir -p ~/.chengfeng-video-fish && echo '{"fish_api_key": "你的key", "voice_id": "你的声音ID"}' > ~/.chengfeng-video-fish/config.json
```

装好后重启 Agent，让它重新加载 Skill 列表。

## 怎么用

直接说：

```text
用 Fish 把这份口播稿配成声音：~/视频/口播稿.md
```

口播稿用 `## 段名` 分段，一段 15–35 秒；放在画面上、不用念的字写在 `【】` 里。

它会一步步做：

1. **分段**：一段配一次，改稿后只重配改了的段。
2. **配音**：先算好要配多少字节、用哪个模型，你点头再调接口。
3. **对齐**：每个字对上时间，列出可能吞字、多念的段，真吞了就重配那一段。
4. **拼接**：拼成一条，段与段之间留一点气口。
5. **压停顿**：长停顿按前面的标点压到一档一档，再整体加速。
6. **查语速**：全片字/分、停顿占比、开头 30 秒，没过就调了重来。

## 出来什么

所有东西都在稿子旁边的 `<稿子名>-配音/` 文件夹里：

| 文件 | 是什么 |
|---|---|
| `口播.wav` | 成品口播 |
| `时间线.json` | 逐段、逐句、逐字的起止时间（成品里的秒），画面照它卡点 |
| `语速.txt` | 语速三项 |
| `段/` | 每段的稿子、配音、对齐结果 |

## 不做什么

- 不写稿。
- 不剪你自己录的口播：那个用 [成峰剪口播](https://github.com/Agentchengfeng/chengfeng-video-koubo)。
- 没人听过的地方，报告里写“没人耳听过”，不写成“没问题”。

## 检查与卸载

```sh
npx -y github:Agentchengfeng/chengfeng-video-fish doctor
npx -y github:Agentchengfeng/chengfeng-video-fish uninstall
```

`doctor` 会查 Skill 装好没有，python3、ffmpeg、whisper、模型和 Fish key 在不在（只看有没有，不打印 key）。包里只有说明文件和脚本，不含 API key 或任何个人数据。

## 脚本也能单独用

```sh
S=~/.claude/skills/chengfeng-video-fish/scripts
python3 $S/分段.py 口播稿.md                  # → 口播稿-配音/
python3 $S/配音.py 口播稿-配音 --只算          # 先看要花多少
python3 $S/配音.py 口播稿-配音
python3 $S/对齐.py 口播稿-配音
python3 $S/拼接.py 口播稿-配音
python3 $S/压停顿.py 口播稿-配音               # 默认 1.3 倍，--rate 1 不加速
python3 $S/语速.py 口播稿-配音
```

## 仓库结构

```text
chengfeng-video-fish/
├── SKILL.md
├── LICENSE / NOTICE.md / CITATION.cff
├── package.json
├── bin/install.js
└── skills/chengfeng-video-fish/
    ├── SKILL.md
    ├── 更新日志.md
    ├── agents/openai.yaml
    └── scripts/               # 分段、配音、对齐、拼接、压停顿、语速
```

## 官方来源

由 **成峰 / AI产品自由** 创建和维护。

- GitHub：[Agentchengfeng](https://github.com/Agentchengfeng) —— 安装问题和 bug 请提 Issue。
- X：[@chengfeng240928](https://x.com/chengfeng240928)
- 小红书 / 公众号 / B站 / 抖音 / 视频号：AI产品自由

## License

Apache-2.0。见 [LICENSE](LICENSE) 和 [NOTICE.md](NOTICE.md)。使用、翻译、转载或改编时，请保留署名与 NOTICE。
