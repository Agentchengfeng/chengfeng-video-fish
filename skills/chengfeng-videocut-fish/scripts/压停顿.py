# 第 5 步：长停顿按标点压到一档一档的长度，再整体加速，出成品口播和成品时间线
# 用法：python3 压停顿.py <工作目录> [--rate 1.3] [--tiers 0.3,0.4,0.55,0.7] [--keep 0.3]
#   读 口播-原速.wav、时间线-原速.json → 写 口播.wav（成品）、时间线.json（成品，单位是成品里的秒）
# 分档（成品秒）：本来不超过 --keep 的停顿不动、不补长；更长的按停顿前的标点定长度，--tiers 依次是
#   句内、逗号类（，、；：—）、句末（。？！…）、换段（## 段之间）。片头留 0.15 秒、片尾留 0.2 秒。
#   静音标准：低于 -45 dB、长过 0.05 秒。
# 默认值是作者拿自己一条 Fish 配音试出来的：1.3 倍时 328 字/分、停顿 12%、开头 30 秒 312 字/分。
import json, os, re, subprocess, sys, tempfile
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 共用 as g

参 = sys.argv[1:]
def 取(名, conv, 默认):
    if 名 not in 参: return 默认
    i = 参.index(名); v = conv(参[i + 1]); del 参[i:i + 2]; return v
RATE = 取("--rate", float, 1.3)
T_IN, T_COMMA, T_END, T_SEG = 取("--tiers", lambda s: tuple(map(float, s.split(","))), (0.3, 0.4, 0.55, 0.7))
KEEP = 取("--keep", float, 0.3)
HEAD, TAIL = 0.15, 0.2
if len(参) != 1: sys.exit("用法：python3 压停顿.py <工作目录> [--rate 1.3] [--tiers 句内,逗号,句末,换段] [--keep 0.3]")
W = 参[0]
SRC, MID, DST = (os.path.join(W, x) for x in ("口播-原速.wav", "口播-压停顿-原速.wav", "口播.wav"))
tl = g.读(os.path.join(W, "时间线-原速.json"))
dur = g.时长(SRC)
K = KEEP * RATE                                   # 原速下“不动”的上限
log = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", SRC, "-af", "silencedetect=noise=-45dB:d=0.05", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
if len(en) < len(st): en.append(dur)

toks = [(w["s"], w["e"], w["t"], s["seg"]) for s in tl["sentences"] for w in s["words"]]   # 标点 s=e，挂在前一个字后面
seg_bounds = [x["end"] for x in tl["segments"][:-1]]
def kind(a, b):
    if any(a - 0.05 <= x <= b + 0.05 for x in seg_bounds) or any(abs(x["start"] - b) < 0.6 and x["start"] > a for x in tl["segments"][1:]):
        return "换段"
    prev = [k for k, t in enumerate(toks) if t[1] <= a + 0.08 and t[2].strip() and t[2] not in g.END | g.COMMA]
    if not prev: return "片头"
    p, j = "", prev[-1] + 1
    while j < len(toks) and toks[j][2] in g.END | g.COMMA | set("”’）)》"): p += toks[j][2]; j += 1
    if set(p) & g.END: return "句末"
    if set(p) & g.COMMA: return "逗号"
    return "句内"

plan = []
for a, b in zip(st, en):
    if a <= 0.001: plan.append((a, b, HEAD * RATE, "片头")); continue
    if b >= dur - 0.001: plan.append((a, b, TAIL * RATE, "片尾")); continue
    if b - a <= K: continue
    c = kind(a, b)
    plan.append((a, b, {"句内": T_IN, "逗号": T_COMMA, "句末": T_END, "换段": T_SEG}.get(c, T_IN) * RATE, c))

chunks, pads, t, head_pad, tail_done = [], [], 0.0, 0.0, False   # 说话块 + 目标长度的静音（两边各留一点原静音，防切掉轻音）
for a, b, L, c in plan:
    m = min(0.06, L / 2, (b - a) / 2)
    if c == "片头": t = max(b - m, 0); head_pad = L - m; continue
    chunks.append((t, a + m)); pads.append(max(L - 2 * m, 0)); t = b - m
    if c == "片尾": tail_done = True
if not tail_done: chunks.append((t, dur)); pads.append(0)
F = 0.006
fl = [f"[0:a]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS,afade=t=in:d={F},afade=t=out:st={max(b - a - F, 0):.4f}:d={F},apad=pad_dur={pads[k]:.4f}[k{k}]"
      for k, (a, b) in enumerate(chunks)]
fl.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{max(head_pad, 0.001):.4f}[h]")
fl.append("[h]" + "".join(f"[k{k}]" for k in range(len(chunks))) + f"concat=n={len(chunks) + 1}:v=0:a=1[o]")
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f: f.write(";".join(fl)); fs = f.name
try:
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", SRC, "-filter_complex_script", fs, "-map", "[o]",
                    "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", MID], check=True)
finally:
    os.unlink(fs)
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", MID, "-filter:a", f"atempo={RATE}", "-c:a", "pcm_s16le", DST], check=True)

starts, acc = [], head_pad          # 原速时间 → 成品时间
for k, (a, b) in enumerate(chunks): starts.append(acc); acc += (b - a) + pads[k]
def mp(t):
    for k, (a, b) in enumerate(chunks):
        if t < a: return round(starts[k] / RATE, 3)
        if t <= b: return round((starts[k] + t - a) / RATE, 3)
    return round(acc / RATE, 3)
for x in tl["segments"]: x["start"], x["end"] = mp(x["start"]), mp(x["end"])
for s in tl["sentences"]:
    s["start"], s["end"] = mp(s["start"]), mp(s["end"])
    for w in s["words"]: w["s"], w["e"] = mp(w["s"]), mp(w["e"])
cnt = Counter(c for *_, c in plan)
tl["压停顿"] = {"rate": RATE, "tiers": [T_IN, T_COMMA, T_END, T_SEG], "keep": KEEP, "各类处数": dict(cnt)}
g.写(os.path.join(W, "时间线.json"), tl)
print("压到档位的停顿", dict(cnt), f"| 本来不超过 {KEEP} 秒的没动")
print(f"原速 {dur:.2f} 秒 → 成品 {acc / RATE:.2f} 秒（{RATE} 倍）→ 口播.wav、时间线.json")
print("下一步：python3 语速.py " + W)
