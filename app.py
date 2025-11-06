import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import datetime
from engine import BacteriaIdentifier

# --- CONFIG ---
st.set_page_config(page_title="BactAI-d Assistant", layout="wide")
st.title("🧫 BactAI-d — Intelligent Bacterial Identification Assistant")

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

# --- SESSION STATE ---
if "user_input" not in st.session_state:
    st.session_state.user_input = {}
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

# --- INPUT FORM ---
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
            field, ["Unknown"] + all_vals
        )
    elif field == "Growth Temperature":
        st.session_state.user_input[field] = st.sidebar.text_input(field, "")
    else:
        st.session_state.user_input[field] = st.sidebar.selectbox(
            field, ["Unknown", "Positive", "Negative", "Variable"]
        )

# --- RESET BUTTON ---
if st.sidebar.button("🔄 Reset All Inputs"):
    for k in st.session_state.user_input.keys():
        st.session_state.user_input[k] = "Unknown"
    st.experimental_rerun()

# --- IDENTIFY BUTTON ---
if st.sidebar.button("🔍 Identify"):
    with st.spinner("Analyzing results..."):
        results = eng.identify(st.session_state.user_input)
        if isinstance(results, list):
            try:
                results = pd.DataFrame(results, columns=["Genus", "Confidence (%)"])
            except:
                results = pd.DataFrame()
        st.session_state.results = results

# --- COLOUR MAPPING FUNCTION ---
def color_confidence(val):
    if isinstance(val, str):
        if "High" in val:
            return "background-color: #b5e7a0"  # green
        elif "Moderate" in val:
            return "background-color: #fff5ba"  # yellow
        elif "Low" in val:
            return "background-color: #ffd6a5"  # orange
        else:
            return "background-color: #f8a5a5"  # red
    return ""

# --- DISPLAY RESULTS ---
if isinstance(st.session_state.results, pd.DataFrame) and not st.session_state.results.empty:
    st.success("Top Possible Matches:")

    # Summary table
    styled_table = st.session_state.results.style.applymap(color_confidence, subset=["Confidence Level"])
    st.dataframe(styled_table, use_container_width=True)

    # Expanders with reasoning
    for _, row in st.session_state.results.iterrows():
        header = f"**{row['Genus']}** — {row['Confidence Level']} ({row['Confidence (%)']}%)"
        with st.expander(header):
            st.markdown(f"**🧠 AI Reasoning:** {row['AI Reasoning']}")
            st.markdown(f"**🧪 Next Step:** {row['Next Test Suggestion']}")
            if row['Extra Notes']:
                st.markdown(f"**🧾 Notes:** {row['Extra Notes']}")

else:
    st.warning("Enter results and click **Identify** to begin analysis.")

# --- PDF EXPORT SECTION ---

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
        pdf.multi_cell(0, 8, safe_text(f"Reasoning: {row['AI Reasoning']}"))
        pdf.multi_cell(0, 8, safe_text(f"Next Step: {row['Next Test Suggestion']}"))
        if row['Extra Notes']:
            pdf.multi_cell(0, 8, safe_text(f"Notes: {row['Extra Notes']}"))
        pdf.ln(4)

    output_path = "BactAI-D_Report.pdf"
    pdf.output(output_path)
    return output_path

# --- PDF BUTTON ---
if isinstance(st.session_state.results, pd.DataFrame) and not st.session_state.results.empty:
    if st.button("📄 Export Results to PDF"):
        pdf_path = export_pdf(st.session_state.results, st.session_state.user_input)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name="BactAI-D_Report.pdf")
