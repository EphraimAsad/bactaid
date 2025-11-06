import pandas as pd
import re
import random

class IdentificationResult:
    def __init__(self, genus, total_score, matched_fields, mismatched_fields, reasoning_factors, extra_notes=""):
        self.genus = genus
        self.total_score = total_score
        self.matched_fields = matched_fields
        self.mismatched_fields = mismatched_fields
        self.reasoning_factors = reasoning_factors
        self.extra_notes = extra_notes

    def reasoning_paragraph(self):
        """Generate a natural-language explanation of why this genus was chosen."""
        if not self.matched_fields:
            return "No significant biochemical or morphological matches were found."

        intro = random.choice([
            "Based on the observed biochemical and morphological traits,",
            "According to the provided test results,",
            "From the available laboratory findings,",
            "Considering the entered reactions and colony traits,"
        ])

        highlights = []
        if "Gram Stain" in self.matched_fields:
            highlights.append(f"it is **Gram {self.reasoning_factors.get('Gram Stain', '').lower()}**")
        if "Shape" in self.matched_fields:
            highlights.append(f"with a **{self.reasoning_factors.get('Shape', '').lower()}** morphology")
        if "Catalase" in self.matched_fields:
            highlights.append(f"and **catalase {self.reasoning_factors.get('Catalase', '').lower()}** activity")
        if "Oxidase" in self.matched_fields:
            highlights.append(f"and **oxidase {self.reasoning_factors.get('Oxidase', '').lower()}** reaction")
        if "Oxygen Requirement" in self.matched_fields:
            highlights.append(f"which prefers **{self.reasoning_factors.get('Oxygen Requirement', '').lower()}** growth conditions")

        summary = " ".join(highlights)
        confidence = "The confidence in this identification is moderate." if self.total_score < 5 else "The confidence in this identification is high."

        suggestion = ""
        if len(self.mismatched_fields) > 0:
            next_test = random.choice(self.mismatched_fields)
            suggestion = f" To confirm this identification, it is recommended to perform or review the **{next_test}** test."

        return f"{intro} {summary}, the isolate most closely resembles **{self.genus}**. {confidence}{suggestion}"


class BacteriaIdentifier:
    def __init__(self, db: pd.DataFrame):
        self.db = db.fillna("")

    def compare_field(self, db_val, user_val, field_name):
        """Compares one field between database and user input, returning match score."""
        if not user_val or str(user_val).strip() == "":
            return 0  # no data provided

        db_val = str(db_val).strip()
        user_val = str(user_val).strip()

        # Hard exclusion fields
        hard_exclusions = ["Gram Stain", "Shape", "Spore Formation"]

        # Split entries for multi-value comparison
        db_options = re.split(r"[;/]", db_val)
        user_options = re.split(r"[;/]", user_val)

        db_options = [x.strip().lower() for x in db_options if x.strip()]
        user_options = [x.strip().lower() for x in user_options if x.strip()]

        # Handle variable logic
        if "variable" in db_options or "variable" in user_options:
            return 0  # do not exclude based on variable

        # Special case: temperature range
        if field_name == "Growth Temperature":
            try:
                if "//" in db_val:
                    low, high = [float(x) for x in db_val.split("//")]
                    temp = float(user_val)
                    return 1 if low <= temp <= high else -1
            except:
                return 0

        # Normal comparison
        match_found = any(u in db_options for u in user_options)

        if match_found:
            return 1
        else:
            if field_name in hard_exclusions:
                return -999  # Hard exclude if critical field doesn't match
            return -1

    def identify(self, user_input):
        """Main identification logic."""
        results = []

        for _, row in self.db.iterrows():
            genus = row["Genus"]
            total_score = 0
            matched_fields = []
            mismatched_fields = []
            reasoning_factors = {}

            for field in self.db.columns:
                if field == "Genus":
                    continue

                db_val = row[field]
                user_val = user_input.get(field, "")

                score = self.compare_field(db_val, user_val, field)

                if score == -999:
                    total_score = -999
                    break  # hard exclusion
                elif score == 1:
                    total_score += 1
                    matched_fields.append(field)
                    reasoning_factors[field] = user_val
                elif score == -1:
                    total_score -= 1
                    mismatched_fields.append(field)

            if total_score > -999:
                extra_notes = row.get("Extra Notes", "")
                results.append(IdentificationResult(genus, total_score, matched_fields, mismatched_fields, reasoning_factors, extra_notes))

        # Sort by score descending
        results.sort(key=lambda x: x.total_score, reverse=True)
        return results[:10]  # return top 10
