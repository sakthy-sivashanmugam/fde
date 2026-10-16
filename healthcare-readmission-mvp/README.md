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

- **Python 3.14** â€” Application development and business logic

- **FastAPI** â€” REST API framework

- **Uvicorn** â€” ASGI application server

- **PostgreSQL** â€” Relational database for patient encounters and care interventions

- **Psycopg 3** â€” PostgreSQL database connectivity

- **python-dotenv** â€” Environment-based configuration

- **Pydantic** â€” API request validation and data models

- **pytest** â€” Automated integration testing

- **HTTPX** â€” HTTP client used by FastAPI's TestClient

- **Git / GitHub** â€” Version control and source-code repository

## Application Architecture

The application follows a layered architecture to separate API handling, business logic, and database operations.

```text

Client / API Consumer

&#x20;       |

&#x20;       v

main.py (FastAPI)

&#x20;       |

&#x20;       v

services/ (Business Logic)

&#x20;       |

&#x20;       v

repositories/ (Database Queries)

&#x20;       |

&#x20;       v

database.py (PostgreSQL Connection)

&#x20;       |

&#x20;       v

PostgreSQL Database

```

### Layer Responsibilities

- **API Layer (`main.py`)** â€” Defines REST endpoints, accepts HTTP requests, validates inputs, and returns responses.

- **Service Layer (`services/`)** â€” Implements application business logic and coordinates operations.

- **Repository Layer (`repositories/`)** â€” Executes SQL queries and retrieves or updates database records.

- **Database Connection (`database.py`)** â€” Manages PostgreSQL connectivity using environment configuration.

- **PostgreSQL** â€” Stores patient encounter data, risk scores, and care-management interventions.

### Supporting Components

- **`risk\_scoring.py`** â€” Implements the explainable rule-based risk-scoring logic.

- **`data\_loader.py`** â€” Loads historical diabetes encounter data into PostgreSQL.

- **`sql/schema.sql`** â€” Defines the database tables and their relationships.

- **`tests/`** â€” Contains automated integration tests for the API and database operations.

## Database Setup

The application uses PostgreSQL to store historical patient encounters, calculated risk scores, and care-management interventions.

### 1. Create the PostgreSQL database

Install PostgreSQL and create a database named:

```sql

CREATE DATABASE healthcare\_readmission\_db;

```

Run this command while connected to an existing PostgreSQL database, such as `postgres`.

### 2. Configure database credentials

Copy `.env.example` to `.env` in the project root.

Update `.env` with your local PostgreSQL connection details:

```dotenv

DB\_HOST=localhost

DB\_PORT=5432

DB\_NAME=healthcare\_readmission\_db

DB\_USER=your\_database\_username

DB\_PASSWORD=your\_database\_password

```

The `.env` file contains local credentials and must not be committed to GitHub.

### 3. Create the database tables

Connect to `healthcare\_readmission\_db` using pgAdmin or another PostgreSQL client.

Execute the SQL statements in:

`sql/schema.sql`

This creates two tables:

- **`patient\_encounters`** â€” Stores historical encounter information and risk scores.

- **`care\_interventions`** â€” Stores intervention status, assignments, and notes.

The tables are linked through `encounter\_id`, which is a foreign key in `care\_interventions`.

The script uses `CREATE TABLE IF NOT EXISTS`, so running it again will not fail merely because the tables already exist.

### 4. Load the historical dataset

The application uses the Diabetes 130-US Hospitals dataset.

Place the source dataset in the `data/` directory using the filename `diabetic\_data.csv`.

The `data\_loader.py` script is responsible for importing encounter data and calculated risk information into PostgreSQL.

The source CSV is excluded from GitHub and must be obtained separately.

**Note:** Database creation and schema execution do not automatically populate the tables with encounter data.
