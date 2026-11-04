# MIDI → MML

把 MIDI 转成 **MML**（洛奇 / 玛奇等支持 `MML@` 语法的游戏或播放器）。一条音轨里的和弦会按和弦自动拆成多个单音声部文件，每个文件头带 BPM 与音量。

## 特性

- **和弦自动拆分**：同一条 MIDI 音轨里的重叠音 → 贪心区间划分，声部数最少
- **16 分音符基准**：默认 `l16`，兼容性优先（字符多但不会吃掉 16 分音符）
- **变速同步**：曲子中途每次变速，所有输出文件在同一音乐位置插入相同的 `t{BPM}`（跨音符时用延音拆开），多文件同播节奏才一致
- **GM 音色分文件夹**：`piano_00/piano_00_v1.txt`、`strings_49/…`
- **演奏动作文件**：每条音轨额外生成 `_action.txt`（`M0`~`M5` + `P{BPM}`）
- **独立校验器**：`tests/verify.py` 反向解析 MML，逐音符比对音高/起点/时值 —— 不是"看起来对"

## 快速使用

```bash
python3 -m venv venv && ./venv/bin/pip install mido
./venv/bin/python scripts/midi2mml.py 输入.mid -o 输出目录 --zip
```

验证：

```bash
./venv/bin/python tests/verify.py 输入.mid 输出目录
```

## 常用参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--divisions 4\|6\|8\|12\|16\|auto` | 4 | 每拍格数，4 = 16 分音符基准 |
| `--prefix ""` | 空 | 每文件前缀，洛奇原版传 `"MML@"`
| `--include-drums` | 关 | 通道 9 鼓轨默认跳过
| `--flat` | 关 | 不建音色文件夹，全部平铺
| `--action auto\|M0..M5\|none` | auto | 演奏动作文件生成策略
| `--zip` | 关 | 额外打包 zip

完整参数见 [SKILL.md](SKILL.md)。

## 目录

```
SKILL.md                  完整使用文档（Hermes 技能格式）
scripts/midi2mml.py       转换器主体（仅依赖 mido）
scripts/requirements.txt  依赖
tests/verify.py           独立校验器
tests/make_test_midi.py   4 轨测试 MIDI（含三和弦）
tests/make_test2.py       边界测试（长时值/三连音/鼓轨）
tests/make_stress.py      压力测试（2000 音/超音域/未闭合/变速）
references/bugfix-log.md  真实 bug 清单：症状 → 根因 → 修法 → 哪个测试抓到的
windows/                  Windows 打包/运行脚本
```

## 已知坑（都踩过）

详见 [SKILL.md](SKILL.md) 的「坑」一节，最重要的几条：

1. **三连音必须用 `l12`/`l6`/`l24`** —— 只有 2 的幂次分母会把 1/3 拍拆错
2. **MML 音高公式是 `pitch = (oct+1)*12 + semi`** —— 不是 `oct*12+semi`，差一个八度且时值全对，极易漏过
3. **音域只有 12~119**（`o0`~`o8`），超出的音要按八度折回
4. **双附点兼容性差**，长时值用延音 `&` 拼接更安全

## License

MIT
