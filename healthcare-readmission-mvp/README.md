# Diabetes Readmission Intervention Queue

## Business Problem
A hospital has historical diabetes encounter data.
The care-management team cannot manually review every
discharged patient.

The application will help prioritize which patient
encounters should be reviewed first.

## Primary Users
- Care Management Team
- Hospital Operations
- Clinical Leadership
- Finance / Transformation

## What We Know
- Historical patient encounters are available.
- Historical readmission outcomes are available.
- Previous healthcare utilization is recorded.

## What We Do Not Know
- Which readmissions were preventable.
- The actual cost of readmissions.
- The cost of care-management interventions.
- Whether the proposed risk rules are clinically valid.

## MVP Hypothesis
An explainable risk-scoring rule based on previous
healthcare utilization may help prioritize patients
for care-management review.

Historical readmission outcomes will be used to
evaluate the prioritization, not calculate the score.

## Technology Stack
- Python
- FastAPI
- PostgreSQL
- Git / GitHub

## Disclaimer
This is a learning prototype and is not intended
for real clinical decision-making.