---
name: chengfeng-video-fish
description: Install the chengfeng-video-fish (成峰 Fish 配音) skill for supported Agent environments.
---

# chengfeng-video-fish

This is the installer package for `chengfeng-video-fish`（成峰 Fish 配音）.

Install it with:

```sh
npx -y github:Agentchengfeng/chengfeng-video-fish install
```

The installed skill voices a Chinese voiceover script with the official Fish Audio TTS API, segment by segment; aligns every character's timing with a local whisper.cpp model and flags swallowed or extra words; joins the segments, shortens long pauses by punctuation, speeds the whole track up, checks the speaking rate, and outputs the final audio plus a per-character timeline for syncing visuals.
