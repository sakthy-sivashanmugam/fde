CREATE TABLE IF NOT EXISTS patient_encounters (
    encounter_id BIGINT PRIMARY KEY,
    patient_nbr BIGINT NOT NULL,
    age VARCHAR(20),
    time_in_hospital INTEGER,
    number_inpatient INTEGER,
    number_emergency INTEGER,
    number_outpatient INTEGER,
    num_medications INTEGER,
    num_lab_procedures INTEGER,
    discharge_disposition_id INTEGER,
    admission_type_id INTEGER,
    readmitted VARCHAR(10),
    risk_score INTEGER,
    risk_level VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS care_interventions (
    intervention_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    encounter_id BIGINT NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_REVIEW',
    assigned_to VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_intervention_encounter
        FOREIGN KEY (encounter_id)
        REFERENCES patient_encounters(encounter_id)
);