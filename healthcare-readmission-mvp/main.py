
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from services import encounter_service
from services import intervention_service

app = FastAPI(
    title="Healthcare Readmission Intervention API",
    version="1.0.0"
)

RiskLevel = Literal["HIGH", "MEDIUM", "LOW"]


class InterventionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "PENDING_REVIEW",
        "ASSIGNED",
        "CONTACTED",
        "FOLLOW_UP_SCHEDULED",
        "CLOSED"
    ] | None = None

    assigned_to: str | None = None
    notes: str | None = None


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Healthcare Readmission MVP"
    }


@app.get("/encounters")
def get_encounters(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    risk_level: RiskLevel | None = None
):
    return encounter_service.list_encounters(
        limit, offset, risk_level
    )


@app.get("/encounters/{encounter_id}")
def get_encounter(encounter_id: int):
    encounter = encounter_service.find_encounter(encounter_id)

    if encounter is None:
        raise HTTPException(404, "Encounter not found")

    return encounter


@app.get("/care-queue")
def get_care_queue(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    return encounter_service.list_care_queue(limit, offset)


@app.get("/care-queue/high")
def get_high_care_queue(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    return encounter_service.list_care_queue(
        limit, offset, "HIGH"
    )


@app.patch("/interventions/{encounter_id}")
def patch_intervention(
    encounter_id: int,
    update: InterventionUpdate
):
    changes = update.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(422, "No fields provided")

    if "status" in changes and changes["status"] is None:
        raise HTTPException(422, "Status cannot be null")

    return intervention_service.update_intervention(
        encounter_id, changes
    )


@app.get("/operations/summary")
def operations_summary():
    return encounter_service.operations_summary()


@app.get("/operations/readmission-analysis")
def readmission_analysis():
    return encounter_service.readmission_analysis()


@app.get("/management/dashboard")
def management_dashboard():
    return encounter_service.management_dashboard()
