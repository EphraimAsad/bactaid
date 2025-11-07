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

    def confidence_percent(self):
        """Return a confidence % score based on total matches."""
        normalized = max(0, min(100, int((self.total_score / 15) * 100)))
        return normalized

    def confidence_colour(self):
        """Convert confidence to qualitative color level."""
        val = self.confidence_percent()
        if val >= 75:
            return "🟩 High"
        elif val >= 50:
            return "🟨 Moderate"
        elif val >= 25:
            return "🟧 Low"
        else:
            return "🟥 Very Low"

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
        confidence = f"The confidence in this identification is **{self.confidence_colour()}**."

        return f"{intro} {summary}, the isolate most closely resembles **{self.genus}**. {confidence}"


class BacteriaIdentifier:
    def __init__(self, db: pd.DataFrame):
        self.db = db.fillna("")

    def compare_field(self, db_val, user_val, field_name):
        """Compare a database field with user input, returning a match score."""
        if not user_val or str(user_val).strip() == "" or user_val.lower() == "unknown":
            return 0

        db_val = str(db_val).strip()
        user_val = str(user_val).strip()

        hard_exclusions = ["Gram Stain", "Shape", "Spore Formation"]

        db_options = [x.strip().lower() for x in re.split(r"[;/]", db_val) if x.strip()]
        user_options = [x.strip().lower() for x in re.split(r"[;/]", user_val) if x.strip()]

        # If either is variable, skip exclusion
        if "variable" in db_options or "variable" in user_options:
            return 0

        # Temperature special handling
        if field_name == "Growth Temperature":
            try:
                if "//" in db_val:
                    low, high = [float(x) for x in db_val.split("//")]
                    temp = float(user_val)
                    return 1 if low <= temp <= high else -1
            except:
                return 0

        # Normal comparison
        match_found = any(u == d or u in d or d in u for u in user_options for d in db_options)

        # Apply hard exclusion logic
        if field_name in hard_exclusions:
            if not match_found and "variable" not in db_options:
                return -999
            else:
                return 1 if match_found else 0

        return 1 if match_found else -1

    def identify(self, user_input):
        """Main bacterial identification logic."""
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
                    break
                elif score == 1:
                    total_score += 1
                    matched_fields.append(field)
                    reasoning_factors[field] = user_val
                elif score == -1:
                    total_score -= 1
                    mismatched_fields.append(field)

            if total_score > -999:
                extra_notes = row.get("Extra Notes", "")
                result = IdentificationResult(
                    genus, total_score, matched_fields, mismatched_fields, reasoning_factors, extra_notes
                )
                results.append(result)

        # Sort descending by total score
        results.sort(key=lambda x: x.total_score, reverse=True)

        # --- Smart Next Step Suggestion ---
        if results:
            top_genera = [r.genus for r in results[:10]]
            unknown_fields = [f for f, v in user_input.items() if v.lower() == "unknown" or v.strip() == ""]

            variation_scores = {}
            for field in unknown_fields:
                unique_vals = set()
                for _, row in self.db[self.db["Genus"].isin(top_genera)].iterrows():
                    unique_vals.update(re.split(r"[;/]", str(row.get(field, "")).strip().lower()))
                variation_scores[field] = len(unique_vals)

            best_field = max(variation_scores, key=variation_scores.get) if variation_scores else None
        else:
            best_field = None

        # --- Final structured results ---
        data = []
        for r in results[:10]:
            suggestion = (
                f"Perform **{best_field}** to help confirm between likely options."
                if best_field else "All key differentiators have been tested."
            )
            data.append({
                "Genus": r.genus,
                "Confidence (%)": r.confidence_percent(),
                "Confidence Level": r.confidence_colour(),
                "Reasoning": r.reasoning_paragraph(),
                "Next Step Suggestion": suggestion,
                "Extra Notes": r.extra_notes
            })

        return pd.DataFrame(data)
