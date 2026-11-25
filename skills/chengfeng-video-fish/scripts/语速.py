# 第 6 步：查成品口播的语速
# 用法：python3 语速.py <工作目录> [--范围 290,330] [--停顿 0.15] [--开头 300]
#   读 口播.wav、时间线.json。字数：中文一字算 1，英文单词、一串数字各算 1。停顿：0.3 秒以上、低于 -45 dB 的静音。
# 默认标准是作者对齐自己真人口播定的：全片 290–330 字/分，停顿占比不超过 15%，开头 30 秒不低于 300 字/分。
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 共用 as g

参 = sys.argv[1:]
def 取(名, conv, 默认):
    if 名 not in 参: return 默认
    i = 参.index(名); v = conv(参[i + 1]); del 参[i:i + 2]; return v
LO, HI = 取("--范围", lambda s: tuple(map(float, s.split(","))), (290, 330))
PAUSE_MAX = 取("--停顿", float, 0.15)
HEAD_MIN = 取("--开头", float, 300)
if len(参) != 1: sys.exit("用法：python3 语速.py <工作目录> [--范围 290,330] [--停顿 0.15] [--开头 300]")
W = 参[0]
TOK = re.compile(r"[一-鿿]|[A-Za-z]+|\d+(?:\.\d+)?")
n = lambda s: len(TOK.findall(s))
tl = g.读(os.path.join(W, "时间线.json")); VOICE = os.path.join(W, "口播.wav")
chars = sum(n(s["text"]) for s in tl["sentences"])
head = sum(n(w["t"]) for s in tl["sentences"] for w in s["words"] if w["s"] < 30)
total = g.时长(VOICE)
log = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", VOICE, "-af", "silencedetect=noise=-45dB:d=0.3", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
gaps = list(zip(st, en + [total] * (len(st) - len(en))))
pause = sum(b - a for a, b in gaps)
full, head_r, ratio = chars / total * 60, head / min(30, total) * 60, pause / total
ok = lambda c: "✓" if c else "✗"
行 = [f"时长 {total:.1f} 秒，{chars} 字",
      f"全片 {full:.0f} 字/分  {ok(LO <= full <= HI)}（{LO:.0f}–{HI:.0f}）",
      f"停顿占比 {ratio:.0%}，{len(gaps)} 处  {ok(ratio <= PAUSE_MAX)}（≤{PAUSE_MAX:.0%}）",
      f"开头 30 秒 {head_r:.0f} 字/分  {ok(head_r >= HEAD_MIN)}（≥{HEAD_MIN:.0f}）"]
长 = [(a, b) for a, b in gaps if b - a >= 0.8]
if 长: 行.append("0.8 秒以上的停顿：" + "、".join(f"{int(a // 60):02d}:{a % 60:04.1f}（{b - a:.1f}s）" for a, b in 长))
print("\n".join(行))
with open(os.path.join(W, "语速.txt"), "w", encoding="utf-8") as f: f.write("\n".join(行) + "\n")
过 = LO <= full <= HI and ratio <= PAUSE_MAX and head_r >= HEAD_MIN
if not 过:
    print("没过：快了调小 --rate、慢了调大 --rate 重跑 压停顿.py；停顿多就把 --tiers 调小。")
sys.exit(0 if 过 else 1)
