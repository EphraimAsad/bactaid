import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import datetime
from engine import BacteriaIdentifier

# --- CONFIG ---
st.set_page_config(page_title="BactAI-D Assistant", layout="wide")

# --- FIELD GROUPS ---
MORPH_FIELDS = [
    "Gram Stain",
    "Shape",
    "Colony Morphology",
    "Media Grown On",
    "Motility",
    "Capsule",
    "Spore Formation"
]

ENZYME_FIELDS = [
    "Catalase",
    "Oxidase",
    "Coagulase",
    "Lipase Test"
]

SUGAR_FIELDS = [
    "Glucose Fermantation",
    "Lactose Fermentation",
    "Sucrose Fermentation",
    "Maltose Fermentation",
    "Mannitol Fermentation",
    "Sorbitol Fermentation",
    "Xylose Fermentation",
    "Rhamnose Fermentation",
    "Arabinose Fermentation",
    "Raffinose Fermentation",
    "Trehalose Fermentation",
    "Inositol Fermentation"
]

# --- LOAD DATABASE ---
@st.cache_data
def load_data():
    data_path = os.path.join("bacteria_db.xlsx")
    df = pd.read_excel(data_path)
    df.columns = [c.strip() for c in df.columns]  # trim stray spaces
    return df

db = load_data()
eng = BacteriaIdentifier(db)

# --- TITLE ---
st.title("🧫 BactAI-d: Intelligent Bacteria Identification Assistant")
st.markdown("Use the sidebar to input your biochemical and morphological results.")

# --- SESSION STATE ---
if "user_input" not in st.session_state:
    st.session_state.user_input = {}
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

# --- SIDEBAR ---
st.sidebar.markdown(
    """
    <div style='background-color:#1565C0; padding:12px; border-radius:10px;'>
        <h3 style='text-align:center; color:white; margin:0;'>🔬 Input Test Results</h3>
    </div>
    """,
    unsafe_allow_html=True
)
# ------------------------
# SECTION 1: MORPHOLOGICAL TESTS
# ------------------------
with st.sidebar.expander("🧫 Morphological Tests", expanded=True):
    for field in MORPH_FIELDS:
        if field not in eng.db.columns:
            continue

        if field in ["Colony Morphology", "Media Grown On", "Shape"]:
            all_vals = []
            for v in eng.db[field]:
                parts = re.split(r"[;/]", str(v))
                for p in parts:
                    clean = p.strip()
                    if clean and clean not in all_vals:
                        all_vals.append(clean)
            all_vals.sort()
            st.session_state.user_input[field] = st.selectbox(
                field, ["Unknown"] + all_vals, index=0, key=field
            )
        else:
            st.session_state.user_input[field] = st.selectbox(
                field, ["Unknown", "Positive", "Negative", "Variable"], index=0, key=field
            )

# ------------------------
# SECTION 2: ENZYME TESTS
# ------------------------
with st.sidebar.expander("🧪 Enzyme Tests", expanded=False):
    for field in ENZYME_FIELDS:
        if field in eng.db.columns:
            st.session_state.user_input[field] = st.selectbox(
                field, ["Unknown", "Positive", "Negative", "Variable"], index=0, key=field
            )

# ------------------------
# SECTION 3: CARBOHYDRATE FERMENTATION TESTS
# ------------------------
with st.sidebar.expander("🍬 Carbohydrate Fermentation Tests", expanded=False):
    for field in SUGAR_FIELDS:
        if field in eng.db.columns:
            st.session_state.user_input[field] = st.selectbox(
                field, ["Unknown", "Positive", "Negative", "Variable"], index=0, key=field
            )

# ------------------------
# SECTION 4: OTHER TESTS
# ------------------------
with st.sidebar.expander("🧬 Other Tests", expanded=False):
    for field in eng.db.columns:
        if field in ["Genus"] + MORPH_FIELDS + ENZYME_FIELDS + SUGAR_FIELDS:
            continue

        if field == "Haemolysis Type":
            all_vals = []
            for v in eng.db[field]:
                parts = re.split(r"[;/]", str(v))
                for p in parts:
                    clean = p.strip()
                    if clean and clean not in all_vals:
                        all_vals.append(clean)
            all_vals.sort()
            st.session_state.user_input[field] = st.selectbox(
                field, ["Unknown"] + all_vals, index=0, key=field
            )
        elif field == "Growth Temperature":
            st.session_state.user_input[field] = st.text_input(field + " (°C)", "", key=field)
        else:
            st.session_state.user_input[field] = st.selectbox(
                field, ["Unknown", "Positive", "Negative", "Variable"], index=0, key=field
            )

# --- RESET BUTTON ---
if st.sidebar.button("🔄 Reset All Inputs"):
    for key in list(st.session_state.user_input.keys()):
        st.session_state.user_input[key] = "Unknown"
    st.rerun()

# --- IDENTIFY BUTTON ---
if st.sidebar.button("🔍 Identify"):
    with st.spinner("Analyzing results..."):
        results = eng.identify(st.session_state.user_input)
        if isinstance(results, list):
            results = pd.DataFrame(
                [
                    [
                        r.genus,
                        f"{max(0, min(100, int((r.total_score / 30) * 100)))}%",
                        r.reasoning_paragraph(),
                        ", ".join(r.mismatched_fields),
                        r.extra_notes,
                    ]
                    for r in results
                ],
                columns=[
                    "Genus",
                    "Confidence",
                    "Reasoning",
                    "Next Step Suggestion",
                    "Extra Notes",
                ],
            )
        st.session_state.results = results

# --- DISPLAY RESULTS ---
if not st.session_state.results.empty:
    st.success("Top Possible Matches:")

    for _, row in st.session_state.results.iterrows():
        confidence_color = (
            "🟢" if int(row["Confidence"].replace("%", "")) >= 75
            else "🟡" if int(row["Confidence"].replace("%", "")) >= 50
            else "🔴"
        )
        header = f"**{row['Genus']}** — {confidence_color} {row['Confidence']}"
        with st.expander(header):
            st.markdown(f"**Reasoning:** {row['Reasoning']}")
            st.markdown(f"**Next Step:** {row['Next Step Suggestion']}")
            if row["Extra Notes"]:
                st.markdown(f"**Notes:** {row['Extra Notes']}")

# --- PDF EXPORT ---
def export_pdf(df, user_input):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="BactAI-d Identification Report", ln=True, align="C")
    pdf.cell(200, 8, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 8, txt="User Input Summary", ln=True)
    pdf.set_font("Arial", size=10)
    for k, v in user_input.items():
        pdf.cell(90, 6, txt=f"{k}:", ln=0)
        pdf.cell(90, 6, txt=str(v), ln=1)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 8, txt="Results", ln=True)
    pdf.set_font("Arial", size=10)

    for _, row in df.iterrows():
        pdf.multi_cell(0, 6, f"{row['Genus']} ({row['Confidence']})")
        pdf.multi_cell(0, 6, f"Reasoning: {row['Reasoning']}")
        pdf.multi_cell(0, 6, f"Next Step: {row['Next Step Suggestion']}")
        if row["Extra Notes"]:
            pdf.multi_cell(0, 6, f"Notes: {row['Extra Notes']}")
        pdf.ln(4)

    output_path = "BactAI-d_Report.pdf"
    pdf.output(output_path, "F")
    return output_path

if isinstance(st.session_state.results, pd.DataFrame) and not st.session_state.results.empty:
    if st.button("📄 Export Results to PDF"):
        pdf_path = export_pdf(st.session_state.results, st.session_state.user_input)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name="BactAI-d_Report.pdf")

# --- FOOTER ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; font-size: 14px;'>Created by <b>Zain</b> | Powered by BactAI-D</div>",
    unsafe_allow_html=True
)

