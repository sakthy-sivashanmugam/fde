
from database import get_connection


def save_intervention(encounter_id, status, assigned_to, notes):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO care_interventions
                    (encounter_id, status, assigned_to, notes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (encounter_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    assigned_to = EXCLUDED.assigned_to,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING
                    intervention_id, encounter_id, status,
                    assigned_to, notes, created_at, updated_at
            """, (encounter_id, status, assigned_to, notes))

            row = cursor.fetchone()

            return dict(zip([
                "intervention_id", "encounter_id", "status",
                "assigned_to", "notes", "created_at", "updated_at"
            ], row))


def get_intervention(encounter_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT status, assigned_to, notes
                FROM care_interventions
                WHERE encounter_id = %s
            """, (encounter_id,))
            row = cursor.fetchone()
            return row
