
from fastapi import HTTPException
from repositories import intervention_repository as repo
from services.encounter_service import find_encounter

STATUSES = [
    "PENDING_REVIEW",
    "ASSIGNED",
    "CONTACTED",
    "FOLLOW_UP_SCHEDULED",
    "CLOSED"
]


def update_intervention(encounter_id, changes):
    if find_encounter(encounter_id) is None:
        raise HTTPException(404, "Encounter not found")

    existing = repo.get_intervention(encounter_id)

    if existing:
        current = {
            "status": existing[0],
            "assigned_to": existing[1],
            "notes": existing[2]
        }
    else:
        current = {
            "status": "PENDING_REVIEW",
            "assigned_to": None,
            "notes": None
        }

    current.update(changes)

    if current["status"] not in STATUSES:
        raise HTTPException(422, "Invalid intervention status")

    return repo.save_intervention(
        encounter_id,
        current["status"],
        current["assigned_to"],
        current["notes"]
    )
