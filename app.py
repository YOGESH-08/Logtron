import streamlit as st

st.set_page_config(
    page_title="LogScan DFA — Log Pattern Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header Section
st.title("🔍 LogScan DFA")
st.caption("High-Performance Log Pattern Analyzer using Regular Expressions and Finite Automata | Course: BITE306L (TOC)")

st.markdown("""
---
### Overview
**LogScan DFA** converts regular expressions into minimal Deterministic Finite Automata (DFA) using **Thompson Construction**, **Subset Construction**, and **Hopcroft's Minimization Algorithm**. It replaces standard NFA backtracking with guaranteed **$O(n)$ linear-time streaming log scanning**, immunizing systems against Catastrophic Backtracking (ReDoS).
""")

# Sidebar Controls
st.sidebar.header("⚙️ Configuration")

regex_input = st.sidebar.text_input(
    "Regular Expression Pattern",
    value="(ERROR|WARN).*",
    help="Enter standard regex pattern (e.g. (a|b)*abb, ERROR.*404, [0-9]+)"
)

preset_option = st.sidebar.selectbox(
    "Sample Presets",
    [
        "Custom",
        "Apache Error Logs: (ERROR|WARN).*",
        "IP Address: [0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+",
        "ReDoS Test (Catastrophic NFA): (a+)+b"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Input Source")
input_mode = st.sidebar.radio("Select Input Mode", ["Sample Text", "Upload Log File"])

if input_mode == "Sample Text":
    log_content = st.sidebar.text_area(
        "Sample Log Payload",
        value="""2026-08-18 10:15:30 [INFO] System initialized successfully.
2026-08-18 10:15:32 [WARN] High memory usage detected (85%).
2026-08-18 10:15:35 [ERROR] Database connection failed: Connection refused.
2026-08-18 10:15:40 [INFO] Retrying connection (attempt 1/3)...
2026-08-18 10:15:45 [ERROR] Critical storage failure on node-04.""",
        height=150
    )
else:
    uploaded_file = st.sidebar.file_uploader("Upload Log File", type=["log", "txt"])
    if uploaded_file is not None:
        log_content = uploaded_file.read().decode("utf-8")
    else:
        log_content = ""

# Main App Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Match Results", 
    "📊 DFA Visualizer", 
    "⚡ ReDoS Benchmark", 
    "📘 Architecture & Theory"
])

with tab1:
    st.subheader("Log Scan Results")
    if st.button("🚀 Run LogScan DFA", type="primary"):
        st.info("Scanner Engine initialization pending core module implementation.")
        st.code(log_content, language="text")

with tab2:
    st.subheader("Automata Visualization")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("NFA States", "—")
    with col2:
        st.metric("DFA States", "—")
    with col3:
        st.metric("Minimized DFA States", "—")
    
    st.info("Automata Graphviz visualizer pending core module implementation.")

with tab3:
    st.subheader("Performance Benchmark vs Python `re` Engine")
    st.info("Benchmark harness pending core module implementation.")

with tab4:
    st.subheader("Theory of Computation (BITE306L) Mapping")
    st.markdown("""
    | Stage | Module | Theory Concept |
    |---|---|---|
    | 1. Regex $\\rightarrow$ AST | Module 3 | Shunting-Yard Parser, Explicit Concat Insertion |
    | 2. AST $\\rightarrow$ NFA | Module 2 | Thompson Construction with $\\epsilon$-transitions |
    | 3. NFA $\\rightarrow$ DFA | Module 2 | Subset Construction & $\\epsilon$-closure Powerset Mapping |
    | 4. DFA $\\rightarrow$ MinDFA | Module 1 | Hopcroft's $O(n \\log n)$ Partition Refinement Algorithm |
    | 5. Log Scanning | Module 1 | Streaming $O(n)$ Character-by-Character State Machine Pass |
    """)

st.markdown("---")
st.caption("LogScan DFA Prototype | Theory of Computation Course Project")
