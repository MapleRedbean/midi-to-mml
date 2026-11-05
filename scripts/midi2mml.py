#!/usr/bin/env python3
"""MIDI -> MML 转换器（多声部拆分 + GM 音色文件夹 + 变速同步）

要点：
  * 每条 MIDI 音轨按和弦拆分声部，每个声部一个文件
  * 每个文件开头一律是 t{BPM}v{音量}o{八度}l{时值}
  * 曲子中途有任何变速，所有文件在同一音乐位置插入相同的 t{BPM}
  * 输出按 GM 音色建文件夹，如 piano_01/、strings_49/
"""
from __future__ import annotations

import argparse
import json
import os
import zipfile
from dataclasses import dataclass

import mido

EPS = 1e-6

# ---------------------------------------------------------------- GM 128 音色
# (文件名前缀, 英文名)，索引 0 对应 GM 编号 01
GM = [
    ("piano", "Acoustic Grand Piano"),
    ("bright_piano", "Bright Acoustic Piano"),
    ("egrand_piano", "Electric Grand Piano"),
    ("honkytonk", "Honky-tonk Piano"),
    ("epiano1", "Electric Piano 1"),
    ("epiano2", "Electric Piano 2"),
    ("harpsichord", "Harpsichord"),
    ("clavinet", "Clavinet"),
    ("celesta", "Celesta"),
    ("glockenspiel", "Glockenspiel"),
    ("musicbox", "Music Box"),
    ("vibraphone", "Vibraphone"),
    ("marimba", "Marimba"),
    ("xylophone", "Xylophone"),
    ("tubularbells", "Tubular Bells"),
    ("dulcimer", "Dulcimer"),
    ("drawbar_organ", "Drawbar Organ"),
    ("perc_organ", "Percussive Organ"),
    ("rock_organ", "Rock Organ"),
    ("church_organ", "Church Organ"),
    ("reed_organ", "Reed Organ"),
    ("accordion", "Accordion"),
    ("harmonica", "Harmonica"),
    ("tango_accordion", "Tango Accordion"),
    ("guitar_nylon", "Acoustic Guitar (nylon)"),
    ("guitar_steel", "Acoustic Guitar (steel)"),
    ("guitar_jazz", "Electric Guitar (jazz)"),
    ("guitar_clean", "Electric Guitar (clean)"),
    ("guitar_muted", "Electric Guitar (muted)"),
    ("overdrive_guitar", "Overdriven Guitar"),
    ("distortion_guitar", "Distortion Guitar"),
    ("guitar_harmonics", "Guitar Harmonics"),
    ("acoustic_bass", "Acoustic Bass"),
    ("bass_finger", "Electric Bass (finger)"),
    ("bass_pick", "Electric Bass (pick)"),
    ("fretless_bass", "Fretless Bass"),
    ("slap_bass1", "Slap Bass 1"),
    ("slap_bass2", "Slap Bass 2"),
    ("synth_bass1", "Synth Bass 1"),
    ("synth_bass2", "Synth Bass 2"),
    ("violin", "Violin"),
    ("viola", "Viola"),
    ("cello", "Cello"),
    ("contrabass", "Contrabass"),
    ("tremolo_strings", "Tremolo Strings"),
    ("pizz_strings", "Pizzicato Strings"),
    ("harp", "Orchestral Harp"),
    ("timpani", "Timpani"),
    ("strings1", "String Ensemble 1"),
    ("strings2", "String Ensemble 2"),
    ("synth_strings1", "SynthStrings 1"),
    ("synth_strings2", "SynthStrings 2"),
    ("choir_aahs", "Choir Aahs"),
    ("voice_oohs", "Voice Oohs"),
    ("synth_voice", "Synth Voice"),
    ("orchestra_hit", "Orchestra Hit"),
    ("trumpet", "Trumpet"),
    ("trombone", "Trombone"),
    ("tuba", "Tuba"),
    ("muted_trumpet", "Muted Trumpet"),
    ("french_horn", "French Horn"),
    ("brass_section", "Brass Section"),
    ("synth_brass1", "SynthBrass 1"),
    ("synth_brass2", "SynthBrass 2"),
    ("soprano_sax", "Soprano Sax"),
    ("alto_sax", "Alto Sax"),
    ("tenor_sax", "Tenor Sax"),
    ("baritone_sax", "Baritone Sax"),
    ("oboe", "Oboe"),
    ("english_horn", "English Horn"),
    ("bassoon", "Bassoon"),
    ("clarinet", "Clarinet"),
    ("piccolo", "Piccolo"),
    ("flute", "Flute"),
    ("recorder", "Recorder"),
    ("pan_flute", "Pan Flute"),
    ("blown_bottle", "Blown Bottle"),
    ("shakuhachi", "Shakuhachi"),
    ("whistle", "Whistle"),
    ("ocarina", "Ocarina"),
    ("lead_square", "Lead 1 (square)"),
    ("lead_saw", "Lead 2 (sawtooth)"),
    ("lead_calliope", "Lead 3 (calliope)"),
    ("lead_chiff", "Lead 4 (chiff)"),
    ("lead_charang", "Lead 5 (charang)"),
    ("lead_voice", "Lead 6 (voice)"),
    ("lead_fifths", "Lead 7 (fifths)"),
    ("lead_bass", "Lead 8 (bass+lead)"),
    ("pad_newage", "Pad 1 (new age)"),
    ("pad_warm", "Pad 2 (warm)"),
    ("pad_polysynth", "Pad 3 (polysynth)"),
    ("pad_choir", "Pad 4 (choir)"),
    ("pad_bowed", "Pad 5 (bowed)"),
    ("pad_metallic", "Pad 6 (metallic)"),
    ("pad_halo", "Pad 7 (halo)"),
    ("pad_sweep", "Pad 8 (sweep)"),
    ("fx_rain", "FX 1 (rain)"),
    ("fx_soundtrack", "FX 2 (soundtrack)"),
    ("fx_crystal", "FX 3 (crystal)"),
    ("fx_atmosphere", "FX 4 (atmosphere)"),
    ("fx_brightness", "FX 5 (brightness)"),
    ("fx_goblins", "FX 6 (goblins)"),
    ("fx_echoes", "FX 7 (echoes)"),
    ("fx_scifi", "FX 8 (sci-fi)"),
    ("sitar", "Sitar"),
    ("banjo", "Banjo"),
    ("shamisen", "Shamisen"),
    ("koto", "Koto"),
    ("kalimba", "Kalimba"),
    ("bagpipe", "Bag pipe"),
    ("fiddle", "Fiddle"),
    ("shanai", "Shanai"),
    ("tinkle_bell", "Tinkle Bell"),
    ("agogo", "Agogo"),
    ("steel_drums", "Steel Drums"),
    ("woodblock", "Woodblock"),
    ("taiko", "Taiko Drum"),
    ("melodic_tom", "Melodic Tom"),
    ("synth_drum", "Synth Drum"),
    ("rev_cymbal", "Reverse Cymbal"),
    ("fret_noise", "Guitar Fret Noise"),
    ("breath_noise", "Breath Noise"),
    ("seashore", "Seashore"),
    ("bird_tweet", "Bird Tweet"),
    ("telephone", "Telephone Ring"),
    ("helicopter", "Helicopter"),
    ("applause", "Applause"),
    ("gunshot", "Gunshot"),
]


def gm_name(program: int) -> tuple[str, int, str]:
    """midi program(0-127) -> (短名, GM 编号 0-127, 英文名)"""
    p = max(0, min(127, int(program)))
    slug, en = GM[p]
    return slug, p, en


# ---------------------------------------------------------------- 数据结构
@dataclass
class Note:
    start: float   # 拍
    end: float     # 拍
    pitch: int
    vel: int


@dataclass
class Track:
    name: str
    notes: list
    program: int
    channel: int
    is_drum: bool


# ---------------------------------------------------------------- 读取 MIDI
def load_midi(path: str, include_drums: bool = True):
    mid = mido.MidiFile(path)
    tpb = mid.ticks_per_beat
    tempo_raw = []
    tracks = []

    for ti, tr in enumerate(mid.tracks):
        notes = []
        on = {}
        program = 0
        channel = 0
        t = 0
        tname = tr.name or ""
        for msg in tr:
            t += msg.time
            mtype = msg.type
            if mtype == "set_tempo":
                tempo_raw.append((t / tpb, round(60_000_000 / msg.tempo, 3)))
            elif mtype == "program_change":
                program = msg.program
                channel = msg.channel
            elif mtype == "note_on" and msg.velocity > 0:
                channel = msg.channel
                on[(msg.channel, msg.note)] = (t / tpb, msg.velocity)
            elif mtype == "note_off" or (mtype == "note_on" and msg.velocity == 0):
                k = (msg.channel, msg.note)
                if k in on:
                    st, vel = on.pop(k)
                    notes.append(Note(st, t / tpb, msg.note, vel))
        end_beat = t / tpb
        for (ch, pitch), (st, vel) in on.items():          # 未闭合音符
            notes.append(Note(st, max(end_beat, st + 0.25), pitch, vel))
        if not notes:
            continue
        is_drum = (channel == 9)
        if is_drum and not include_drums:
            continue
        if not tname:
            tname = f"track{ti + 1:02d}"
        tracks.append(Track(tname, sorted(notes, key=lambda n: (n.start, n.pitch)),
                            program, channel, is_drum))

    # 变速时间线：位置(拍) -> BPM，相邻同值合并
    tempo_raw.sort()
    tempos = []
    for pos, bpm in tempo_raw:
        if not tempos or abs(tempos[-1][1] - bpm) > 1e-6:
            tempos.append((pos, bpm))
    if not tempos:
        tempos = [(0.0, 120.0)]

    meta = {
        "ticks_per_beat": tpb,
        "length_sec": round(mid.length, 1),
        "tempo_changes": len(tempos),
        "bpm_first": round(tempos[0][1], 2),
        "bpm_values": (min(b for _, b in tempos), max(b for _, b in tempos)),
    }
    return tpb, tempos, tracks, meta


# ---------------------------------------------------------------- 量化 / 拆声部
def pick_divisions(notes, candidates=(4, 6, 8, 12, 16)):
    best = None
    for d in candidates:
        step = 1.0 / d
        err = 0.0
        for n in notes:
            err += abs(round(n.start / step) * step - n.start)
            err += abs(round(n.end / step) * step - n.end)
        err /= max(1, len(notes))
        if best is None or err < best[1] - 1e-9:
            best = (d, err)
        if err < 1e-9:
            break
    return best


def quantize(notes, step: float):
    out = []
    for n in notes:
        st = round(n.start / step) * step
        en = round(n.end / step) * step
        if en <= st:
            en = st + step
        out.append(Note(st, en, n.pitch, n.vel))
    out.sort(key=lambda n: (n.start, n.pitch))
    return out


def split_voices(notes):
    """区间图着色：把多声部拆成尽量少的单声部"""
    voices = []
    for n in notes:
        placed = False
        for v in voices:
            if v[-1].end <= n.start + EPS:
                v.append(n)
                placed = True
                break
        if not placed:
            voices.append([n])
    return voices


# ---------------------------------------------------------------- MML 时值
DENS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64)


def duration_tokens(beats: float, max_dots: int = 1):
    """拍数 -> [(分母, 附点数)]，用延音符号拼不够整的音"""
    if beats <= EPS:
        return [(64, 0)]
    cands = []
    for den in DENS:
        base = 4.0 / den
        for dots in range(max_dots + 1):
            mul = 1.0
            if dots >= 1:
                mul += 0.5
            if dots >= 2:
                mul += 0.25
            cands.append((base * mul, den, dots))
    cands.sort(key=lambda x: -x[0])
    out = []
    rest = beats
    guard = 0
    limit = max(64, int(beats / (4.0 / 64)) + 16)
    while rest > 1e-4 and guard < limit:
        for val, den, dots in cands:
            if val <= rest + 1e-4:
                out.append((den, dots))
                rest -= val
                break
        else:
            break
        guard += 1
    return out or [(64, 0)]


def tok_str(den: int, dots: int) -> str:
    return str(den) + "." * dots


def fit_mml_range(pitch: int) -> int:
    """MML 只有 o0~o8（MIDI 12~119），越界按八度折回"""
    while pitch < 12:
        pitch += 12
    while pitch > 119:
        pitch -= 12
    return pitch


NOTE_NAMES = ("c", "c+", "d", "d+", "e", "f", "f+", "g", "g+", "a", "a+", "b")
NOTE_NAMES_FLAT = ("c", "d-", "d", "e-", "e", "f", "g-", "g", "a-", "a", "b-", "b")


def note_name(pitch: int, prefer_flat: bool = False):
    p = fit_mml_range(pitch)
    octv = p // 12 - 1
    pc = p % 12
    return (NOTE_NAMES_FLAT if prefer_flat else NOTE_NAMES)[pc], octv


# ---------------------------------------------------------------- 生成 MML
def rest_mml(beats: float, max_dots: int = 1) -> str:
    return "".join("r" + tok_str(d, k) for d, k in duration_tokens(beats, max_dots))


def voice_to_mml(notes, tempos, volume: int, default_len: int = 16,
                 prefix: str = "", prefer_flat: bool = False,
                 fixed_octave=None, tie: str = "&", max_dots: int = 1) -> str:
    """把一个声部转成 MML。变速点按音乐位置精确插入（跨音符时用延音拆开）。"""
    bpm0 = int(round(tempos[0][1]))
    if not notes:
        return f"{prefix}t{bpm0}v{volume}o4l{default_len}"
    octv = _first_oct(notes, prefer_flat, fixed_octave)
    header = f"{prefix}t{bpm0}v{volume}o{octv}l{default_len}"

    pending = [(p, b) for p, b in tempos if p > EPS]
    parts = []
    cursor = 0.0
    ti = 0

    def emit_tempo_before(limit: float):
        """输出所有位置 <= limit 的变速；中间空隙用休止补齐"""
        nonlocal cursor, ti
        while ti < len(pending) and pending[ti][0] <= limit + EPS:
            tp, tb = pending[ti]
            if tp > cursor + EPS:
                parts.append(rest_mml(tp - cursor, max_dots))
                cursor = tp
            parts.append(f"t{int(round(tb))}")
            ti += 1

    for n in notes:
        emit_tempo_before(n.start)
        if n.start > cursor + EPS:
            parts.append(rest_mml(n.start - cursor, max_dots))
            cursor = n.start

        oct_, semi = n.pitch // 12 - 1, n.pitch % 12
        if oct_ < octv:
            parts.append("<" * (octv - oct_))
            octv = oct_
        elif oct_ > octv:
            parts.append(">" * (oct_ - octv))
            octv = oct_
        name = note_name(n.pitch, prefer_flat)[0]

        # 音符内部若有变速点，按变速点切成若干段，用延音连起来
        inner = sorted(p for p, _ in pending[ti:] if n.start + EPS < p < n.end - EPS)
        pts = [n.start] + inner + [n.end]
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            emit_tempo_before(a)
            if a > cursor + EPS:
                parts.append(rest_mml(a - cursor, max_dots))
                cursor = a
            seg = ""
            for j, (den, dots) in enumerate(duration_tokens(b - a, max_dots)):
                tok = tok_str(den, dots)
                lit = name if (den == default_len and dots == 0) else name + tok
                seg += lit if (k == 0 and j == 0) else tie + lit
            parts.append(seg)
            cursor = b
    return header + "".join(parts)

def _first_oct(notes, prefer_flat, fixed_octave):
    if fixed_octave is not None:
        return max(0, min(8, fixed_octave))
    return max(0, min(8, note_name(notes[0].pitch, prefer_flat)[1]))


# ---------------------------------------------------------------- 主流程
def action_timeline(tracks_notes, tempos, act_cmd, max_dots=1, min_rest=1.0):
    """返回 _action.txt 的期望 (pos, cmd) 事件列表，与 build_action_mml 一致。"""
    ivs = []
    for notes in tracks_notes:
        for n in notes:
            if n.end - n.start > EPS:
                ivs.append((n.start, n.end))
    ivs.sort()
    merged = []
    for s, e in ivs:
        # 间隙小于 min_rest 拍的，视为连续演奏（不切 M0）
        if merged and s <= merged[-1][1] + min_rest:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    span = max((e for _, e in merged), default=0.0)

    m_events = []
    if merged:
        if merged[0][0] <= EPS:
            m_events.append((0.0, act_cmd))
        else:
            m_events.append((0.0, "M0"))
        for i, (s, e) in enumerate(merged):
            if s > EPS:
                m_events.append((s, act_cmd))
            if e < span - EPS:
                m_events.append((e, "M0"))
    else:
        m_events.append((0.0, "M0"))

    p_events = [(p, f"P{max(32, min(255, int(round(b))))}") for p, b in tempos]
    events = sorted(m_events + p_events, key=lambda x: (round(x[0], 6), 0 if x[1].startswith("M") else 1))
    return events, act_cmd

def build_action_mml(tracks_notes, tempos, bpm0, default_len=16,
                     act="auto", max_dots=1, volume=10, min_rest=1.0):
    """生成 _action.txt：全局 M/P 时间轴（无音符，只有 M/P 与休止）。

    规则：
      * 任意声部有音符的时段 -> M3/M4（auto 按音符密度选）
      * 全部声部都休止的时段 -> M0
      * 每个变速点写 P{BPM}（32~255，越小越慢）
      * M 写在 P 前面
    """
    total = sum(len(ns) for ns in tracks_notes)
    ivs = []
    for notes in tracks_notes:
        for n in notes:
            if n.end - n.start > EPS:
                ivs.append((n.start, n.end))
    span = max((e for _, e in ivs), default=0.0)
    npb = total / span if span > EPS else 0.0
    if act == "auto":
        act_cmd = "M4" if npb > 2.0 else "M3"
    else:
        act_cmd = act.upper()

    events, _ = action_timeline(tracks_notes, tempos, act_cmd, min_rest=min_rest)

    parts = [f"t{int(round(bpm0))}v{volume}o4l{default_len}"]
    cursor = 0.0
    for pos, cmd in events:
        if pos > cursor + EPS:
            parts.append(rest_mml(pos - cursor, max_dots))
            cursor = pos
        parts.append(cmd)
    return "".join(parts), act_cmd, npb

def convert(midi_path, outdir, divisions="4", max_volume=15, default_len=16,
            prefix="", tie="&", include_drums=True, prefer_flat=False,
            max_dots=1, split_into_folders=True, zip_out=False, verbose=True,
            action="auto", action_min_rest=1.0):
    tpb, tempos, tracks, meta = load_midi(midi_path, include_drums=include_drums)
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(midi_path))[0]

    warnings = []
    if len(tempos) > 1:
        changes = sum(1 for i in range(1, len(tempos)) if abs(tempos[i][1] - tempos[i - 1][1]) > 1e-6)
        warnings.append(f"含 {len(tempos)} 段变速（{meta['bpm_values'][0]:.0f}~{meta['bpm_values'][1]:.0f} BPM），"
                        f"已在所有文件的相同位置插入 t 指令（共 {changes} 次变化）")

    files, report = [], []
    used_dirs = {}
    tracks_q = []

    for ti, tr in enumerate(tracks, 1):
        if tr.is_drum:
            slug, gid, en = "drums", tr.channel + 1, "Drums"
        else:
            slug, gid, en = gm_name(tr.program)
        if divisions == "auto":
            div, err = pick_divisions(tr.notes)
        else:
            div = int(divisions)
            step0 = 1.0 / div
            err = sum(abs(round(n.start / step0) * step0 - n.start) for n in tr.notes) / max(1, len(tr.notes))
        step = 1.0 / div
        q = quantize(tr.notes, step)
        voices = split_voices(q)
        tracks_q.append(q)

        # 文件夹名：piano_01 / piano_01_c2（同音色多轨时加序号）
        folder = f"{slug}_{gid:02d}"
        if folder in used_dirs:
            # 同音色的第二条轨：用轨道名区分（如 piano_01_left_hand）
            used_dirs[folder] += 1
            # 音轨名只保留 ASCII 字母数字/连字符；中文等非 ASCII 一律转下划线，
            # 避免中文音轨名混进文件夹名后打包 zip 回传时乱码（统一 ASCII 安全命名）
            ts = "".join(
                ch if ("\u0000" <= ch <= "\u007f" and (ch.isalnum() or ch in "-_")) else "_"
                for ch in tr.name
            ).strip("_").lower()
            ts = "_".join(x for x in ts.split("_") if x)[:24]
            folder = f"{folder}_{ts}" if ts else f"{folder}_c{used_dirs[folder]}"
        else:
            used_dirs[folder] = 1
        target_dir = os.path.join(outdir, folder) if split_into_folders else outdir
        os.makedirs(target_dir, exist_ok=True)

        for vi, v in enumerate(voices, 1):
            vol = max(1, min(max_volume, round(sum(n.vel for n in v) / len(v) / 127 * max_volume)))
            mml = voice_to_mml(v, tempos, vol, default_len=default_len, prefix=prefix,
                               tie=tie, prefer_flat=prefer_flat, max_dots=max_dots)
            suffix = f"_v{vi}" if len(voices) > 1 else ""
            fname = f"{slug}_{gid:02d}{suffix}.txt"
            path = os.path.join(target_dir, fname)
            with open(path, "w", encoding="utf-8") as f:
                f.write(mml + "\n")
            rel = os.path.relpath(path, outdir)
            files.append(rel)
            report.append({
                "file": rel, "track_index": ti, "track": tr.name, "program": gid,
                "gm": en, "channel": tr.channel + 1, "voice": vi,
                "voices": len(voices), "notes": len(v), "volume": vol,
                "chars": len(mml), "divisions": div,
                "quant_error_beats": round(err, 5),
            })

        if action and action.lower() != "none":
            # 每条音轨一个动作文件：{slug}_{id:02d}_action.txt，放进该轨文件夹
            amml, act_cmd, npb = build_action_mml([q], tempos, tempos[0][1],
                                                  default_len=default_len, act=action,
                                                  max_dots=max_dots,
                                                  min_rest=action_min_rest)
            afname = f"{slug}_{gid:02d}_action.txt"
            apath = os.path.join(target_dir, afname)
            with open(apath, "w", encoding="utf-8") as f:
                f.write(amml + "\n")
            arel = os.path.relpath(apath, outdir)
            files.append(arel)
            report.append({"file": arel, "track_index": ti, "track": tr.name,
                           "program": gid, "gm": en, "channel": tr.channel + 1,
                           "voice": 0, "voices": 0, "notes": 0, "volume": 10,
                           "chars": len(amml), "divisions": div,
                           "quant_error_beats": 0, "action": act_cmd,
                           "action_min_rest": action_min_rest,
                           "notes_per_beat": round(npb, 2)})

    manifest = {
        "source": os.path.basename(midi_path),
        "bpm": int(round(tempos[0][1])),
        "tempo_changes": len(tempos),
        "tempo_map": [[round(p, 4), round(b, 2)] for p, b in tempos],
        "divisions_default": str(divisions),
        "prefix": prefix,
        "tie": tie,
        "max_volume": max_volume,
        "warnings": warnings,
        "files": files,
        "report": report,
    }
    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    zpath = None
    if zip_out:
        zpath = os.path.join(os.path.dirname(os.path.abspath(outdir.rstrip("/"))) or ".",
                             f"{base}_mml.zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _dirs, fs in os.walk(outdir):
                for fn in fs:
                    full = os.path.join(root, fn)
                    z.write(full, os.path.relpath(full, outdir))

    if verbose:
        print(f"源文件      : {os.path.basename(midi_path)}")
        print(f"BPM         : {int(round(tempos[0][1]))}"
              + (f"（共 {len(tempos)} 段变速，已同步到每个文件）" if len(tempos) > 1 else ""))
        print(f"音轨        : {len(tracks)}  |  输出文件: {len(files)}")
        print(f"时值基准    : l{default_len}（16 分音符）  |  前缀: {prefix or '(无)'}")
        for r in report:
            print(f"  {r['file']:<42} {r['gm']:<24} GM{r['program']:>3}  "
                  f"{r['notes']:>4}音  v{r['volume']:<2} {r['chars']:>5}字符")
        for w in warnings:
            print("⚠ " + w)
        if zpath:
            print(f"ZIP         : {zpath}")

    return {"files": files, "zpath": zpath, "manifest": manifest, "report": report}


def main(argv=None):
    ap = argparse.ArgumentParser(description="MIDI -> MML（多声部拆分 / GM 文件夹 / 变速同步）")
    ap.add_argument("midi")
    ap.add_argument("-o", "--out", default="mml_out")
    ap.add_argument("--divisions", default="4", help="每拍格数：4=16分(默认) 6=三连 8=32分 auto=自动")
    ap.add_argument("--default-len", type=int, default=16, help="默认时值分母（16=16分音符）")
    ap.add_argument("--prefix", default="", help='行首前缀，需要时填 "MML@"')
    ap.add_argument("--tie", default="&", help="延音符号（& 或 ^）")
    ap.add_argument("--max-volume", type=int, default=15)
    ap.add_argument("--max-dots", type=int, default=1)
    ap.add_argument("--no-drums", action="store_true", help="跳过鼓轨（GM 通道 10），默认转换鼓轨")
    ap.add_argument("--prefer-flat", action="store_true", help="用降号代替升号")
    ap.add_argument("--flat", action="store_true", help="不建音色文件夹，全部平铺")
    ap.add_argument("--action", default="auto", help="生成 _action.txt：auto|M0..M5|none（默认 auto 按复杂度选 M3/M4）")
    ap.add_argument("--action-min-rest", type=float, default=1.0, help="间隙小于此拍数的休止不切 M0（避免动作频繁切换），默认 1.0")
    ap.add_argument("--zip", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    res = convert(a.midi, a.out, divisions=a.divisions, max_volume=a.max_volume,
                  default_len=a.default_len, prefix=a.prefix, tie=a.tie,
                  include_drums=not a.no_drums, prefer_flat=a.prefer_flat,
                  max_dots=a.max_dots, split_into_folders=not a.flat, zip_out=a.zip,
                  action=a.action, action_min_rest=a.action_min_rest)
    if a.json:
        print(json.dumps({"files": res["files"], "report": res["report"]},
                         ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
