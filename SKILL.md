---
name: midi-to-mml
description: 把 MIDI 转成 MML（洛奇等），自动按和弦拆分声部，每个文件带 t(BPM)/v(音量) 头。
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [midi, mml, music, 洛奇, 编曲, 格式转换]
    related_skills: [songwriting-and-ai-music]
---

# MIDI → MML（多声部拆分）

## When to Use（何时用）

- 用户给一个 `.mid`，要转成 MML 谱（洛奇/玛奇、支持 `MML@` 语法的游戏或播放器）
- MIDI 一条音轨里有和弦，而 MML 轨道是**单音**的，需要拆成多个文件
- 要求每个文件头部带 BPM 与音量

## 快速用法

```bash
PY=/vol1/@appdata/trim.hermes/venvs/midi2mml/bin/python
$PY scripts/midi2mml.py 输入.mid -o 输出目录 --zip
```

依赖 `mido`（已装在 `/vol1/@appdata/trim.hermes/venvs/midi2mml`）。新环境先建：

```bash
python3 -m venv /vol1/@appdata/trim.hermes/venvs/midi2mml
/vol1/@appdata/trim.hermes/venvs/midi2mml/bin/pip install mido
```

## 输出规则

| 规则 | 行为 |
|---|---|
| 文件粒度 | 按 GM 音色建文件夹，文件名 `{音色}_{id:02d}[_v{声部}].txt`，如 `piano_00/piano_00_v1.txt` |
| 和弦处理 | 同一时刻重叠的音 → 贪心分配声部（区间划分，声部数最少） |
| 文件头 | `t{BPM}v{音量}o{起始八度}l16`（**默认无 MML@ 前缀**，需要时 `--prefix "MML@"`） |
| 变速同步 | 曲子中途每次变速，**所有文件在同一音乐位置插入相同 `t{BPM}`**（跨音符时用延音拆开） |
| 音量 | 由力度映射：`v = round(vel/127*15)`，默认取该声部**平均**力度 |
| 鼓轨 | 通道 9 默认**跳过**，`--include-drums` 才转 |
| 清单 | 输出目录生成 `manifest.json`（每文件的音符数、音量、BPM、量化栅格、告警） |

## 节奏基准：16 分音符（L16）

**默认就是 16 分音符基准，不要改成 8 分。** 两点保证：

1. `--default-len` 默认 **16**，所以文件头恒为 `l16`
2. 量化栅格候选 `(4, 6, 8, 12, 16)` 的单位是「每拍切几格」，最小 **4** = 每拍 4 格 = **16 分音符**。永远不会退到 8 分音符栅格的 `divisions=2`

效果对照：

| 实际时值 | 输出 | 说明 |
|---|---|---|
| 16 分 | `c` | 单字符，L16 省略 |
| 8 分 | `c8` | |
| 4 分 | `c4` | |
| 附点 8 分 | `c8.` | 单附点 |
| 3/16 | `c8.` | |
| 全音符 | `c1` | |
| 6 拍 | `c1.` | |
| 8 拍 | `c1.&c2` | 超全音符用延音 |
| 32 分 | `c32` | 仅当曲子里真有 32 分才升栅格 |

用户明确要求「**最好是16分音符，虽然字符超多但是兼容性好**」，因此：

- 不要为了省字符把 `--default-len` 设成 8
- 不要用 `--divisions 2`（那是 8 分栅格，会吃掉 16 分音符）
- 若目标播放器不认 32 分，用 `--divisions 4` 强制吸附到 16 分栅格（三连音曲目慎用，会走音）

## _action.txt（演奏动作文件）

- 原有声部文件**不变**，每条音轨额外生成一个 `{音色}_{id:02d}_action.txt`（放进该轨文件夹）
- 规则：**该轨**声部有音符的时段 → `M3/M4`；该轨全休止时段 → `M0`；变速点 → `P{BPM}`
- `M` 永远写在 `P` 前面；间隙小于 `--action-min-rest` 拍的休止不切 M0（避免动作频繁切换）
- `--action auto` 按音符密度自动选 M3/M4（密度>2音/拍→M4，否则 M3），也可指定 M0..M5 或 none
- 示例：`t90v10o4l16M4P90r4r16M0r2r8.M4r1.r1...P45...P90r2r16M0...`

## 参数

**以下必须与 `scripts/midi2mml.py` 的 argparse 保持同步**（本节曾因改默认值后忘改文档而失效）：

```
--divisions 4|6|8|12|16|auto   每拍格数。默认 4（=16分音符）；auto 挑误差最小
--default-len 16               默认时值分母，配合行内数字省略
--prefix ""                    每文件前缀（默认空=无 MML@；洛奇原版传 "MML@"）
--tie &                        延音符号（部分方言用 ^ 或 +）
--max-volume 15                MML 音量上限（洛奇=15）
--max-dots 1                   附点上限（0/1/2）
--include-drums                转换鼓轨（通道 9，默认跳过）
--prefer-flat                  升降号用 b-/e- 而非 c+/d+
--flat                         不建音色文件夹，全部平铺
--action auto|M0..M5|none      生成 _action.txt（默认 auto）
--action-min-rest 1.0          休止多少拍才切 M0（防动作抖动）
--zip                          额外打成 zip
--json                         打印 JSON 报告
```

## 验证（改完代码必须跑）

```bash
$PY tests/verify.py 输入.mid 输出目录
```

它会做两件事，比"看起来对"严格：

1. **完整性**：该轨所有声部音符的并集 == 源 MIDI 量化后的音符，一个不能丢、不能多
2. **正确性**：反向解析每个 MML 文件，音高/起点/时值必须与对应声部完全一致，并校验 `t` 头

## 坑（都踩过）

1. **三连音必须用 `l12`/`l6`/`l24`** —— 只给 2 的幂次分母（4/8/16）时，1/3 拍会被错误拆成 0.25+0.0625 之类，时长直接错。代码里分母表是 `1,2,3,4,6,8,12,16,24,32,48,64`，别删三元。
2. **音域只有 12~119**（`o0`~`o8`）。超出的音必须按八度折回，否则会生成 `o-1`、`o9` 这种非法指令，播放器直接不认。转换器会自动折并写告警。
3. **变速同步**：MML 的 `t` 是全局的，但本工具把每次变速都写进**每个文件**的对应位置（跨音符时用延音拆开），多文件同时播放节奏才一致。文件头取时间占比最大的 BPM。
4. **双附点兼容性差**。`max_dots=1`，更长时值靠延音 `&` 拼接（`c2.&c8`），比 `c2..` 安全。
5. **量化栅格要和校验器一致**。校验器优先读 `manifest.json` 里的 `divisions_used`，不要手动传错。
6. **未闭合音符**（只有 note_on 没有 note_off）会被钳到轨尾，不报错但要留意。
7. **声部数爆炸**：如果一条轨是钢琴双手密集和弦，可能拆出 6~10 个声部。这符合"单音轨"约束，但游戏里没法同时播，需要人工取舍（`--max-voices` 或后期筛选）。
8. **MML 音高公式是 `pitch = (oct+1)*12 + semi`**，即 `o4` = MIDI 60（**不是** `oct*12+semi`）。转换器与校验器必须用同一公式，否则整轨差一个八度，而时值/起点全对，极易漏过。
9. **测试脚本不要命名 `inspect.py`** —— 会遮蔽标准库 `inspect`，`import dataclasses` 会炸出 `SyntaxError: unexpected character` 这类误导性错误。改名 `inspect_midi.py`。
10. **改 `manifest.json` 结构必须同步改 `tests/verify.py`** —— 校验器按 `files` / `report` / `track_index` / `divisions` 取数，schema 一变就 `KeyError`，且这是"校验失败"还是"校验器跟不上"要能分清。
11. **长时值生成必须有 guard 上限保护**，且循环上限要随 `beats` 增长 —— 见 `references/bugfix-log.md` 第 1 条（曾因写死 32 导致长休止被截断）。

## 文件

- `scripts/midi2mml.py` —— 转换器主体（纯 mido 依赖）
- `tests/verify.py` —— 独立校验器
- `tests/make_test_midi.py` —— 生成 4 轨测试 MIDI（含三和弦）
- `tests/make_test2.py` —— 边界测试（长时值/三连音/鼓轨）
- `tests/make_stress.py` —— 压力测试（2000 音/超音域/未闭合/变速）
- `tests/make_tempo.py` —— 变速同步测试（多轨 + 中途两次变速）
- `references/bugfix-log.md` —— 真实 bug 清单：症状→根因→修法→哪个测试抓到的（改代码前先看）
