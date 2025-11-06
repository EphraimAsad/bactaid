import streamlit as st
import pandas as pd
import re
import os
from engine import BacteriaIdentifier  # Make sure engine.py is in same folder

# --- Load the database ---
@st.cache_data
def load_data():
    data_path = os.path.join("bacteria_db.xlsx")
    return pd.read_excel(data_path)

db = load_data()
eng = BacteriaIdentifier(db)

st.title("BactAI-D – Bacterial Identification Assistant")

st.write("Enter your test results below. You can leave any field as 'Unknown' if you haven’t done that test yet.")

# --- Input Fields ---
fields = [
    "Gram Stain", "Shape", "Catalase", "Oxidase", "Colony Morphology", "Haemolysis",
    "Haemolysis Type", "Indole", "Growth Temperature", "Media Grown On", "Motility",
    "Capsule", "Spore Formation", "Oxygen Requirement", "Methyl Red", "VP", "Citrate",
    "Urease", "H2S", "Lactose Fermentation", "Glucose Fermantation", "Sucrose Fermentation",
    "Nitrate Reduction", "Lysine Decarboxylase", "Ornitihine Decarboxylase", "Arginine dihydrolase",
    "Gelatin Hydrolysis", "Esculin Hydrolysis", "Dnase", "ONPG", "NaCl Tolerant (>=6%)"
]

user_input = {}

for field in fields:
    # Handle fields with multiple descriptive options
    if field in ["Colony Morphology", "Media Grown On", "Oxygen Requirement", "Haemolysis Type"]:
        all_vals = []
        for v in eng.db[field]:
            parts = re.split(r"[;/]", str(v))
            for p in parts:
                clean = p.strip()
                if clean and clean not in all_vals:
                    all_vals.append(clean)
        all_vals.sort()
        user_input[field] = st.selectbox(field, ["Unknown"] + all_vals)

    # Growth temperature stays a text input
    elif field == "Growth Temperature":
        user_input[field] = st.text_input("Growth Temperature (e.g., 10//40)", "Unknown")

    # Standard Positive/Negative/Variable dropdowns
    else:
        user_input[field] = st.selectbox(field, ["Unknown", "Positive", "Negative", "Variable"])

# --- Identify Button ---
if st.button("Identify Bacteria"):
    with st.spinner("Analyzing results..."):
        results = eng.identify(user_input)
        if results.empty:
            st.error("No matches found. Try changing a few inputs or ensure valid data entry.")
        else:
            st.success("Top possible matches:")
            st.dataframe(results)

st.caption("BactAI-D © – Created by Zain.")
