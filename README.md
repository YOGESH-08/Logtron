# LogScan DFA
### High-Performance Log Pattern Analyzer using Regular Expressions and Finite Automata

**Course:** BITE306L — Theory of Computation  
**Repository:** [YOGESH-08/Logtron](https://github.com/YOGESH-08/Logtron)  
**Team Members:** _[Add Registration Numbers / Names Here]_

---

## 📌 Project Overview

**LogScan DFA** is a deterministic finite automata log analysis tool designed to scan high-volume log streams in **guaranteed linear time $O(n)$** relative to input length. 

Traditional regular expression engines (such as Python `re`, PCRE, or Java `regex`) rely on **NFA with Backtracking**, rendering them vulnerable to **Catastrophic Backtracking** (Regex Denial of Service / ReDoS) when processing pathological patterns or malformed log inputs. 

LogScan DFA compiles user regular expressions into automata using:
1. **Thompson Construction** (AST $\rightarrow$ NFA with $\epsilon$-transitions)
2. **Subset Construction** (NFA $\rightarrow$ DFA via $\epsilon$-closure powerset mapping)
3. **Hopcroft's Minimization Algorithm** (DFA $\rightarrow$ Minimal DFA via $O(n \log n)$ partition refinement)

The resulting minimal DFA is used by a streaming scanner engine to parse log files character-by-character. The project also provides an interactive DFA visualizer and a benchmark suite comparing performance against traditional backtracking regex engines.

---

## 📑 Course Mapping (Theory of Computation)

| Syllabus Module | Project Component | Theoretical Concept |
|---|---|---|
| **Module 1** (DFA, Minimization) | Hopcroft's Algorithm, DFA Scanner | Partition Refinement, $O(n)$ Streaming State Transitions |
| **Module 2** (NFA, $\epsilon$-transitions, Equivalence) | Thompson Construction, Subset Construction | AST $\rightarrow$ NFA Conversion, Powerset $\epsilon$-Closure |
| **Module 3** (Regular Expressions, RE $\leftrightarrow$ FA) | Regex Parser, AST Engine | Shunting-Yard Infix $\rightarrow$ Postfix, Concatenation Insertion |

---

## 🏗️ System Architecture

```
User Regex ─▶ [Shunting-Yard Parser] ─▶ [AST] ─▶ [Thompson Construction] ─▶ NFA (ε-transitions)
                                                                                  │
                                                                 [Subset Construction (powerset)]
                                                                                  │
                                                                                  ▼
                                                                                 DFA
                                                                                  │
                                                                [Hopcroft's Minimization]
                                                                                  │
                                                                                  ▼
                                                                           Minimal DFA
                                                                                  │
Log File ──▶ [Streaming DFA Scanner Engine] ◀─────────────────────────────────────┘
                     │
                     ├──▶ Matches + Highlighted Log Output
                     ├──▶ [Visualizer] — Graphviz State Diagram
                     └──▶ [Benchmark Engine] — Latency & ReDoS comparison vs Python `re`
```

Detailed architectural specifications, dataflow models, and component designs can be found in the **[High-Level Design (HLD) Document](docs/HLD.md)**.

---

## 🧩 Subsystem Breakdown

1. **Regex Parser (`src/parser.py`)**: Converts regex syntax into an AST using Shunting-Yard infix-to-postfix conversion with explicit concatenation insertion (`.`). Supports union (`|`), Kleene star (`*`), plus (`+`), optional (`?`), character classes (`[a-z]`), escapes, and wildcards (`.`).
2. **Thompson Construction (`src/thompson.py`)**: Walks the AST to build canonical NFA fragments for base symbols and operators.
3. **Subset Construction (`src/subset.py`)**: Computes $\epsilon$-closures of NFA state sets to build deterministic DFA state transition tables.
4. **Hopcroft Minimization (`src/hopcroft.py`)**: Refines state partitions in $O(n \log n)$ time to construct the minimal state DFA.
5. **DFA Scanner (`src/scanner.py`)**: Streams log text char-by-char, tracking current DFA state transitions and recording match indices.
6. **Visualizer (`src/visualizer.py`)**: Renders DFA state graphs using Graphviz DOT syntax with double-circled accept states.
7. **Benchmark Suite (`src/benchmark.py`)**: Executes comparative timing and memory usage tests against Python `re`.
8. **Web Interface (`app.py`)**: Interactive Streamlit dashboard for real-time regex testing, log uploading, visual graph inspection, and benchmark execution.

---

## 🛠️ Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Core Programming | Python 3.10+ | Algorithm implementation and data structure handling |
| Graph Visualization | Graphviz | Automated layout and rendering of finite automata state diagrams |
| UI Framework | Streamlit | Web dashboard for live regex scanning and visualization |
| Benchmarking | `timeit` + `matplotlib` | High-resolution execution timing and visualization charts |
| Automated Testing | `pytest` | Unit testing of automata transformations and textbook DFAs |

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10 or higher
- Graphviz system binary (installed and available in system PATH)

### Installation
```bash
# Clone the repository
git clone https://github.com/YOGESH-08/Logtron.git
cd Logtron

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

# Install dependencies (once requirements.txt is generated)
pip install -r requirements.txt
```

---

## 📚 Documentation Links

- **[High-Level Design (HLD)](docs/HLD.md)** — Architectural design, module responsibilities, NFRs, and course alignment.
