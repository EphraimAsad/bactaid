import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF  # For PDF export
from engine import BacteriaIdentifier  # Ensure engine.py is in same folder

# --- Load the database ---
@st.cache_data
def load_data():
    data_path = os.path.join("bacteria_db.xlsx")
    return pd.read_excel(data_path)

db = load_data()
eng = BacteriaIdentifier(db)

# --- Sidebar input section ---
st.sidebar.title("BactAI-D 🧫")
st.sidebar.write("Enter your biochemical or morphological test results below.")
st.sidebar.write("Leave any field as 'Unknown' if you haven’t done that test yet.")

fields = [
    "Gram Stain", "Shape", "Catalase", "Oxidase", "Colony Morphology", "Haemolysis",
    "Haemolysis Type", "Indole", "Growth Temperature", "Media Grown On", "Motility",
    "Capsule", "Spore Formation", "Oxygen Requirement", "Methyl Red", "VP", "Citrate",
    "Urease", "H2S", "Lactose Fermentation", "Glucose Fermantation", "Sucrose Fermentation",
    "Nitrate Reduction", "Lysine Decarboxylase", "Ornitihine Decarboxylase", "Arginine dihydrolase",
    "Gelatin Hydrolysis", "Esculin Hydrolysis", "Dnase", "ONPG", "NaCl Tolerant (>=6%)"
]

# --- Create / reset session state for inputs ---
if "user_input" not in st.session_state:
    st.session_state.user_input = {f: "Unknown" for f in fields}
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

# --- Sidebar input fields ---
for field in fields:
    # Multi-option descriptive fields
    if field in ["Colony Morphology", "Media Grown On", "Oxygen Requirement", "Haemolysis Type"]:
        all_vals = []
        for v in eng.db[field]:
            parts = re.split(r"[;/]", str(v))
            for p in parts:
                clean = p.strip()
                if clean and clean not in all_vals:
                    all_vals.append(clean)
        all_vals.sort()
        st.session_state.user_input[field] = st.sidebar.selectbox(
            field, ["Unknown"] + all_vals, index=["Unknown"] + all_vals.index(st.session_state.user_input[field]) if st.session_state.user_input[field] in all_vals else 0
        )

    elif field == "Growth Temperature":
        st.session_state.user_input[field] = st.sidebar.text_input(
            "Growth Temperature (e.g., 10//40)", st.session_state.user_input[field]
        )

    else:
        st.session_state.user_input[field] = st.sidebar.selectbox(
            field,
            ["Unknown", "Positive", "Negative", "Variable"],
            index=["Unknown", "Positive", "Negative", "Variable"].index(st.session_state.user_input[field])
            if st.session_state.user_input[field] in ["Unknown", "Positive", "Negative", "Variable"]
            else 0,
        )

# --- Buttons ---
col1, col2 = st.sidebar.columns(2)
identify_clicked = col1.button("🔍 Identify Bacteria")
reset_clicked = col2.button("🔄 Reset Inputs")

if reset_clicked:
    st.session_state.user_input = {f: "Unknown" for f in fields}
    st.session_state.results = pd.DataFrame()
    st.experimental_rerun()

# --- Main section ---
st.title("BactAI-D: Bacterial Identification Assistant")
st.write("This tool compares your test results with over 150 bacterial genera to suggest the most likely matches.")

# --- Identify logic ---
if identify_clicked:
    with st.spinner("Analyzing results..."):
        results = eng.identify(st.session_state.user_input)
        st.session_state.results = results
        if results.empty:
            st.error("No matches found. Try adjusting your inputs.")
        else:
            st.success("Top possible matches:")
            st.dataframe(results)

# --- PDF Export ---
if not st.session_state.results.empty:
    def export_pdf(dataframe, user_input):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt="BactAI-D Identification Report", ln=True, align="C")

        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Entered Tests:", ln=True, align="L")

        for k, v in user_input.items():
            pdf.multi_cell(0, 8, f"{k}: {v}")

        pdf.cell(200, 10, txt="\nTop Matches:", ln=True, align="L")
        pdf.set_font("Arial", size=11)
        for i, row in dataframe.iterrows():
            row_text = ", ".join([f"{col}: {row[col]}" for col in dataframe.columns])
            pdf.multi_cell(0, 8, row_text)

        output_path = "BactAI-D_Report.pdf"
        pdf.output(output_path)
        return output_path

    if st.button("📄 Export Results to PDF"):
        pdf_path = export_pdf(st.session_state.results, st.session_state.user_input)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name="BactAI-D_Report.pdf")

st.caption("BactAI-D © — Built by Zain")
