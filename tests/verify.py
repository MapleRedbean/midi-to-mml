"""独立校验器（新版）：逐音比对 + 变速位置同步 + 文件头检查

用法: python verify.py <input.mid> <outdir> [divisions]
检查项：
  A. 每个文件头以 t{BPM}v{音量} 开头（无 MML@ 前缀）
  B. 音符逐音比对（音高/起点/时值）
  C. 变速位置：每个文件的 t 序列 == 全局变速表（位置与数值完全一致）
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from midi2mml import (action_timeline, load_midi, quantize,  # noqa: E402
                      split_voices)

EPS = 1e-6
NOTE_RE = re.compile(r"^([a-g])([\-+]?)$")


def read_len(body, i, default):
    """解析 [数字][附点] 时值，返回 (den, dots, new_i)"""
    num = ""
    while i < len(body) and body[i].isdigit():
        num += body[i]
        i += 1
    dots = 0
    while i < len(body) and body[i] == ".":
        dots += 1
        i += 1
    return (int(num) if num else default), dots, i


def parse_mml(text):
    """返回 (header, notes, tempos)；notes=[(start,dur,pitch)]，tempos=[(pos,bpm)]"""
    body = text.strip()
    header = {}
    m = re.match(r"^t(\d+)v(\d+)(?:o(\d+))?(?:l(\d+))?", body)
    if not m:
        raise ValueError(f"文件头不是 t..v.. 开头: {body[:40]!r}")
    header["t"] = int(m.group(1))
    header["v"] = int(m.group(2))
    header["o"] = int(m.group(3)) if m.group(3) else 4
    header["l"] = int(m.group(4)) if m.group(4) else 16
    body = body[m.end():]

    notes, tempos = [], []
    mcmds, pcmds = [], []
    octv, dlen, cursor = header["o"], header["l"], 0.0
    cur_bpm = header["t"]
    pending_tie = False
    i = 0
    while i < len(body):
        c = body[i]
        if c.isspace():
            i += 1
            continue
        if c in "MmPp":
            i += 1
            num = ""
            while i < len(body) and body[i].isdigit():
                num += body[i]
                i += 1
            if num:
                (mcmds if c in "Mm" else pcmds).append((cursor, f"{c.upper()}{num}"))
            continue
        if c == "t":
            i += 1
            num = ""
            while i < len(body) and body[i].isdigit():
                num += body[i]
                i += 1
            if num:
                cur_bpm = int(num)
                tempos.append((cursor, cur_bpm))
            continue
        if c == "v":
            i += 1
            while i < len(body) and body[i].isdigit():
                i += 1
            continue
        if c == "o":
            i += 1
            num = ""
            while i < len(body) and body[i].isdigit():
                num += body[i]
                i += 1
            if num:
                octv = int(num)
            continue
        if c == "l":
            i += 1
            dlen, _, i = read_len(body, i, dlen)
            continue
        if c == "<":
            octv -= 1
            i += 1
            continue
        if c == ">":
            octv += 1
            i += 1
            continue
        if c == "&":
            pending_tie = True
            i += 1
            continue
        if c == "r":
            den, dots, i = read_len(body, i + 1, dlen)
            cursor += (4.0 / den) * (1 + 0.5 * dots)
            continue
        mm = re.match(r"([a-g])([\-+]?)", body[i:])
        if mm:
            name, acc = mm.group(1), mm.group(2)
            i += mm.end()
            den, dots, i = read_len(body, i, dlen)
            dur = (4.0 / den) * (1 + 0.5 * dots)
            base = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}[name]
            semi = base + (1 if acc == "+" else -1 if acc == "-" else 0)
            pitch = (octv + 1) * 12 + semi
            if pending_tie and notes:
                st, du, p = notes[-1]
                notes[-1] = (st, du + dur, p)
            else:
                notes.append((cursor, dur, pitch))
            pending_tie = False
            cursor += dur
            continue
        raise ValueError(f"无法解析的字符 {c!r} 于 {body[max(0,i-8):i+8]!r}")
    return header, notes, tempos, mcmds, pcmds


def close(a, b, eps=1e-4):
    return abs(a - b) <= eps


def main(mid_path, outdir, default_div=4):
    tpb, tempos, tracks, meta = load_midi(mid_path)
    man_p = os.path.join(outdir, "manifest.json")
    if not os.path.exists(man_p):
        print("缺少 manifest.json")
        return 1
    man = json.load(open(man_p))
    files = man["files"]
    report = {r["file"]: r for r in man["report"]}

    errors = []
    ok = 0
    for rel in files:
        p = os.path.join(outdir, rel)
        text = open(p, encoding="utf-8").read()
        r = report[rel]
        ti, voice = r["track_index"] - 1, r["voice"]
        div = r.get("divisions") or default_div
        step = 1.0 / div

        # A. 文件头
        if not re.match(r"^t\d+v\d+", text.strip()):
            errors.append(f"{rel}: 文件头不是 t..v.. 开头")
            continue

        header, notes, ftempos, mcmds, pcmds = parse_mml(text)

        # _action.txt：只校验 M/P 时间轴
        if rel.endswith("_action.txt"):
            act_cmd = r.get("action") or "M3"
            min_rest = r.get("action_min_rest", 1.0)
            div_all = r.get("divisions") or default_div
            step_all = 1.0 / div_all
            tq = [quantize(tracks[ti].notes, step_all)]
            want_ev, _ = action_timeline(tq, tempos, act_cmd, min_rest=min_rest)
            got_ev = sorted([(round(p, 6), c) for p, c in mcmds + pcmds],
                            key=lambda x: (x[0], 0 if x[1].startswith("M") else 1))
            want_cmp = [(round(p, 6), c) for p, c in want_ev]
            if want_cmp != got_ev:
                bad = [(a, b) for a, b in zip(want_cmp, got_ev) if a != b][:3]
                errors.append(f"{rel}: M/P 时间轴不符（差异 {len(bad)} 处，如 {bad}）")
                continue
            ok += 1
            continue

        # B. 音符比对
        tr = tracks[ti]
        q = quantize(tr.notes, step)
        voices = split_voices(q)
        exp = voices[voice - 1]
        exp_t = [(n.start, n.end - n.start, n.pitch) for n in exp]
        if len(exp_t) != len(notes):
            errors.append(f"{rel}: 音符数 {len(notes)} != 期望 {len(exp_t)}")
            continue
        for (s1, d1, p1), (s2, d2, p2) in zip(notes, exp_t):
            if not (close(s1, s2) and close(d1, d2) and p1 == p2):
                errors.append(f"{rel}: 音符不符 got=({s1},{d1},{p1}) exp=({s2},{d2},{p2})")
                break

        # C. 变速位置同步
        span_end = max((s + d for s, d, _ in notes), default=0.0)
        want = [(round(p, 6), int(round(b))) for p, b in tempos
                if EPS < p < span_end - EPS]
        got = [(round(p, 6), b) for p, b in ftempos]
        if want != got:
            errors.append(f"{rel}: 变速不同步\n    期望 {want[:6]}...\n    实际 {got[:6]}...")
            continue
        ok += 1

    print(f"校验文件数: {ok + len(errors)}")
    if errors:
        print(f"❌ {len(errors)} 个文件未通过:")
        for e in errors[:10]:
            print("  ", e)
        return 1
    print(f"✅ 全部通过：文件头 t/v、音符逐音、变速位置同步（{len(tempos)} 段变速）")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2],
                  int(sys.argv[3]) if len(sys.argv) > 3 else 4))
