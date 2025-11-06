import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime
from fpdf import FPDF
from engine import BacteriaIdentifier  # Make sure engine.py is in the same folder

# --- Load database ---
@st.cache_data
def load_data():
    data_path = os.path.join("bacteria_db.xlsx")
    return pd.read_excel(data_path)

db = load_data()
eng = BacteriaIdentifier(db)

# --- Sidebar Input Section ---
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

# --- Initialize Session State ---
if "user_input" not in st.session_state:
    st.session_state.user_input = {f: "Unknown" for f in fields}
if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

# --- Sidebar Fields ---
for field in fields:
    if field in ["Shape", "Colony Morphology", "Media Grown On", "Oxygen Requirement", "Haemolysis Type"]:
        all_vals = []
        for v in eng.db[field]:
            parts = re.split(r"[;/]", str(v))
            for p in parts:
                clean = p.strip()
                if clean and clean not in all_vals:
                    all_vals.append(clean)
        all_vals.sort()

        if st.session_state.user_input[field] in all_vals:
            idx = all_vals.index(st.session_state.user_input[field]) + 1
        else:
            idx = 0

        st.session_state.user_input[field] = st.sidebar.selectbox(
            field,
            ["Unknown"] + all_vals,
            index=idx
        )

    elif field == "Growth Temperature":
        st.session_state.user_input[field] = st.sidebar.text_input(
            "Growth Temperature (e.g., 10//40)", st.session_state.user_input[field]
        )

    else:
        options = ["Unknown", "Positive", "Negative", "Variable"]
        if st.session_state.user_input[field] in options:
            idx = options.index(st.session_state.user_input[field])
        else:
            idx = 0
        st.session_state.user_input[field] = st.sidebar.selectbox(
            field, options, index=idx
        )

# --- Sidebar Buttons ---
col1, col2 = st.sidebar.columns(2)
identify_clicked = col1.button("🔍 Identify")
reset_clicked = col2.button("🔄 Reset")

if reset_clicked:
    st.session_state.user_input = {f: "Unknown" for f in fields}
    st.session_state.results = pd.DataFrame()
    st.experimental_rerun()

# --- Main Page Layout ---
st.title("BactAI-D: Bacterial Identification Assistant")
st.write("Compare your biochemical results against a database of 150+ bacterial genera for likely matches.")

# --- Identify Logic ---
if identify_clicked:
    with st.spinner("Analyzing results..."):
        results = eng.identify(st.session_state.user_input)

        # --- Ensure DataFrame format ---
        if isinstance(results, list):
            # If results are a list of lists (e.g. [['E.coli', 95], ['Salmonella', 87]])
            if all(isinstance(r, (list, tuple)) for r in results):
                num_cols = len(results[0])
                if num_cols == 2:
                    results = pd.DataFrame(results, columns=["Genus", "Confidence"])
                else:
                    col_names = [f"Column_{i+1}" for i in range(num_cols)]
                    results = pd.DataFrame(results, columns=col_names)
            else:
                # If it's a flat list like ['E.coli', 'Salmonella']
                results = pd.DataFrame(results, columns=["Genus"])

        st.session_state.results = results

        if results.empty:
            st.error("No matches found. Try adjusting your inputs.")
        else:
            st.success("Top Possible Matches:")
            st.dataframe(results)

# --- PDF Export Function ---
def export_pdf(dataframe, user_input):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "BactAI-D Identification Report", ln=True, align="C")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Generated: {timestamp}", ln=True, align="R")
    pdf.ln(5)

    # --- Input Section ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Entered Tests", ln=True)
    pdf.set_font("Arial", size=11)
    for k, v in user_input.items():
        pdf.multi_cell(0, 8, f"• {k}: {v}")

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Top Matches", ln=True)
    pdf.set_font("Arial", size=11)

    for i, row in dataframe.iterrows():
        pdf.cell(0, 8, f"{i+1}. {row['Genus']}", ln=True)
        for col in dataframe.columns:
            if col != "Genus":
                pdf.cell(0, 8, f"   - {col}: {row[col]}", ln=True)
        pdf.ln(2)

    output_path = "BactAI-D_Report.pdf"
    pdf.output(output_path)
    return output_path

# --- PDF Export Button ---
if isinstance(st.session_state.results, pd.DataFrame) and not st.session_state.results.empty:
    if st.button("📄 Export Results to PDF"):
        pdf_path = export_pdf(st.session_state.results, st.session_state.user_input)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name="BactAI-D_Report.pdf")

st.caption("BactAI-D © — Built by Zain.")
