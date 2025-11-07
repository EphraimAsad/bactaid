import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import datetime
from engine import BacteriaIdentifier

# --- PAGE CONFIG ---
st.set_page_config(page_title="BactAI-D Assistant", layout="wide")
st.title("🧫 BactAI-D — Intelligent Bacterial Identification Assistant")

# --- LOAD DATABASE ---
@st.cache_data
def load_data():
    data_path = os.path.join("bacteria_db.xlsx")
    try:
        return pd.read_excel(data_path)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

db = load_data()
eng = BacteriaIdentifier(db)

# --- SESSION STATE INIT ---
if "user_input" not in st.session_state:
    st.session_state.user_input = {}
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

# --- SIDEBAR INPUTS ---
st.sidebar.header("Input Biochemical & Morphological Results")

for field in eng.db.columns:
    if field == "Genus":
        continue
    if field in ["Colony Morphology", "Media Grown On", "Oxygen Requirement", "Shape", "Haemolysis Type"]:
        all_vals = []
        for v in eng.db[field]:
            parts = re.split(r"[;/]", str(v))
            for p in parts:
                clean = p.strip()
                if clean and clean not in all_vals:
                    all_vals.append(clean)
        all_vals.sort()
        st.session_state.user_input[field] = st.sidebar.selectbox(
            field,
            ["Unknown"] + all_vals,
            key=field
        )
    elif field == "Growth Temperature":
        st.session_state.user_input[field] = st.sidebar.text_input(field, "", key=field)
    else:
        st.session_state.user_input[field] = st.sidebar.selectbox(
            field, ["Unknown", "Positive", "Negative", "Variable"], key=field
        )

# --- RESET BUTTON ---
if st.sidebar.button("🔄 Reset All Inputs"):
    for key in list(st.session_state.user_input.keys()):
        st.session_state.user_input[key] = "Unknown"
    st.session_state.results = pd.DataFrame()
    st.toast("✅ All inputs reset successfully", icon="🔁")
    st.experimental_set_query_params(reset="1")
    st.rerun()

# --- IDENTIFY BUTTON ---
if st.sidebar.button("🔍 Identify"):
    with st.spinner("Analyzing results..."):
        results = eng.identify(st.session_state.user_input)
        st.session_state.results = results

# --- COLOR MAP FUNCTION ---
def confidence_color(level):
    level = level.lower()
    if "very high" in level:
        return "#2ecc71"   # green
    elif "high" in level:
        return "#f1c40f"   # yellow
    elif "moderate" in level:
        return "#e67e22"   # orange
    elif "low" in level:
        return "#e74c3c"   # red
    return "#bdc3c7"       # grey fallback

# --- DISPLAY RESULTS ---
if isinstance(st.session_state.results, pd.DataFrame) and not st.session_state.results.empty:
    st.success("### Top Possible Matches:")

    for idx, row in st.session_state.results.iterrows():
        genus = row["Genus"]
        conf_pct = row["Confidence (%)"]
        conf_lvl = row["Confidence Level"]
        color = confidence_color(conf_lvl)

        # Header with colored badge
        header_html = f"""
        <div style='background-color:{color}; padding:8px; border-radius:8px; margin-bottom:4px;'>
            <strong>{idx+1}. {genus}</strong> — {conf_lvl} ({conf_pct}%)
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)

        with st.expander("Details & Reasoning"):
            st.markdown(f"**Reasoning:** {row['Reasoning']}")
            st.markdown(f"**Next Step:** {row['Next Step Suggestion']}")
            if row['Extra Notes']:
                st.markdown(f"**Notes:** {row['Extra Notes']}")

else:
    st.info("Enter your results on the left and click **Identify** to begin analysis.")

# --- PDF EXPORT ---
def safe_text(s):
    """Ensure unicode characters are encoded safely for PDF output."""
    return str(s).encode('latin-1', 'replace').decode('latin-1')

def export_pdf(df, user_input):
    """Generate a Unicode-safe PDF report."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    pdf.cell(0, 10, "BactAI-d Identification Report", ln=True, align="C")
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, "Entered Biochemical Results:", ln=True)
    for k, v in user_input.items():
        pdf.cell(0, 8, safe_text(f"{k}: {v}"), ln=True)
    pdf.ln(10)

    for _, row in df.iterrows():
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, safe_text(f"{row['Genus']} — {row['Confidence Level']} ({row['Confidence (%)']}%)"), ln=True)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 8, safe_text(f"Reasoning: {row['Reasoning']}"))
        pdf.multi_cell(0, 8, safe_text(f"Next Step: {row['Next Step Suggestion']}"))
        if row['Extra Notes']:
            pdf.multi_cell(0, 8, safe_text(f"Notes: {row['Extra Notes']}"))
        pdf.ln(4)

    output_path = "BactAI-D_Report.pdf"
    pdf.output(output_path)
    return output_path

# --- PDF DOWNLOAD ---
if isinstance(st.session_state.results, pd.DataFrame) and not st.session_state.results.empty:
    if st.button("📄 Export Results to PDF"):
        pdf_path = export_pdf(st.session_state.results, st.session_state.user_input)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name="BactAI-D_Report.pdf")

# --- FOOTER ---
st.markdown(
    """
    <hr style="margin-top:50px; margin-bottom:10px;">
    <div style='text-align:center; color:gray; font-size:14px;'>
        Created by <strong>Zain</strong> — <em>BactAI-d Project</em> © 2025
    </div>
    """,
    unsafe_allow_html=True
)
