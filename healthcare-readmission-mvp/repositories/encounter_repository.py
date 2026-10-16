
from database import get_connection

ENCOUNTER_COLUMNS = """
    encounter_id, patient_nbr, age, time_in_hospital,
    number_inpatient, number_emergency, number_outpatient,
    num_medications, num_lab_procedures,
    discharge_disposition_id, admission_type_id,
    readmitted, risk_score, risk_level
"""

ENCOUNTER_KEYS = [
    "encounter_id", "patient_nbr", "age", "time_in_hospital",
    "number_inpatient", "number_emergency", "number_outpatient",
    "num_medications", "num_lab_procedures",
    "discharge_disposition_id", "admission_type_id",
    "readmitted", "risk_score", "risk_level"
]


def to_dict(row):
    return dict(zip(ENCOUNTER_KEYS, row))


def get_encounters(limit=10, offset=0, risk_level=None):
    sql = f"SELECT {ENCOUNTER_COLUMNS} FROM patient_encounters"
    params = []

    if risk_level:
        sql += " WHERE risk_level = %s"
        params.append(risk_level)

    sql += " ORDER BY encounter_id LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            return [to_dict(row) for row in cursor.fetchall()]


def get_encounter_by_id(encounter_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""SELECT {ENCOUNTER_COLUMNS}
                    FROM patient_encounters
                    WHERE encounter_id = %s""",
                (encounter_id,)
            )
            row = cursor.fetchone()
            return to_dict(row) if row else None


def get_care_queue(limit=20, offset=0, risk_level=None):
    sql = f"""
        SELECT {", ".join("e." + c for c in ENCOUNTER_KEYS)},
               i.status, i.assigned_to, i.notes
        FROM patient_encounters e
        LEFT JOIN care_interventions i
            ON e.encounter_id = i.encounter_id
        WHERE e.risk_level IN ('HIGH', 'MEDIUM')
    """
    params = []

    if risk_level:
        sql += " AND e.risk_level = %s"
        params.append(risk_level)

    sql += """
        ORDER BY e.risk_score DESC, e.encounter_id
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            results = []

            for row in cursor.fetchall():
                encounter = to_dict(row[:len(ENCOUNTER_KEYS)])
                encounter["intervention_status"] = (
                    row[-3] or "PENDING_REVIEW"
                )
                encounter["assigned_to"] = row[-2]
                encounter["notes"] = row[-1]
                results.append(encounter)

            return results


def get_operations_summary():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (WHERE risk_level = 'HIGH'),
                    COUNT(*) FILTER (WHERE risk_level = 'MEDIUM'),
                    COUNT(*) FILTER (WHERE risk_level = 'LOW')
                FROM patient_encounters
            """)
            total, high, medium, low = cursor.fetchone()

            cursor.execute("""
                SELECT status, COUNT(*)
                FROM care_interventions
                GROUP BY status
                ORDER BY status
            """)
            statuses = dict(cursor.fetchall())

            return {
                "total_encounters": total,
                "high_risk": high,
                "medium_risk": medium,
                "low_risk": low,
                "intervention_status_counts": statuses
            }


def get_readmission_analysis():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    risk_level,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (
                        WHERE readmitted = '<30'
                    ) AS early_readmissions
                FROM patient_encounters
                GROUP BY risk_level
                ORDER BY
                    CASE risk_level
                        WHEN 'HIGH' THEN 1
                        WHEN 'MEDIUM' THEN 2
                        ELSE 3
                    END
            """)

            return [
                {
                    "risk_level": level,
                    "total_encounters": total,
                    "readmitted_within_30_days": early,
                    "early_readmission_rate_pct": (
                        round(100 * early / total, 2)
                        if total else 0
                    )
                }
                for level, total, early in cursor.fetchall()
            ]
