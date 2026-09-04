"""LogScan DFA — Professional Enterprise Web Application."""

import html
import time

import pandas as pd
import streamlit as st

from benchmark.benchmark_runner import BenchmarkRunner
from core.hopcroft import minimize_dfa
from core.regex_parser import RegexParser
from core.scanner import DFAScanner
from core.subset import nfa_to_dfa
from core.thompson import regex_to_nfa
from visualization.graph_visualizer import visualize_dfa, visualize_nfa

st.set_page_config(
    page_title="LogScan DFA — Log Pattern Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Modern Enterprise Dark Dashboard & Hiding Streamlit Branding
st.markdown(
    """
    <style>
    /* Hide Deploy Button & Footer only */
    #MainMenu {display: none !important;}
    footer {display: none !important;}
    .stDeployButton {display: none !important;}

    /* Sidebar & Sidebar Expand/Collapse Toggle Button Styling */
    section[data-testid="stSidebar"] {
        background-color: #0D1117 !important;
        border-right: 1px solid #30363D !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        visibility: visible !important;
        z-index: 999999 !important;
        margin-top: 5px !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button {
        color: #F0F6FC !important;
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
    }

    /* Main Layout Container */
    .main .block-container {
        padding-top: 1rem !important;
        margin-top: 0px !important;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    /* Metric Cards Styling */
    [data-testid="stMetric"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 14px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }

    [data-testid="stMetricLabel"] {
        color: #8B949E !important;
        font-size: 0.82rem !important;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    [data-testid="stMetricValue"] {
        color: #58A6FF !important;
        font-size: 1.45rem !important;
        font-weight: 700;
    }

    /* Segmented Navigation Tab Bar Styling */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        justify-content: center;
        gap: 10px;
        background-color: #161B22;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #30363D;
        margin-top: 15px;
        margin-bottom: 25px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 8px;
        padding: 0 22px;
        font-size: 14px;
        font-weight: 600;
        color: #8B949E;
        border: none !important;
        transition: all 0.15s ease-in-out;
    }

    .stTabs [aria-selected="true"] {
        background-color: #21262D !important;
        color: #58A6FF !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0D1117;
        border-right: 1px solid #30363D;
    }
    
    /* Primary Action Buttons */
    div.stButton > button[kind="primary"] {
        background-color: #238636 !important;
        border: 1px solid rgba(240, 246, 252, 0.1) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        padding: 6px 20px !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #2EA043 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Centered Hero Header Section
st.markdown(
    """
    <div style="text-align: center; padding: 0px 0 10px 0;">
        <h1 style="font-size: 2.6rem; font-weight: 800; letter-spacing: -0.5px; color: #F0F6FC; margin:0;">
            LogScan DFA
        </h1>
        <p style="color: #8B949E; font-size: 0.95rem; max-width: 680px; margin: 0 auto; line-height: 1.5;">
            High-Performance Log Pattern Analyzer using Regular Expressions and Finite Automata | Course: BITE306L
        </p>
    </div>
    """,
    unsafe_allow_html=True,
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
st.sidebar.header("Configuration")

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
st.sidebar.subheader("Input Source")
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
st.sidebar.subheader("Scanner Settings")
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
    st.error(f"Automata Pipeline Construction Error: {pipeline_error}")


# Main App Segmented Navigation Tabs
tab1, tab2, tab3 = st.tabs(
    [
        "Match Results",
        "DFA Visualizer",
        "ReDoS Benchmark",
    ]
)

# -----------------------------------------------------------------------------
# TAB 1: Match Results
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Log Scan & Match Highlighting")

    if pipeline_error:
        st.warning("Please correct the regular expression pattern in the sidebar configuration.")
    elif not log_content:
        st.info("Please enter or upload log content in the sidebar to run the scan.")
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

        st.markdown("#### Highlighted Log Payload Viewer")

        # Construct line-numbered, IDE-styled HTML view
        spans = scanner.find_matches(log_content, overlapping=False, longest=longest_match)
        lines = log_content.splitlines()

        line_offsets = []
        curr = 0
        for line in lines:
            line_offsets.append((curr, curr + len(line)))
            curr += len(line) + 1  # account for newline

        html_lines = []
        for idx, (l_start, l_end) in enumerate(line_offsets, start=1):
            line_str = log_content[l_start:l_end]
            line_spans = [
                (max(0, s - l_start), min(len(line_str), e - l_start))
                for s, e in spans
                if s < l_end and e > l_start
            ]

            line_html = ""
            last = 0
            for ms, me in line_spans:
                line_html += html.escape(line_str[last:ms])
                matched_text = html.escape(line_str[ms:me])
                line_html += (
                    f'<mark style="background: rgba(255, 213, 79, 0.22); color: #FFE082; '
                    f'border: 1px solid rgba(255, 213, 79, 0.55); border-radius: 4px; '
                    f'padding: 1px 5px; font-weight: 700; box-shadow: 0 0 8px rgba(255, 213, 79, 0.15);">'
                    f"{matched_text}</mark>"
                )
                last = me
            line_html += html.escape(line_str[last:])

            line_num_html = (
                f'<span style="color: #484F58; user-select: none; min-width: 35px; '
                f'display: inline-block; text-align: right; padding-right: 15px; '
                f'font-family: Consolas, Monaco, monospace; font-size: 13px;">{idx}</span>'
            )
            html_lines.append(
                f'<div style="line-height: 1.6; font-family: \'Fira Code\', Consolas, Monaco, monospace; '
                f'font-size: 13.5px; white-space: pre-wrap; word-break: break-all;">'
                f"{line_num_html}{line_html}</div>"
            )

        log_body_html = "\n".join(html_lines) if html_lines else html.escape(log_content)

        terminal_html = f"""
        <div style="background-color: #0D1117; border: 1px solid #30363D; border-radius: 10px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35); overflow: hidden; margin-top: 10px; margin-bottom: 20px;">
            <div style="background-color: #161B22; border-bottom: 1px solid #30363D; padding: 10px 16px; display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="height: 12px; width: 12px; background-color: #FF5F56; border-radius: 50%; display: inline-block;"></span>
                    <span style="height: 12px; width: 12px; background-color: #FFBD2E; border-radius: 50%; display: inline-block;"></span>
                    <span style="height: 12px; width: 12px; background-color: #27C93F; border-radius: 50%; display: inline-block;"></span>
                    <span style="color: #8B949E; font-family: monospace; font-size: 12.5px; margin-left: 10px; font-weight: 500;">logscan_output.log — {len(lines)} lines</span>
                </div>
                <div style="background-color: rgba(255, 213, 79, 0.15); color: #FFE082; border: 1px solid rgba(255, 213, 79, 0.4); padding: 3px 10px; border-radius: 12px; font-size: 12px; font-family: monospace; font-weight: 600;">
                    {len(matches)} Matches Highlighted
                </div>
            </div>
            <div style="padding: 16px; max-height: 480px; overflow-y: auto; background-color: #0D1117; color: #E6EDF3;">
                {log_body_html}
            </div>
        </div>
        """

        st.markdown(terminal_html, unsafe_allow_html=True)

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
# TAB 2: Automata Visualizer
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

        vtab1, vtab2, vtab3 = st.tabs(
            [
                "Thompson NFA",
                "Powerset DFA",
                "Hopcroft Minimal DFA",
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

# -----------------------------------------------------------------------------
# TAB 3: ReDoS Performance Benchmark
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

        if st.button("Run Scaling Benchmark", type="primary"):
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
                            "LogScan DFA (ms)": m.dfa_scanner_time_ms,
                            "Python re (ms)": m.python_re_time_ms,
                            "DFA Matches": m.dfa_scanner_matches,
                            "Python re Matches": m.python_re_matches,
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



st.markdown("---")
st.caption("LogScan DFA | Course Project for BITE306L — Theory of Computation")
