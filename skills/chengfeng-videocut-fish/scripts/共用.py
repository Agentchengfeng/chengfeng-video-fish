# 各脚本共用：配置、读写、时长、whisper 模型
import json, os, re, subprocess, sys

配置目录 = os.path.expanduser("~/.chengfeng-videocut-fish")
PUNCT = set("，。？！：；、“”‘’（）《》…—,.?!:;\"'()")
END = set("。？！?!…")
COMMA = set("，、；：,;:—")


def 配置():
    p = os.path.join(配置目录, "config.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def key():
    k = os.environ.get("FISH_API_KEY", "").strip() or str(配置().get("fish_api_key", "")).strip()
    if not k:
        sys.exit("没有 Fish Audio 的 API key。去 https://fish.audio/app/developers/get-started/ 开一把，然后：\n"
                 "  export FISH_API_KEY=你的key\n"
                 f"或写进 {配置目录}/config.json：{{\"fish_api_key\": \"你的key\"}}")
    return k


def 读(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def 写(p, o):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)


def 时长(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


def whisper模型():
    """返回 (模型文件, -dtw 用的名字)。默认 ~/.cache/whisper/ggml-small.bin。"""
    p = os.path.expanduser(配置().get("whisper_model") or "~/.cache/whisper/ggml-small.bin")
    if not os.path.exists(p):
        sys.exit(f"找不到 whisper 模型 {p}。下载：\n  mkdir -p ~/.cache/whisper && curl -L -o ~/.cache/whisper/ggml-small.bin "
                 "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin")
    m = re.search(r"ggml-(.+?)\.bin$", os.path.basename(p))
    名 = (m.group(1) if m else "small").replace("large-", "large.").replace("-turbo", ".turbo").replace("-q5_0", "").replace("-q8_0", "")
    return p, 名


def 段落(W):
    p = os.path.join(W, "段落.json")
    if not os.path.exists(p):
        sys.exit(f"{W} 里没有 段落.json：先跑 分段.py")
    return 读(p)


def 选段(段们, 参数):
    """--段 s01,s03 → 只要这几段"""
    if "--段" not in 参数:
        return 段们
    i = 参数.index("--段"); 要 = set(参数[i + 1].split(",")); del 参数[i:i + 2]
    没有 = 要 - {d["id"] for d in 段们}
    if 没有:
        sys.exit("没有这些段：" + "、".join(sorted(没有)))
    return [d for d in 段们 if d["id"] in 要]
