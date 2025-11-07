import pandas as pd
import re
import random

class IdentificationResult:
    def __init__(self, genus, total_score, matched_fields, mismatched_fields, reasoning_factors, total_fields_evaluated, total_fields_possible, extra_notes=""):
        self.genus = genus
        self.total_score = total_score
        self.matched_fields = matched_fields
        self.mismatched_fields = mismatched_fields
        self.reasoning_factors = reasoning_factors
        self.total_fields_evaluated = total_fields_evaluated
        self.total_fields_possible = total_fields_possible
        self.extra_notes = extra_notes

    def confidence_percent(self):
        """Confidence based on fields entered"""
        if self.total_fields_evaluated == 0:
            return 0
        return max(0, min(100, int((self.total_score / self.total_fields_evaluated) * 100)))

    def true_confidence(self):
        """Confidence based on all possible tests"""
        if self.total_fields_possible == 0:
            return 0
        return max(0, min(100, int((self.total_score / self.total_fields_possible) * 100)))

    def reasoning_paragraph(self):
        """Generate natural reasoning explanation."""
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

        if len(highlights) > 1:
            summary = ", ".join(highlights[:-1]) + " and " + highlights[-1]
        else:
            summary = "".join(highlights)

        confidence_text = "The confidence in this identification is high." if self.confidence_percent() >= 70 else "The confidence in this identification is moderate."

        # --- Suggest next 3 differentiation tests ---
        next_tests = random.sample(self.mismatched_fields, min(3, len(self.mismatched_fields))) if self.mismatched_fields else []
        suggestion = ""
        if next_tests:
            suggestion = f" To further differentiate, consider performing: **{', '.join(next_tests)}**."

        return f"{intro} {summary}, the isolate most closely resembles **{self.genus}**. {confidence_text}{suggestion}"


class BacteriaIdentifier:
    def __init__(self, db: pd.DataFrame):
        self.db = db.fillna("")

    def compare_field(self, db_val, user_val, field_name):
        """Compare field and return score."""
        if not user_val or str(user_val).strip() == "" or user_val.lower() == "unknown":
            return 0

        db_val = str(db_val).strip().lower()
        user_val = str(user_val).strip().lower()
        hard_exclusions = ["Gram Stain", "Shape", "Spore Formation"]

        db_options = re.split(r"[;/]", db_val)
        user_options = re.split(r"[;/]", user_val)
        db_options = [x.strip() for x in db_options if x.strip()]
        user_options = [x.strip() for x in user_options if x.strip()]

        if "variable" in db_options or "variable" in user_options:
            return 0

        # Temperature special logic
        if field_name == "Growth Temperature":
            try:
                if "//" in db_val:
                    low, high = [float(x) for x in db_val.split("//")]
                    temp = float(user_val)
                    return 1 if low <= temp <= high else -1
            except:
                return 0

        # --- Partial overlap logic ---
        match_found = any(
            any(u in db_opt or db_opt in u for db_opt in db_options)
            for u in user_options
        )

        if match_found:
            return 1
        else:
            if field_name in hard_exclusions:
                return -999
            return -1

    def identify(self, user_input):
        """Run identification."""
        results = []
        total_fields_possible = len([c for c in self.db.columns if c != "Genus"])

        for _, row in self.db.iterrows():
            genus = row["Genus"]
            total_score = 0
            matched_fields, mismatched_fields, reasoning_factors = [], [], {}
            total_fields_evaluated = 0

            for field in self.db.columns:
                if field == "Genus":
                    continue

                db_val = row[field]
                user_val = user_input.get(field, "")

                score = self.compare_field(db_val, user_val, field)
                if user_val and user_val.lower() != "unknown":
                    total_fields_evaluated += 1

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
                results.append(
                    IdentificationResult(
                        genus, total_score, matched_fields, mismatched_fields,
                        reasoning_factors, total_fields_evaluated, total_fields_possible, extra_notes
                    )
                )

        results.sort(key=lambda x: x.total_score, reverse=True)
        return results[:10]
