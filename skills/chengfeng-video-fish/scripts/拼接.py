# 第 4 步：把各段拼成一条口播（原速），出逐句逐字时间线
# 用法：python3 拼接.py <工作目录> [--gap 0.4]      段与段之间留 --gap 秒气口
# 出：口播-原速.wav、时间线-原速.json（segments：每段起止；sentences：每句起止、文字、words 每个字 t/s/e，单位秒）
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 共用 as g

参 = sys.argv[1:]
GAP = 0.4
if "--gap" in 参: i = 参.index("--gap"); GAP = float(参[i + 1]); del 参[i:i + 2]
if not 参: sys.exit("用法：python3 拼接.py <工作目录> [--gap 0.4]")
W = 参[0]
段们 = g.段落(W)
缺 = [d["id"] for d in 段们 if not os.path.exists(os.path.join(W, "段", d["id"] + ".json"))]
if 缺: sys.exit("这些段还没配音或没对齐：" + "、".join(缺))
r3 = lambda x: round(x, 3)
out = {"segments": [], "sentences": []}; t = 0.0; ins, fl = [], []
for k, d in enumerate(段们):
    sid = d["id"]; j = g.读(os.path.join(W, "段", sid + ".json")); a = t; last = k == len(段们) - 1
    out["segments"].append({"id": sid, "段名": d["段名"], "start": r3(a), "end": r3(a + j["duration"])})
    for s in j["subtitle"]["sentences"]:
        out["sentences"].append({"seg": sid, "start": r3(a + s["start_time"] / 1000), "end": r3(a + s["end_time"] / 1000), "text": s["text"],
                                 "words": [{"t": w["text"], "s": r3(a + w["start_time"] / 1000), "e": r3(a + w["end_time"] / 1000)} for w in s["words"]]})
    ins += ["-i", os.path.join(W, "段", sid + ".wav")]
    fl.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{j['duration']},apad=pad_dur={0 if last else GAP},asetpts=PTS-STARTPTS[a{k}]")
    t = a + j["duration"] + (0 if last else GAP)
fc = ";".join(fl) + ";" + "".join(f"[a{k}]" for k in range(len(段们))) + f"concat=n={len(段们)}:v=0:a=1[o]"
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[o]", "-c:a", "pcm_s16le",
                os.path.join(W, "口播-原速.wav")], check=True)
g.写(os.path.join(W, "时间线-原速.json"), out)
print(f"拼好 {len(段们)} 段，原速 {t:.1f} 秒 → 口播-原速.wav、时间线-原速.json")
print("下一步：python3 压停顿.py " + W)
