import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import datetime
from engine import BacteriaIdentifier

# --- CONFIG ---
st.set_page_config(page_title="BactAI-d Assistant", layout="wide")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    data_path = os.path.join("bacteria_db.xlsx")
    df = pd.read_excel(data_path)
    df.columns = [c.strip() for c in df.columns]
    return df

db = load_data()
eng = BacteriaIdentifier(db)

# --- PAGE HEADER ---
st.title("🧫 BactAI-d: Intelligent Bacteria Identification Assistant")
st.markdown("Use the sidebar to input your biochemical and morphological results.")

# --- FIELD GROUPS ---
MORPH_FIELDS = ["Gram Stain", "Shape", "Colony Morphology", "Media Grown On", "Motility", "Capsule", "Spore Formation"]
ENZYME_FIELDS = ["Catalase", "Oxidase", "Coagulase", "Lipase Test"]
SUGAR_FIELDS = [
    "Glucose Fermentation", "Lactose Fermentation", "Sucrose Fermentation", "Maltose Fermentation",
    "Mannitol Fermentation", "Sorbitol Fermentation", "Xylose Fermentation", "Rhamnose Fermentation",
    "Arabinose Fermentation", "Raffinose Fermentation", "Trehalose Fermentation", "Inositol Fermentation"
]

# --- SESSION STATE ---
if "user_input" not in st.session_state:
    st.session_state.user_input = {}
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

# --- RESET TRIGGER HANDLER (before widgets are created) ---
if "reset_trigger" in st.session_state and st.session_state["reset_trigger"]:
    for key in list(st.session_state.user_input.keys()):
        st.session_state.user_input[key] = "Unknown"

    for key in list(st.session_state.keys()):
        if key not in ["user_input", "results", "reset_trigger"]:
            if isinstance(st.session_state[key], list):
                st.session_state[key] = []
            else:
                st.session_state[key] = "Unknown"

    st.session_state["reset_trigger"] = False
    st.rerun()

# --- SIDEBAR HEADER ---
st.sidebar.markdown(
    """
    <div style='background-color:#1565C0; padding:12px; border-radius:10px;'>
        <h3 style='text-align:center; color:white; margin:0;'>🔬 Input Test Results</h3>
    </div>
    """,
    unsafe_allow_html=True
)

def get_unique_values(field):
    vals = []
    for v in eng.db[field]:
        parts = re.split(r"[;/]", str(v))
        for p in parts:
            clean = p.strip()
            if clean and clean not in vals:
                vals.append(clean)
    vals.sort()
    return vals

# --- SIDEBAR INPUTS ---
with st.sidebar.expander("🧫 Morphological Tests", expanded=True):
    for field in MORPH_FIELDS:
        if field in ["Shape", "Colony Morphology", "Media Grown On"]:
            options = get_unique_values(field)
            selected = st.multiselect(field, options, default=[], key=field)
            st.session_state.user_input[field] = "; ".join(selected) if selected else "Unknown"
        else:
            st.session_state.user_input[field] = st.selectbox(field, ["Unknown", "Positive", "Negative", "Variable"], index=0, key=field)

with st.sidebar.expander("🧪 Enzyme Tests", expanded=False):
    for field in ENZYME_FIELDS:
        st.session_state.user_input[field] = st.selectbox(field, ["Unknown", "Positive", "Negative", "Variable"], index=0, key=field)

with st.sidebar.expander("🍬 Carbohydrate Fermentation Tests", expanded=False):
    for field in SUGAR_FIELDS:
        st.session_state.user_input[field] = st.selectbox(field, ["Unknown", "Positive", "Negative", "Variable"], index=0, key=field)

with st.sidebar.expander("🧬 Other Tests", expanded=False):
    for field in db.columns:
        if field in ["Genus"] + MORPH_FIELDS + ENZYME_FIELDS + SUGAR_FIELDS:
            continue
        if field == "Haemolysis Type":
            options = get_unique_values(field)
            selected = st.multiselect(field, options, default=[], key=field)
            st.session_state.user_input[field] = "; ".join(selected) if selected else "Unknown"
        elif field == "Oxygen Requirement":
            options = get_unique_values(field)
            st.session_state.user_input[field] = st.selectbox(field, ["Unknown"] + options, index=0, key=field)
        elif field == "Growth Temperature":
            st.session_state.user_input[field] = st.text_input(field + " (°C)", "", key=field)
        else:
            st.session_state.user_input[field] = st.selectbox(field, ["Unknown", "Positive", "Negative", "Variable"], index=0, key=field)

# --- RESET BUTTON ---
if st.sidebar.button("🔄 Reset All Inputs"):
    st.session_state["reset_trigger"] = True
    st.rerun()

# --- IDENTIFY BUTTON ---
if st.sidebar.button("🔍 Identify"):
    with st.spinner("Analyzing results..."):
        results = eng.identify(st.session_state.user_input)
        if not results:
            st.error("No matches found.")
        else:
            results = pd.DataFrame(
                [
                    [
                        r.genus,
                        f"{r.confidence_percent()}%",
                        f"{r.true_confidence()}%",
                        r.reasoning_paragraph(results),
                        r.reasoning_factors.get("next_tests", ""),
                        r.extra_notes
                    ]
                    for r in results
                ],
                columns=["Genus", "Confidence", "True Confidence (All Tests)", "Reasoning", "Next Tests", "Extra Notes"],
            )
            st.session_state.results = results

# --- DISPLAY RESULTS ---
if not st.session_state.results.empty:
    st.info("Percentages based upon options entered. True confidence percentage shown within each expanded result.")
    for _, row in st.session_state.results.iterrows():
        confidence_value = int(row["Confidence"].replace("%", ""))
        confidence_color = "🟢" if confidence_value >= 75 else "🟡" if confidence_value >= 50 else "🔴"
        header = f"**{row['Genus']}** — {confidence_color} {row['Confidence']}"
        with st.expander(header):
            st.markdown(f"**Reasoning:** {row['Reasoning']}")
            st.markdown(f"**Top 3 Next Tests to Differentiate:** {row['Next Tests']}")
            st.markdown(f"**True Confidence (All Tests):** {row['True Confidence (All Tests)']}")
            if row["Extra Notes"]:
                st.markdown(f"**Notes:** {row['Extra Notes']}")

# --- PDF EXPORT ---
def export_pdf(results_df, user_input):
    def safe_text(text):
        """Convert text to Latin-1 safe characters."""
        text = str(text).replace("•", "-").replace("—", "-").replace("–", "-")
        return text.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "BactAI-d Identification Report", ln=True, align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Entered Test Results:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for k, v in user_input.items():
        pdf.multi_cell(0, 6, safe_text(f"- {k}: {v}"))

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top Possible Matches:", ln=True)
    pdf.set_font("Helvetica", "", 10)

    for _, row in results_df.iterrows():
        pdf.multi_cell(0, 7, safe_text(f"- {row['Genus']} — Confidence: {row['Confidence']} (True: {row['True Confidence (All Tests)']})"))
        pdf.multi_cell(0, 6, safe_text(f"  Reasoning: {row['Reasoning']}"))
        if row['Next Tests']:
            pdf.multi_cell(0, 6, safe_text(f"  Next Tests: {row['Next Tests']}"))
        if row['Extra Notes']:
            pdf.multi_cell(0, 6, safe_text(f"  Notes: {row['Extra Notes']}"))
        pdf.ln(3)

    pdf.output("BactAI-d_Report.pdf")
    return "BactAI-d_Report.pdf"

if not st.session_state.results.empty:
    if st.button("📄 Export Results to PDF"):
        pdf_path = export_pdf(st.session_state.results, st.session_state.user_input)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name="BactAI-d_Report.pdf")

# --- FOOTER ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; font-size:14px;'>Created by <b>Zain</b> | Powered by BactAI-d</div>", unsafe_allow_html=True)
