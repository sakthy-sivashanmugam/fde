from database import get_connection

def calculate_risk_score(encounter):
    score = 0

    if encounter["number_inpatient"] >= 3:
        score += 3

    if encounter["number_emergency"] >= 2:
        score += 2

    if encounter["number_outpatient"] >= 3:
        score += 1

    if encounter["time_in_hospital"] >= 7:
        score += 1

    if encounter["num_medications"] >= 20:
        score += 1

    return score

def classify_risk(score):
    if score >= 5:
        return "HIGH"
    elif score >= 3:
        return "MEDIUM"
    else:
        return "LOW"
    
def assess_encounter_risk(encounter):
    score = calculate_risk_score(encounter)
    level = classify_risk(score)

    return {
        "risk_score": score,
        "risk_level": level
    }

def get_encounter(encounter_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    number_inpatient,
                    number_emergency,
                    number_outpatient,
                    time_in_hospital,
                    num_medications
                FROM patient_encounters
                WHERE encounter_id = %s
                """,
                (encounter_id,)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "number_inpatient": row[0],
                "number_emergency": row[1],
                "number_outpatient": row[2],
                "time_in_hospital": row[3],
                "num_medications": row[4]
            }

def update_encounter_risk(encounter_id, assessment):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE patient_encounters
                SET
                    risk_score = %s,
                    risk_level = %s
                WHERE encounter_id = %s
                """,
                (
                    assessment["risk_score"],
                    assessment["risk_level"],
                    encounter_id
                )
            )

            print("Rows updated:", cursor.rowcount)

def score_all_encounters():
    batch_size = 1000
    total_updated = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    encounter_id,
                    number_inpatient,
                    number_emergency,
                    number_outpatient,
                    time_in_hospital,
                    num_medications
                FROM patient_encounters
                ORDER BY encounter_id
            """)

            rows = cursor.fetchall()

    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]

        with get_connection() as connection:
            with connection.cursor() as cursor:
                for row in batch:
                    encounter_id = row[0]

                    encounter = {
                        "number_inpatient": row[1],
                        "number_emergency": row[2],
                        "number_outpatient": row[3],
                        "time_in_hospital": row[4],
                        "num_medications": row[5]
                    }

                    assessment = assess_encounter_risk(encounter)

                    cursor.execute("""
                        UPDATE patient_encounters
                        SET risk_score = %s,
                            risk_level = %s
                        WHERE encounter_id = %s
                    """, (
                        assessment["risk_score"],
                        assessment["risk_level"],
                        encounter_id
                    ))

                    total_updated += cursor.rowcount

        print(
            f"Batch {start // batch_size + 1} committed"
        )

    print("Total encounters updated:", total_updated)

if __name__ == "__main__":
    score_all_encounters()