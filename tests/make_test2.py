"""边界测试：长时值（需要延音）、三连音、鼓轨(通道9)、变调古里"""
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

TPB = 480
mid = MidiFile(ticks_per_beat=TPB)

def nt(notes, vel=100, ch=0, name=None):
    tr = MidiTrack(); mid.tracks.append(tr)
    if name: tr.name = name
    tr.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(96), time=0))
    ev = []
    for st, du, p in notes:
        ev.append((int(st*TPB), "on", p, vel)); ev.append((int((st+du)*TPB), "off", p, 0))
    ev.sort(key=lambda e: (e[0], e[1] == "on"))
    last = 0
    for tick, kind, p, v in ev:
        tr.append(Message("note_on" if kind=="on" else "note_off", note=p, velocity=v, channel=ch, time=tick-last))
        last = tick

# 1) 长音：3.5 拍（必须用延音 &）与 7 拍（更长）
nt([(0.0, 3.5, 60), (3.5, 0.5, 62), (4.0, 7.0, 64)], 100, name="longnotes")
# 2) 三连音（在 --divisions 6 下应无误差）
nt([(i*(1/3.0), 1/3.0, 60+i%3) for i in range(12)], 100, name="triplet")
# 3) 鼓轨（通道 9，默认应被跳过）
nt([(i*0.5, 0.25, 36 if i%2==0 else 38) for i in range(8)], 120, ch=9, name="drums")
out = "/vol1/@appdata/trim.hermes/workspace/midi2mml/test_edge.mid"
mid.save(out); print("saved", out)
