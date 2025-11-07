import streamlit as st
import pandas as pd
import re
import os
from fpdf import FPDF
from datetime import datetime
from engine import BacteriaIdentifier

# --- PAGE CONFIG ---
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
            field, ["Unknown"] + all_vals, key=field
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

# --- COLOR GRADIENT FUNCTION ---
def confidence_gradient(conf_pct):
    """Generate a smooth color gradient from red (low) → green (high)."""
    red = int(255 - (conf_pct * 2.55))
    green = int(conf_pct * 2.55)
    return f"rgb({red},{green},60)"

# --- SMART NEXT STEP FUNCTION ---
def suggest_next_tests(user_input, db, top_results):
    """Suggest which unknown tests would most differentiate top candidates."""
    if len(top_results) < 2:
        return "All known fields already consistent. No further differentiation required."

    top_genera = [r["Genus"] for _, r in top_results.iterrows()]
    subset = db[db["Genus"].isin(top_genera)]

    unknown_fields = [k for k, v in user_input.items() if v == "Unknown"
                      and k not in ["Extra Notes", "Colony Morphology"]]

    if not unknown_fields:
        return "No untested fields available for further differentiation."

    field_variability = {}
    for field in unknown_fields:
        unique_vals = set()
        for v in subset[field]:
            for val in re.split(r"[;/]", str(v)):
                if val.strip():
                    unique_vals.add(val.strip().lower())
        field_variability[field] = len(unique_vals)

    if not field_variability:
        return "No further key differentiating tests identified."

    best_field = max(field_variability, key=field_variability.get)
    return f"Perform or review the **{best_field}** test to further differentiate among top candidates."

# --- COMPARATIVE REASONING FUNCTION (GRAMMATICALLY POLISHED) ---
def generate_reasoning(main_row, second_row, user_input):
    """Describe how the top genus differs from the runner-up, with natural phrasing."""
    genus1 = main_row["Genus"]
    genus2 = second_row["Genus"]
    differences = []

    for field, val in user_input.items():
        if field == "Genus" or val in ["Unknown", ""]:
            continue
        db_val1 = str(db.loc[db["Genus"] == genus1, field].values[0]) if not db.loc[db["Genus"] == genus1].empty else ""
        db_val2 = str(db.loc[db["Genus"] == genus2, field].values[0]) if not db.loc[db["Genus"] == genus2].empty else ""
        if db_val1.lower() != db_val2.lower():
            differences.append(field.lower())

    if not differences:
        return f"The biochemical profile matches **{genus1}** closely, showing minimal distinction from {genus2}."

    # --- Grammar fix for 'and' before last element ---
    if len(differences) == 1:
        formatted_diffs = differences[0]
    elif len(differences) == 2:
        formatted_diffs = " and ".join(differences)
    else:
        formatted_diffs = ", ".join(differences[:-1]) + f", and {differences[-1]}"

    return (f"The isolate aligns best with **{genus1}**, differing from *{genus2}* primarily in "
            f"{formatted_diffs}. These results support identification as **{genus1}**.")

# --- DISPLAY RESULTS ---
if isinstance(st.session_state.results, pd.DataFrame) and not st.session_state.results.empty:
    st.success("### Top Possible Matches:")

    for idx, row in st.session_state.results.iterrows():
        genus = row["Genus"]
        conf_pct = float(row["Confidence (%)"])
        conf_lvl = row["Confidence Level"]
        color = confidence_gradient(conf_pct)

        header_html = f"""
        <div style='background:{color}; padding:8px; border-radius:8px; margin-bottom:4px; color:white;'>
            <strong>{idx+1}. {genus}</strong> — {conf_lvl} ({conf_pct:.1f}%)
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)

        with st.expander("Details & Reasoning"):
            if idx == 0 and len(st.session_state.results) > 1:
                reasoning = generate_reasoning(row, st.session_state.results.iloc[1], st.session_state.user_input)
            else:
                reasoning = row["Reasoning"]

            st.markdown(f"**Reasoning:** {reasoning}")
            next_step = suggest_next_tests(st.session_state.user_input, db, st.session_state.results.head(5))
            st.markdown(f"**Next Step:** {next_step}")
            if row['Extra Notes']:
                st.markdown(f"**Notes:** {row['Extra Notes']}")

else:
    st.info("Enter your results on the left and click **Identify** to begin analysis.")

# --- PDF EXPORT ---
def safe_text(s):
    return str(s).encode('latin-1', 'replace').decode('latin-1')

def export_pdf(df, user_input):
    """Export results as a well-formatted PDF with grammatical reasoning."""
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

    for i, row in df.iterrows():
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, safe_text(f"{row['Genus']} — {row['Confidence Level']} ({row['Confidence (%)']}%)"), ln=True)
        pdf.set_font("Helvetica", size=10)

        if i == 0 and len(df) > 1:
            reasoning = generate_reasoning(row, df.iloc[1], user_input)
        else:
            reasoning = row["Reasoning"]

        pdf.multi_cell(0, 8, safe_text(f"Reasoning: {reasoning}"))
        next_step = suggest_next_tests(user_input, db, df.head(5))
        pdf.multi_cell(0, 8, safe_text(f"Next Step: {next_step}"))
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
