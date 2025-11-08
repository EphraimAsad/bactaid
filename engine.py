import pandas as pd
import re
import random

# -----------------------------
# Helper Function
# -----------------------------
def join_with_and(items):
    """Join list into a readable string, using commas and 'and' before last item."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


# -----------------------------
# Identification Result Class
# -----------------------------
class IdentificationResult:
    """Stores data about a single bacterial genus result and generates reasoning text."""
    def __init__(
        self,
        genus,
        total_score,
        matched_fields,
        mismatched_fields,
        reasoning_factors,
        total_fields_evaluated,
        total_fields_possible,
        extra_notes="",
    ):
        self.genus = genus
        self.total_score = total_score
        self.matched_fields = matched_fields
        self.mismatched_fields = mismatched_fields
        self.reasoning_factors = reasoning_factors
        self.total_fields_evaluated = total_fields_evaluated
        self.total_fields_possible = total_fields_possible
        self.extra_notes = extra_notes

    # -----------------------------
    # Confidence Calculations
    # -----------------------------
    def confidence_percent(self):
        """Confidence based only on tests the user entered."""
        if self.total_fields_evaluated == 0:
            return 0
        return max(0, min(100, int((self.total_score / self.total_fields_evaluated) * 100)))

    def true_confidence(self):
        """Confidence based on *all* possible tests (complete database fields)."""
        if self.total_fields_possible == 0:
            return 0
        return max(0, min(100, int((self.total_score / self.total_fields_possible) * 100)))

    # -----------------------------
    # Reasoning Paragraph Generator
    # -----------------------------
    def reasoning_paragraph(self, ranked_results=None):
        """Generate detailed reasoning paragraph with comparison to other genera."""
        if not self.matched_fields:
            return "No significant biochemical or morphological matches were found."

        intro = random.choice([
            "Based on the observed biochemical and morphological traits,",
            "According to the provided test results,",
            "From the available laboratory findings,",
            "Considering the entered reactions and colony traits,"
        ])

        # Key descriptive highlights
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
            highlights.append(f"which prefers **{self.reasoning_factors.get('Oxygen Requirement', '').lower()}** conditions")

        # Join highlights grammatically
        summary = ", ".join(highlights[:-1]) + " and " + highlights[-1] if len(highlights) > 1 else "".join(highlights)

        # Confidence text
        confidence_text = (
            "The confidence in this identification is high."
            if self.confidence_percent() >= 70
            else "The confidence in this identification is moderate."
        )

        # Comparative reasoning vs other close results
        comparison = ""
        if ranked_results and len(ranked_results) > 1:
            close_others = ranked_results[1:3]
            other_names = [r.genus for r in close_others]
            if other_names:
                if self.total_score >= close_others[0].total_score:
                    comparison = f" It is **more likely** than {join_with_and(other_names)} based on stronger alignment in {join_with_and(self.matched_fields[:3])}."
                else:
                    comparison = f" It is **less likely** than {join_with_and(other_names)} due to differences in {join_with_and(self.mismatched_fields[:3])}."

        return f"{intro} {summary}, the isolate most closely resembles **{self.genus}**. {confidence_text}{comparison}"


# -----------------------------
# Bacteria Identifier Engine
# -----------------------------
class BacteriaIdentifier:
    """Main engine to match bacterial genus based on biochemical & morphological data."""
    def __init__(self, db: pd.DataFrame):
        self.db = db.fillna("")

    # -----------------------------
    # Field Comparison Logic
    # -----------------------------
    def compare_field(self, db_val, user_val, field_name):
        """Compare one test field between database and user input."""
        if not user_val or str(user_val).strip() == "" or user_val.lower() == "unknown":
            return 0  # Skip empty or unknown

        db_val = str(db_val).strip().lower()
        user_val = str(user_val).strip().lower()
        hard_exclusions = ["Gram Stain", "Shape", "Spore Formation"]

        # Split entries by separators for multi-value matches
        db_options = re.split(r"[;/]", db_val)
        user_options = re.split(r"[;/]", user_val)
        db_options = [x.strip() for x in db_options if x.strip()]
        user_options = [x.strip() for x in user_options if x.strip()]

        # Handle "variable" logic
        if "variable" in db_options or "variable" in user_options:
            return 0

        # Special handling for Growth Temperature
        if field_name == "Growth Temperature":
            try:
                if "//" in db_val:
                    low, high = [float(x) for x in db_val.split("//")]
                    temp = float(user_val)
                    return 1 if low <= temp <= high else -1
            except:
                return 0

        # Flexible match: partial overlap counts as match
        match_found = any(any(u in db_opt or db_opt in u for db_opt in db_options) for u in user_options)

        if match_found:
            return 1
        else:
            if field_name in hard_exclusions:
                return -999  # Hard exclusion
            return -1

    # -----------------------------
    # Suggest Next Tests
    # -----------------------------
    def suggest_next_tests(self, top_results):
        """Suggest 3 tests that best differentiate top matches."""
        if len(top_results) < 2:
            return []
        varying_fields = []
        top3 = top_results[:3]

        for field in self.db.columns:
            if field in ["Genus", "Extra Notes", "Colony Morphology"]:
                continue

            field_values = set()
            for r in top3:
                field_values.update(r.matched_fields)
                field_values.update(r.mismatched_fields)

            if len(field_values) > 1:
                varying_fields.append(field)

        random.shuffle(varying_fields)
        return varying_fields[:3]

    # -----------------------------
    # Main Identification Routine
    # -----------------------------
    def identify(self, user_input):
        """Compare user input to database and rank top 10 possible genera."""
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

                # Count only real inputs for relative confidence
                if user_val and user_val.lower() != "unknown":
                    total_fields_evaluated += 1

                if score == -999:
                    total_score = -999
                    break  # Hard exclusion ends comparison

                elif score == 1:
                    total_score += 1
                    matched_fields.append(field)
                    reasoning_factors[field] = user_val

                elif score == -1:
                    total_score -= 1
                    mismatched_fields.append(field)

            # Append valid genus
            if total_score > -999:
                extra_notes = row.get("Extra Notes", "")
                results.append(
                    IdentificationResult(
                        genus,
                        total_score,
                        matched_fields,
                        mismatched_fields,
                        reasoning_factors,
                        total_fields_evaluated,
                        total_fields_possible,
                        extra_notes,
                    )
                )

        # Sort descending by total score
        results.sort(key=lambda x: x.total_score, reverse=True)

        # Generate next-test suggestions for top 3
        if results:
            top_suggestions = self.suggest_next_tests(results)
            for r in results[:3]:
                r.reasoning_factors["next_tests"] = ", ".join(top_suggestions)

        # Return top 10 results
        return results[:10]



