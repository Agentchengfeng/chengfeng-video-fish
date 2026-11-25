---
name: chengfeng-videocut-fish
description: Fish 配音：把写好的中文口播稿交给 Fish Audio 官方接口自动配音，一段一段配；再用本机 whisper 对上逐字时间、查吞字，拼成一条，长停顿按标点压短、整体加速，查语速，交出成品口播 wav 和逐句逐字的时间线（给画面卡点用）。要一把 Fish Audio 的 API key 和一个声音 ID，加上 python3、ffmpeg、whisper.cpp。用户说用 Fish 配音、AI 配口播、把口播稿配成声音、自动配音时使用。不写稿；自己录的口播要剪，用 chengfeng-videocut-koubo。
---

# Fish 配音

从一份口播稿到能直接放进视频的配音，六步一线。所有东西都写在**工作目录**里（默认在稿子旁边，叫 `<稿子名>-配音/`）。脚本都在本 skill 的 `scripts/` 里，下面写 `S=<本 skill 目录>/scripts`。

```text
1 分段     口播稿 → 一段一段（## 段名）                 分段.py
2 配音     调 Fish Audio 官方接口，一段一个 mp3          配音.py    付费
3 对齐     whisper 对上逐字时间，查吞字、多念            对齐.py
4 拼接     拼成一条原速口播和时间线                      拼接.py
5 压停顿   长停顿按标点压短，整体加速                    压停顿.py
6 查语速   全片字/分、停顿占比、开头 30 秒               语速.py
```

**每一步的完成判据是它的产出文件**，没出文件不算做完。用户只在两处说话：开配前点头（花钱）；拿到成品后说哪里要改。

## 0. 准备

- `python3`（3.8 以上，只用标准库）、`ffmpeg` / `ffprobe`、`whisper-cli`（macOS：`brew install ffmpeg whisper-cpp`）。缺了告诉用户怎么装，不替用户装。
- whisper 模型：默认 `~/.cache/whisper/ggml-small.bin`，没有就告诉用户下载：`mkdir -p ~/.cache/whisper && curl -L -o ~/.cache/whisper/ggml-small.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin`。换模型写进 config 的 `whisper_model`。
- Fish Audio 的 API key：环境变量 `FISH_API_KEY`，或 `~/.chengfeng-videocut-fish/config.json` 里的 `fish_api_key`。没有就停下，告诉用户去 https://fish.audio/app/developers/get-started/ 开一把，API 余额在 https://fish.audio/app/developers/billing/ 充。key 不打印、不写进别的文件。
- 声音 ID：config 的 `voice_id`，或每次 `--voice`。用户在 fish.audio 上挑好声音（或自己克隆一个），把它的 ID（32 位字母和数字）给你。
- 模型：config 的 `model`，没写用 `s2.1-pro`（官方推荐的正式模型）。官方还有免费的 `s2.1-pro-free`，适合先试。
- 想改别的接口参数（`temperature`、`prosody` 等），写在 config 的 `"tts": {…}` 里，字段名照官方文档。

## 1. 分段

```sh
python3 $S/分段.py <口播稿.md>
```

- 口播稿用 `## 段名` 分段，一段 15–35 秒（约 80–180 字）。没有 `##` 就按空行分，再合到每段约 150 字。
- `【】` 里的字不念：放在画面上的字、提示词、网址都这样标。
- 改了稿子再跑一次：哪段的字变了，它的旧音频会删掉，下一步只重配它。

## 2. 配音（付费）

先算钱：

```sh
python3 $S/配音.py <工作目录> --只算
```

把“要配几段、多少字节、用哪个模型”和官方价格页 https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits 告诉用户（按输入文字的 UTF-8 字节计费），**用户点头再配**：

```sh
python3 $S/配音.py <工作目录>
```

- 已经有 mp3 的段跳过；只重配某几段：`--段 s03,s05 --重配`。
- 报错照屏幕上的话处理：401 是 key 不对，402 是 API 余额不够，400/404 多半是声音 ID 或模型名写错。429 和 5xx 脚本会自己等着重试。

## 3. 对齐：对上逐字时间，查吞字

```sh
python3 $S/对齐.py <工作目录>
```

Fish 接口只给音频，不给每个字的时间。脚本用本机 whisper 识别出每个字的时刻，再按原稿逐字对齐；识别错的字用原稿的字，时间按前后插值。

最后列出的“要人看一眼的段”逐个处理：

- whisper 自己也会认错，可疑不等于真的吞字。能听就听那一段；听不了，看“对不上”的是不是整个词没了，连着好几个字整段没了多半是真吞。
- Fish 整段念时偶尔会吞掉重复出现的短句。真吞了就重配那一段：`python3 $S/配音.py <工作目录> --段 s03 --重配`，再跑一次对齐。
- 没听过的，交付时照实说“没人耳听过”。

## 4. 拼接

```sh
python3 $S/拼接.py <工作目录>
```

段与段之间留 0.4 秒气口（`--gap` 可改），出 `口播-原速.wav` 和 `时间线-原速.json`。

## 5. 压停顿、加速

```sh
python3 $S/压停顿.py <工作目录>
```

- 本来不超过 0.3 秒的停顿不动；更长的按停顿前的标点压到一档一档：句内 0.3、逗号 0.4、句末 0.55、换段 0.7 秒（成品里的秒）。再整体 1.3 倍。
- 用户不要加速：`--rate 1`；要换档位：`--tiers 句内,逗号,句末,换段`。
- 出 `口播.wav`（成品）和 `时间线.json`（成品里的秒）。

## 6. 查语速

```sh
python3 $S/语速.py <工作目录>
```

默认标准：全片 290–330 字/分，停顿占比不超过 15%，开头 30 秒不低于 300 字/分。用户有自己的标准，用 `--范围`、`--停顿`、`--开头` 换。没过就调 `--rate` 或 `--tiers` 重跑第 5、6 步，调了什么告诉用户。

## 交付

给用户三样：`口播.wav`、`时间线.json`、`语速.txt`。报告写：几段、成品多长、语速三项、可疑段怎么处理的、有没有人耳听过。

`时间线.json` 的格式：`segments` 每段起止；`sentences` 每句的起止和文字，`words` 里每个字（标点也在，起止相同）的 `t` 文字、`s` 开始秒、`e` 结束秒。画面按它卡点。

## 改稿

改口播稿 → 重跑第 1 步（只有字变了的段会删旧音频）→ 第 2 步只配缺的 → 第 3–6 步。

## 来源

- 配音这一步调的是 Fish Audio 官方 TTS 接口（`POST https://api.fish.audio/v1/tts`），写法照官方文档：https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech 。
- 对时间用 whisper.cpp（https://github.com/ggml-org/whisper.cpp）的 DTW 逐字时间。
- 分段、对齐、压停顿、查语速是作者自己做讲解视频的做法。
