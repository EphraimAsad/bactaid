import streamlit as st
import pandas as pd
import os
from engine import BacteriaIdentifier

@st.cache_data
def load_data():
    data_path = "bacteria_db.xlsx"
    st.write("🔍 Current working directory:", os.getcwd())
    st.write("📁 Files in directory:", os.listdir())
    st.write("🔎 Looking for:", data_path)

    if not os.path.exists(data_path):
        st.error(f"❌ File not found: {data_path}")
        st.stop()

    try:
        df = pd.read_excel(data_path, engine="openpyxl")
        st.success("✅ Database loaded successfully!")
        return df
    except Exception as e:
        st.error(f"⚠️ Error reading Excel: {e}")
        st.stop()

db = load_data()
eng = BacteriaIdentifier(db)

# --- App Header ---
st.title("🧫 AI Bacteria Identification Assistant")
st.write("Enter your test results below. The AI will suggest the most likely genera based on your inputs.")

# --- Sidebar inputs ---
st.sidebar.header("🧍 Input Your Laboratory Results")
user_input = {}

for field in eng.db.columns:
    if field == "Genus":
        continue

    # --- Multi-select fields ---
    if field in ["Colony Morphology", "Media Grown On", "Oxygen Requirement", "Shape"]:
        all_vals = []
        for v in eng.db[field]:
            parts = re.split(r"[;/]", str(v))
            for p in parts:
                clean = p.strip()
                if clean and clean not in all_vals:
                    all_vals.append(clean)
        all_vals = sorted(set(all_vals))

        selected = st.sidebar.multiselect(
            field,
            options=all_vals,
            help="Select one or more options (optional)."
        )
        user_input[field] = "; ".join(selected)

    # --- Special fields ---
    elif field == "Growth Temperature":
        user_input[field] = st.sidebar.text_input(
            field,
            help="Enter a numeric temperature in °C (e.g., 37)"
        )

    elif field == "Extra Notes":
        user_input[field] = st.sidebar.text_area(
            field,
            help="Optional notes for explanation output."
        )

    # --- Default dropdown ---
    else:
        user_input[field] = st.sidebar.selectbox(
            field,
            ["", "Positive", "Negative", "Variable"],
            index=0
        )

# --- Run identification ---
if st.sidebar.button("🔍 Identify"):
    st.subheader("🔬 Identification Results")
    results = eng.identify(user_input)

    if not results:
        st.warning("No matches found. Try entering more test results.")
    else:
        for i, r in enumerate(results, 1):
            confidence_pct = round((r.total_score + 10) * 5, 1)
            confidence_pct = max(0, min(confidence_pct, 100))

            st.markdown(f"### {i}. **{r.genus}**")
            st.progress(confidence_pct / 100)
            st.caption(f"Confidence: {confidence_pct}%")

            with st.expander("🧠 Reasoning and Explanation"):
                st.write(r.reasoning_paragraph())

            if r.extra_notes:
                st.markdown(f"**Notes:** {r.extra_notes}")

# --- Footer ---
st.markdown("---")
st.caption("AI Bacteria Identification Assistant | Built by [Zain] 🧫 Powered by Python")


