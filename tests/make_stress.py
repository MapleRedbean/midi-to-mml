"""压力/异常测试：2000 音随机多声部、极低极音、未闭合音符、变速、纯鼓"""
import random
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

random.seed(7)
TPB = 480
mid = MidiFile(ticks_per_beat=TPB)

def nt(notes, vel=100, ch=0, name=None, close=True, tempo=None, tempo_change=False):
    tr = MidiTrack(); mid.tracks.append(tr)
    if name: tr.name = name
    tr.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo or 120), time=0))
    ev = []
    for st, du, p in notes:
        ev.append((int(st*TPB), "on", p, vel))
        if close:
            ev.append((int((st+du)*TPB), "off", p, 0))
    ev.sort(key=lambda e: (e[0], e[1] == "on"))
    last = 0
    for tick, kind, p, v in ev:
        tr.append(Message("note_on" if kind=="on" else "note_off", note=p, velocity=v, channel=ch, time=tick-last))
        last = tick
    if tempo_change:
        tr.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(180), time=TPB*2))

# 1) 2000 音符随机多声部
big = []
t = 0.0
for i in range(2000):
    big.append((t, random.choice([0.25, 0.5, 0.75, 1.0]), random.randint(48, 84)))
    t += random.choice([0.0, 0.25, 0.5])
nt(big, 100, name="stress2000")

# 2) 极低/极高音（MML 可表示范围外）
nt([(0, 1, 5), (1, 1, 10), (2, 1, 120), (3, 1, 127)], 100, name="extremes")

# 3) 未闭合音符（缺 note_off）
nt([(0, 1, 60), (2, 4, 64), (6, 1, 67)], 90, name="unclosed", close=False)

# 4) 变速（中途改速）
nt([(0, 1, 60), (1, 1, 62), (4, 1, 64), (7, 1, 65)], 80, name="tempovar", tempo_change=True)

# 5) 纯鼓轨
nt([(i*0.5, 0.25, 36) for i in range(20)], 110, ch=9, name="onlydrums")

out = "/vol1/@appdata/trim.hermes/workspace/midi2mml/test_stress.mid"
mid.save(out); print("saved", out, "tracks", len(mid.tracks))
