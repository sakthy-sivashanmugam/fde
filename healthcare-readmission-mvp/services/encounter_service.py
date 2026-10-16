
from repositories import encounter_repository as repo


def list_encounters(limit=10, offset=0, risk_level=None):
    return repo.get_encounters(limit, offset, risk_level)


def find_encounter(encounter_id):
    return repo.get_encounter_by_id(encounter_id)


def list_care_queue(limit=20, offset=0, risk_level=None):
    return repo.get_care_queue(limit, offset, risk_level)


def operations_summary():
    return repo.get_operations_summary()


def readmission_analysis():
    return repo.get_readmission_analysis()


def management_dashboard():
    summary = operations_summary()
    analysis = readmission_analysis()

    return {
        "overview": summary,
        "readmission_analysis": analysis,
        "priority_encounters": list_care_queue(limit=10),
    }
