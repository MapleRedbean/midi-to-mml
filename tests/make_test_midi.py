"""生成用于测试的 4 轨 MIDI（含和弦、附点、休止、变速）"""
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

TPB = 480
mid = MidiFile(ticks_per_beat=TPB)


def nt(notes, vel=100, ch=0):
    """一条音轨：notes = [(start_beat, dur_beat, pitch)]"""
    tr = MidiTrack()
    mid.tracks.append(tr)
    tr.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
    events = []
    for st, du, p in notes:
        events.append((int(st * TPB), "on", p, vel))
        events.append((int((st + du) * TPB), "off", p, 0))
    events.sort(key=lambda e: (e[0], e[1] == "on"))
    last = 0
    for tick, kind, p, v in events:
        tr.append(Message("note_on" if kind == "on" else "note_off",
                          note=p, velocity=v, channel=ch, time=tick - last))
        last = tick


# 1) 旋律：八分音符 + 附点 + 休止
mel = []
seq = [60, 62, 64, 67, 72, 71, 69, 67]
for i, p in enumerate(seq):
    mel.append((i * 0.5, 0.5, p))
mel += [(4.0, 1.5, 64), (5.5, 0.5, 62), (6.0, 2.0, 60)]  # 附点四分 + 二分

# 2) 和弦轨：C 大三和弦 x4，F 大三和弦 x4（必然裂成 3 个声部）
cho = []
for bar in range(2):
    for beat in range(4):
        s = bar * 4 + beat
        if bar == 0:
            cho += [(s, 1.0, 60), (s, 1.0, 64), (s, 1.0, 67)]
        else:
            cho += [(s, 1.0, 65), (s, 1.0, 69), (s, 1.0, 72)]

# 3) 低音：二分音符
bas = [(0.0, 2.0, 36), (2.0, 2.0, 43), (4.0, 2.0, 41), (6.0, 2.0, 36)]

# 4) 琶音 + 长音叠加（测试"音尾交叠"导致的额外声部）
arp = []
for i in range(16):
    arp.append((i * 0.25, 0.25, [60, 64, 67, 72][i % 4]))
arp += [(0.0, 4.0, 48)]  # 一个长音，与琶音重叠 -> 必然产生第 2 声部

nt(mel, 100)
nt(cho, 90)
nt(bas, 80)
nt(arp, 110)

mid.tracks[0].name = "melody"
mid.tracks[1].name = "chords"
mid.tracks[2].name = "bass"
mid.tracks[3].name = "arpeggio"

out = "/vol1/@appdata/trim.hermes/workspace/midi2mml/test4.mid"
mid.save(out)
print("saved", out, "| tracks:", len(mid.tracks), "| notes:", sum(len(t) for t in mid.tracks))
