<h1 align="center">logisim-ita-lab</h1>

<p align="center">A text-first workflow for Logisim-ITA circuit labs: parse, generate, and verify <code>.circ</code> files.</p>

<p align="center"><a href="README.zh-CN.md">简体中文</a> | English</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/Logisim--ITA-2.16.2.0-informational" alt="Logisim-ITA 2.16.2.0">
</p>

## Highlights

- **Circuits as text.** A `.circ` file is UTF-8 XML, so a circuit can be generated, diffed, and reviewed without clicking through a GUI.
- **Two verification paths, chosen by circuit kind.** Gate-level simulation for combinational logic; the real Logisim engine, tick by tick, for sequential logic.
- **Measured, not guessed.** Component port coordinates were read back from Logisim-ITA 2.16.2.0 with a dump tool, and the tables record what was actually observed.
- **Stdlib-only Python.** Parser, gate-level simulator, and truth-table validator need no third-party packages. Java is needed only when the real engine has to run.
- **Knowledge base included.** `references/exp1-tasks.md` records the five Lab 1 tasks: logic, pins, truth table, topology, coordinates.
- **Offline self-test.** `scripts/selftest.py` exercises the whole parser → generator → simulator → validator chain and needs no Java.

## Architecture

The workflow takes a problem statement plus a template `.circ`, produces one candidate `.circ`, and routes it to one of three verification paths.

```text
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│  Problem docx or  │    │    circ_parser    │    │  Topology design  │
│   template .circ  │───▶│  (structure JSON) │───▶│   + circlib emit  │
└───────────────────┘    └───────────────────┘    └─────────┬─────────┘
                                                            │
                                   ┌────────────────────────┘
                         ┌─────────▼─────────┐
                         │   candidate.circ  │
                         └─────────┬─────────┘
          ┌────────────────────────┴────────────────────────┐
          ▼                        ▼                        ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│    validate.py    │    │  Logisim-ITA GUI  │    │    CircRun.java   │
│  gate-level check │    │    manual poke    │    │  runner.py, tick  │
└───────────────────┘    └───────────────────┘    └───────────────────┘
    combinational      transistor / subcircuit         sequential
```

`references/` holds the format manual, the component port table, the sequential-test protocol, and the platform notes. `SKILL.md` is the operating procedure that ties them together.

## Usage Example

```bash
# Inspect a template: main circuit name, pins, tunnels, blank areas
python scripts/circ_parser.py path/to/lab1.3.circ

# Compare a circuit against a built-in Lab 1 truth table
python scripts/validate.py path/to/lab1.3.circ --task lab1.3

# Or supply a custom truth table
python scripts/validate.py path/to/my.circ --table-file truth.json
```

`validate.py` exit codes: `0` every case matches, `1` a case or a pin label mismatches, `2` the circuit cannot be simulated at gate level (transistors, subcircuits, sequential parts).

Custom truth-table format:

```json
{"inputs": ["X", "Y"], "outputs": ["F"],
 "cases": [{"in": [0, 0], "out": [0]}, {"in": [1, 1], "out": [1]}]}
```

Built-in tables cover `lab1.1` through `lab1.5`.

## Quick Install

Requirements:

| Part | Needed for | Note |
|---|---|---|
| Python 3 | every script | standard library only, no `pip install` |
| JDK 8 or newer | `CircRun.java`, `Conn`, `Dump`, `ErrLoad` | compile once with `javac` |
| Logisim-ITA 2.16.2.0 | GUI checks and the real engine | same version as the target platform |

For the Java helpers, point the scripts at your local copies through environment variables:

```bash
export LOGISIM_JAVA="<jdk>/bin/java"      # default: java on PATH
export LOGISIM_JAR="<dir>/Logisim-ITA-2.16.2.0/Logisim-ITA.jar"
export LOGISIM_TOOLS="<compiled classes dir>"   # default: tools
```

To use the repository as an agent skill, copy the folder into your skills directory (for WorkBuddy, `~/.workbuddy/skills/`). `SKILL.md` carries the frontmatter that the loader reads.

## Quick Start

```bash
git clone https://github.com/SunshineMahiru/logisim-ita-lab.git
cd logisim-ita-lab
python scripts/selftest.py
```

Expected output, produced by the repository as it stands:

```text
[1/4] 解析: 主电路 main，电路 dict_keys(['main'])
[2/4] 仿真: 8 组用例与 lab1.3 真值表一致
[3/4] 命令行: validate.py 返回 0
[4/4] 降级: 含晶体管的电路被门级仿真器拒绝
SELFTEST: ALL PASS
```

The self-test builds a 2-to-1 multiplexer from a minimal template, simulates all eight input combinations, runs the CLI end to end, and confirms that a transistor circuit is rejected at gate level.

## Repository Layout

| Path | Contents |
|---|---|
| `SKILL.md` | Operating procedure: extract requirements, read the template, design topology, emit XML, verify |
| `references/circ-format.md` | `.circ` syntax: XML structure, library numbers, component attributes, generation rules |
| `references/components.md` | Measured port coordinates for gates, D flip-flops, registers, adders, multiplexers, splitters |
| `references/timing-verification.md` | Sequential-circuit test and acceptance protocol, plus the digital-clock reference build |
| `references/platform-notes.md` | Evaluation mechanics, clock conventions, external library references, transfer channels |
| `references/exp1-tasks.md` | The five Lab 1 tasks as a worked example and regression source |
| `scripts/*.py` | Parser, gate-level simulator, validator, text emitter, runner wrapper, self-test |
| `scripts/*.java` | Headless engine driver, dangling-endpoint lister, port dumper, load-error capture |

## Verification Paths

| Circuit kind | Tool | What it proves |
|---|---|---|
| Combinational (AND/OR/NOT and friends) | `validate.py` | every row of the truth table matches |
| Transistor level or subcircuit | Logisim-ITA GUI | the netlist behaves under manual pokes |
| Sequential (flip-flops, registers, counters) | `CircRun.java` + `runner.py` | state sequence matches per clock edge |

The sequential path also covers structural checks: `Conn` lists dangling endpoints, `Dump` prints the port coordinate a component actually exposes, and `ErrLoad` returns the load error text that the GUI would otherwise swallow.

## Scope

- The target is Logisim-ITA 2.16.2.0 and the EduCoder "Computer Organization" lab series. Other versions can differ in library numbering and port geometry.
- Platform behaviour recorded in `references/platform-notes.md` comes from one course deployment. Treat per-level details as observations to re-check, not as universal rules.
- The repository does not cover Verilog or Vivado flows, and it does not modify Logisim-ITA itself.
- Lab answer topologies are teaching material for that course. Use them within the rules that apply to you.

## License

MIT. See [LICENSE](LICENSE). Copyright (c) 2026 SunshineMahiru (曦昼Sunshine).
