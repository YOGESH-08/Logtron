"""LogScan DFA — Streamlit Web Application."""

import html
import time

import pandas as pd
import streamlit as st

from benchmark.benchmark_runner import BenchmarkRunner
from core.hopcroft import minimize_dfa
from core.regex_parser import RegexParser, RegexSyntaxError, ast_to_string
from core.scanner import DFAScanner
from core.subset import nfa_to_dfa
from core.thompson import regex_to_nfa
from visualization.graph_visualizer import visualize_dfa, visualize_nfa

st.set_page_config(
    page_title="LogScan DFA — Log Pattern Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Header Section
st.title("🔍 LogScan DFA")
st.caption(
    "High-Performance Log Pattern Analyzer using Regular Expressions and Finite Automata | Course: BITE306L (TOC)"
)

st.markdown(
    """
---
### Overview
**LogScan DFA** converts regular expressions into minimal Deterministic Finite Automata (DFA) using 
**Thompson Construction**, **Subset Construction**, and **Hopcroft's Minimization Algorithm**. 
It replaces standard NFA backtracking with guaranteed **$O(n)$ linear-time streaming log scanning**, 
immunizing log engines against Catastrophic Backtracking (ReDoS).
"""
)

# Initialize Session State for Preset Patterns
if "pattern_input" not in st.session_state:
    st.session_state["pattern_input"] = "(ERROR|WARN).*"


def on_preset_change():
    selected = st.session_state.get("preset_select", "Custom")
    if selected == "Apache Error Logs: (ERROR|WARN).*":
        st.session_state["pattern_input"] = "(ERROR|WARN).*"
    elif selected == "IP Address: [0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+":
        st.session_state["pattern_input"] = r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"
    elif selected == "Status Codes (4xx/5xx): (4|5)[0-9][0-9]":
        st.session_state["pattern_input"] = "(4|5)[0-9][0-9]"
    elif selected == "ReDoS Pattern Test: (a+)+b":
        st.session_state["pattern_input"] = "(a+)+b"


# Sidebar Controls
st.sidebar.header("⚙️ Configuration")

preset_option = st.sidebar.selectbox(
    "Sample Presets",
    [
        "Custom",
        "Apache Error Logs: (ERROR|WARN).*",
        "IP Address: [0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+",
        "Status Codes (4xx/5xx): (4|5)[0-9][0-9]",
        "ReDoS Pattern Test: (a+)+b",
    ],
    key="preset_select",
    on_change=on_preset_change,
)

regex_input = st.sidebar.text_input(
    "Regular Expression Pattern",
    key="pattern_input",
    help="Enter regular expression (e.g. (ERROR|WARN).*, [0-9]+, a(b|c)*)",
)

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Input Source")
input_mode = st.sidebar.radio(
    "Select Input Mode",
    ["Sample Text", "Preset Log Files", "Upload Log File"],
)

if input_mode == "Sample Text":
    log_content = st.sidebar.text_area(
        "Sample Log Payload",
        value="""2026-08-18 10:15:30 [INFO] System initialized successfully.
2026-08-18 10:15:32 [WARN] High memory usage detected (85%).
2026-08-18 10:15:35 [ERROR] Database connection failed: Connection refused (500).
2026-08-18 10:15:40 [INFO] Retrying connection (attempt 1/3)...
2026-08-18 10:15:45 [ERROR] Critical storage failure on node-04 (404).""",
        height=180,
    )
elif input_mode == "Preset Log Files":
    preset_file = st.sidebar.selectbox(
        "Select Sample Log File",
        [
            "Apache Access Log (sample_logs/apache_access.log)",
            "Syslog Authentication Log (sample_logs/syslog_auth.log)",
            "App Server Log (sample_logs/app_server.log)",
            "Database Audit Log (sample_logs/db_audit.log)",
        ],
    )
    file_map = {
        "Apache Access Log (sample_logs/apache_access.log)": "sample_logs/apache_access.log",
        "Syslog Authentication Log (sample_logs/syslog_auth.log)": "sample_logs/syslog_auth.log",
        "App Server Log (sample_logs/app_server.log)": "sample_logs/app_server.log",
        "Database Audit Log (sample_logs/db_audit.log)": "sample_logs/db_audit.log",
    }
    filepath = file_map[preset_file]
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            log_content = f.read()
    except Exception as exc:
        st.error(f"Error loading {filepath}: {exc}")
        log_content = ""
else:
    uploaded_file = st.sidebar.file_uploader("Upload Log File", type=["log", "txt"])
    if uploaded_file is not None:
        log_content = uploaded_file.read().decode("utf-8")
    else:
        log_content = ""

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Scanner Settings")
overlapping = st.sidebar.checkbox("Allow Overlapping Matches", value=False)
longest_match = st.sidebar.checkbox("Find Longest Match per Position", value=True)


# Build Automata Pipeline
pipeline_error = None
ast = None
nfa = None
dfa = None
minimal_dfa = None
scanner = None

if regex_input:
    try:
        parser = RegexParser(regex_input)
        ast = parser.parse()
        nfa = regex_to_nfa(regex_input)
        dfa = nfa_to_dfa(nfa)
        minimal_dfa = minimize_dfa(dfa)
        scanner = DFAScanner(minimal_dfa)
    except Exception as exc:
        pipeline_error = str(exc)

if pipeline_error:
    st.error(f"❌ Automata Pipeline Construction Error: {pipeline_error}")


# Main App Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🎯 Match Results",
        "📊 DFA Visualizer",
        "⚡ ReDoS Benchmark",
        "📘 Architecture & Theory",
    ]
)

# -----------------------------------------------------------------------------
# TAB 1: Match Results (Developer 1 - Yogesh Task)
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Log Scan & Match Highlighting")

    if pipeline_error:
        st.warning("⚠️ Please correct the regular expression pattern in the sidebar configuration.")
    elif not log_content:
        st.info("ℹ️ Please enter or upload log content in the sidebar to run the scan.")
    else:
        start_time = time.perf_counter()
        matches = scanner.find_match_objects(
            log_content, overlapping=overlapping, longest=longest_match
        )
        end_time = time.perf_counter()
        scan_time_ms = (end_time - start_time) * 1000.0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Matches Found", len(matches))
        with col2:
            st.metric("Log Size", f"{len(log_content.encode('utf-8'))} bytes")
        with col3:
            st.metric("Scan Execution Time", f"{scan_time_ms:.3f} ms")
        with col4:
            st.metric("Minimal DFA States", len(minimal_dfa.states))

        st.markdown("#### Highlighted Log Payload")

        # Construct non-overlapping HTML highlighted view
        spans = scanner.find_matches(log_content, overlapping=False, longest=longest_match)
        highlighted_html = ""
        last_idx = 0
        for s, e in spans:
            highlighted_html += html.escape(log_content[last_idx:s])
            matched_slice = html.escape(log_content[s:e])
            highlighted_html += (
                f'<mark style="background-color: #FFE082; color: #000000; '
                f'padding: 2px 4px; border-radius: 4px; font-weight: bold;">'
                f"{matched_slice}</mark>"
            )
            last_idx = e
        highlighted_html += html.escape(log_content[last_idx:])

        st.markdown(
            f'<pre style="background-color: #0E1117; color: #FAFAFA; padding: 15px; '
            f'border-radius: 8px; font-family: monospace; white-space: pre-wrap; '
            f'line-height: 1.5;">{highlighted_html}</pre>',
            unsafe_allow_html=True,
        )

        if matches:
            st.markdown("#### Match Spans Summary")
            match_data = [
                {
                    "Index": i + 1,
                    "Start": m.start,
                    "End": m.end,
                    "Length": m.end - m.start,
                    "Matched Segment": m.text,
                }
                for i, m in enumerate(matches)
            ]
            st.dataframe(pd.DataFrame(match_data), use_container_width=True)
        else:
            st.info("No matching pattern instances found in the provided log payload.")

# -----------------------------------------------------------------------------
# TAB 2: Automata Visualizer (Developer 2 - Teammate Task)
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("Automata Pipeline Visualization")

    if pipeline_error or not nfa or not dfa or not minimal_dfa:
        st.warning("Automata visualization available once valid regex is entered.")
    else:
        state_reduction = (
            round((1 - len(minimal_dfa.states) / len(dfa.states)) * 100, 1)
            if len(dfa.states) > 0
            else 0.0
        )

        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            st.metric("NFA States", len(nfa.states))
        with mcol2:
            st.metric("DFA States", len(dfa.states))
        with mcol3:
            st.metric("Minimized DFA States", len(minimal_dfa.states))
        with mcol4:
            st.metric("Hopcroft Reduction", f"{state_reduction}%")

        vtab1, vtab2, vtab3, vtab4 = st.tabs(
            [
                "1️⃣ Thompson ε-NFA",
                "2️⃣ Powerset DFA",
                "3️⃣ Hopcroft Minimal DFA",
                "🌳 Abstract Syntax Tree",
            ]
        )

        with vtab1:
            st.markdown("**Thompson Construction ε-NFA Diagram**")
            st.graphviz_chart(visualize_nfa(nfa))

        with vtab2:
            st.markdown("**Subset Construction Powerset DFA Diagram**")
            st.graphviz_chart(visualize_dfa(dfa, title="Powerset DFA"))

        with vtab3:
            st.markdown("**Hopcroft Minimal State DFA Diagram**")
            st.graphviz_chart(visualize_dfa(minimal_dfa, title="Minimal DFA"))

        with vtab4:
            st.markdown("**Abstract Syntax Tree (AST)**")
            if ast:
                st.code(ast_to_string(ast), language="text")

# -----------------------------------------------------------------------------
# TAB 3: ReDoS Performance Benchmark (Developer 2 - Teammate Task)
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Performance Benchmark vs Python `re` Engine")

    if pipeline_error:
        st.warning("Please enter a valid regular expression to run benchmarks.")
    else:
        st.write(
            "Compare execution efficiency between Python's standard backtracking `re` module "
            "and LogScan's deterministic linear-time DFA scanner."
        )
        st.caption(
            "Python `re` is executed in a subprocess with a 2 second timeout for safer ReDoS demonstrations."
        )

        if st.button("🚀 Run Scaling Benchmark", type="primary"):
            with st.spinner("Executing benchmarks across scaled log payloads..."):
                runner = BenchmarkRunner(regex_input, re_timeout_seconds=2.0)
                suite = runner.run_scaling_benchmark(
                    log_content, scales=[1, 2, 5, 10, 20, 50, 100, 250, 500]
                )

                df_metrics = pd.DataFrame(
                    [
                        {
                            "Input Size": m.input_size_label,
                            "Bytes": m.input_size_bytes,
                            "Python re Status": m.python_re_status,
                            "LogScan DFA (ms)": m.python_re_time_ms,
                            "Python re (ms)": m.dfa_scanner_time_ms,
                            "DFA Matches": m.python_re_matches,
                            "Python re Matches": m.dfa_scanner_matches,
                            "DFA Speedup Factor": (
                                f">= {m.speedup_ratio}x"
                                if m.python_re_timed_out
                                else f"{m.speedup_ratio}x"
                            ),
                        }
                        for m in suite.metrics
                    ]
                )

                st.markdown("#### Benchmark Results Table")
                st.dataframe(df_metrics, use_container_width=True)

                chart_data = df_metrics.set_index("Input Size")[
                    ["LogScan DFA (ms)", "Python re (ms)"]
                ]
                st.markdown("#### Execution Time Comparison (ms)")
                st.bar_chart(chart_data)

# -----------------------------------------------------------------------------
# TAB 4: Architecture & Theory (Developer 2 - Teammate Task)
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("Theory of Computation (BITE306L) Mapping")

    st.markdown(
        """
    | Pipeline Stage | Module | Theoretical Algorithm / Concept |
    |---|---|---|
    | **1. Regex Parsing** | `core/regex_parser.py` | Shunting-Yard Infix $\\rightarrow$ Postfix Conversion, Explicit Concatenation Insertion |
    | **2. NFA Construction** | `core/thompson.py` | Thompson Construction Algorithm with $\\epsilon$-transitions |
    | **3. Powerset DFA** | `core/subset.py` | Subset Construction, $\\epsilon$-Closure Computation |
    | **4. DFA Minimization** | `core/hopcroft.py` | Hopcroft Partition Refinement Algorithm ($O(n \\log n)$) |
    | **5. Log Scanning** | `core/scanner.py` | Deterministic Finite State Machine Input Pass ($O(n)$) |
    | **6. Visualizer** | `visualization/graph_visualizer.py` | Graphviz Automata State Diagram Rendering |
    | **7. Benchmarking** | `benchmark/benchmark_runner.py` | Linear DFA vs Backtracking ReDoS Performance Analysis |
    """
    )

    st.markdown("#### Viva Guide")

    with st.expander("Regex Parser to AST", expanded=True):
        st.markdown(
            """
            The parser converts the regex into typed tokens, inserts explicit concatenation,
            converts infix notation to postfix using operator precedence, and builds an AST.
            This makes the later automata stages operate on a clear formal structure.
            """
        )

    with st.expander("Thompson Construction"):
        st.markdown(
            """
            Each AST node becomes an epsilon-NFA fragment with one start state and one accept
            state. Concatenation connects fragments, union creates two epsilon branches, and
            repetition operators add loop and bypass epsilon transitions.
            """
        )

    with st.expander("Subset Construction"):
        st.markdown(
            """
            A DFA state represents a set of NFA states. The start state is the epsilon-closure
            of the NFA start state. For every input symbol, the algorithm applies move followed
            by epsilon-closure and creates a new DFA state for each unseen set.
            """
        )

    with st.expander("Hopcroft Minimization"):
        st.markdown(
            """
            Hopcroft's algorithm starts with accepting and non-accepting partitions. A worklist
            repeatedly chooses splitter sets and refines partitions whose transitions behave
            differently. States left in the same final partition are language-equivalent.
            """
        )

    with st.expander("DFA Scanner and Benchmark"):
        st.markdown(
            """
            The scanner advances deterministically through the minimal DFA and records accepted
            spans. The benchmark compares Python re.finditer with the DFA scanner using a
            timeout-limited Python re subprocess for safer ReDoS demonstrations.
            """
        )

st.markdown("---")
st.caption("LogScan DFA | Course Project for BITE306L — Theory of Computation")
