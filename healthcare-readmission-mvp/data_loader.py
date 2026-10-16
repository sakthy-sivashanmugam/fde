import csv
from pathlib import Path
from database import get_connection

CSV_PATH = Path(__file__).resolve().parent / "data" / "diabetic_data.csv"
BATCH_SIZE = 1000

REQUIRED_COLUMNS = [
    "encounter_id",
    "patient_nbr",
    "age",
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
    "num_lab_procedures",
    "discharge_disposition_id",
    "admission_type_id",
    "readmitted",
]

INSERT_ENCOUNTER_SQL = """
    INSERT INTO patient_encounters (
        encounter_id,
        patient_nbr,
        age,
        time_in_hospital,
        number_inpatient,
        number_emergency,
        number_outpatient,
        num_medications,
        num_lab_procedures,
        discharge_disposition_id,
        admission_type_id,
        readmitted
    )
    VALUES (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (encounter_id) DO NOTHING;
"""

def inspect_csv():
    with open(CSV_PATH, mode="r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(f"Missing required columns in CSV: {missing_columns}")

        first_row = next(reader)

        selected_row = {column: first_row[column] for column in REQUIRED_COLUMNS}

        rejected_records = []

        # Test 1: Valid record
        valid_result = validate_and_transform(
            selected_row, 2, rejected_records
        )

        # Test 2: Invalid record
        invalid_row = selected_row.copy()
        invalid_row["time_in_hospital"] = "UNKNOWN"

        invalid_result = validate_and_transform(
            invalid_row, 3, rejected_records
        )

        print("Valid result:", valid_result is not None)
        print("Invalid result:", invalid_result)
        print("Rejected records:", rejected_records)

        transformed_row = transform_encounter(selected_row)

        
def transform_encounter(row):
    numeric_columns = [
        "encounter_id",
        "patient_nbr",
        "time_in_hospital",
        "number_inpatient",
        "number_emergency",
        "number_outpatient",
        "num_medications",
        "num_lab_procedures",
        "discharge_disposition_id",
        "admission_type_id",
    ]

    transformed_row = row.copy()

    for column in numeric_columns:
        try:
            transformed_row[column] = int(row[column])
        except (ValueError, TypeError) as error:
            raise ValueError(
            f"Invalid value '{row[column]}' "
            f"for column '{column}' "
            f"in encounter {row.get('encounter_id')}"
            ) from error

    if transformed_row["time_in_hospital"] <= 0:
        raise ValueError(
        f"Invalid hospital stay "
        f"'{transformed_row['time_in_hospital']}' "
        f"for encounter {transformed_row['encounter_id']}"
        )

    utilization_columns = [
        "number_inpatient",
        "number_emergency",
        "number_outpatient",
        "num_medications",
        "num_lab_procedures",
    ]

    for column in utilization_columns:
        if transformed_row[column] < 0:
            raise ValueError(
            f"Negative value '{transformed_row[column]}' "
            f"for column '{column}' "
            f"in encounter {transformed_row['encounter_id']}"
        )

    return transformed_row

def insert_encounter(encounter):
    values = tuple(
        encounter[column]
        for column in REQUIRED_COLUMNS
    )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(INSERT_ENCOUNTER_SQL, values)

            print("Rows inserted:", cursor.rowcount)

def create_batches(records, batch_size):
    for index in range(0, len(records), batch_size):
        yield records[index:index + batch_size]

def validate_and_transform(row, row_number, rejected_records):
    try:
        return transform_encounter(row)

    except ValueError as error:
        rejected_records.append({
            "row_number": row_number,
            "encounter_id": row.get("encounter_id"),
            "reason": str(error)
        })
        return None

def validate_full_csv():
    seen_encounter_ids = set()
    total_records = 0
    valid_records = 0
    rejected_records = []
    

    with open(CSV_PATH, mode="r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        missing_columns = [
            column for column in REQUIRED_COLUMNS
            if column not in (reader.fieldnames or [])
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}"
            )

        for row_number, row in enumerate(reader, start=2):
            total_records += 1

            selected_row = {
                column: row[column]
                for column in REQUIRED_COLUMNS
            }

            result = validate_and_transform(
                selected_row,
                row_number,
                rejected_records
            )

            if result is not None:
                
                if result is not None:
                    encounter_id = result["encounter_id"]

                    if encounter_id in seen_encounter_ids:
                        rejected_records.append({
                        "row_number": row_number,
                        "encounter_id": encounter_id,
                        "reason": "Duplicate encounter_id"
                    })
                    else:
                        seen_encounter_ids.add(encounter_id)
                        valid_records += 1

    print("\nCSV Validation Summary")
    print("----------------------")
    print("Total records:", total_records)
    print("Valid records:", valid_records)
    print("Rejected records:", len(rejected_records))

    print(
        "Reconciliation:",
        total_records == valid_records + len(rejected_records)
    )

    if rejected_records:
        print("\nFirst 5 rejected records:")
        for record in rejected_records[:5]:
            print(record)

def prepare_batch_values(batch):
    return [
        tuple(encounter[column] for column in REQUIRED_COLUMNS)
        for encounter in batch
    ]


def load_all_encounters():
    valid_records = []
    rejected_records = []
    seen_encounter_ids = set()
    total_records = 0

    with open(CSV_PATH, mode="r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        missing_columns = [
            column for column in REQUIRED_COLUMNS
            if column not in (reader.fieldnames or [])
        ]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        for row_number, row in enumerate(reader, start=2):
            total_records += 1

            selected_row = {
                column: row[column]
                for column in REQUIRED_COLUMNS
            }

            encounter = validate_and_transform(
                selected_row, row_number, rejected_records
            )

            if encounter is None:
                continue

            encounter_id = encounter["encounter_id"]

            if encounter_id in seen_encounter_ids:
                rejected_records.append({
                    "row_number": row_number,
                    "encounter_id": encounter_id,
                    "reason": "Duplicate encounter_id"
                })
                continue

            seen_encounter_ids.add(encounter_id)
            valid_records.append(encounter)

    print("Total CSV records:", total_records)
    print("Valid records:", len(valid_records))
    print("Rejected records:", len(rejected_records))

    if total_records != len(valid_records) + len(rejected_records):
        raise RuntimeError("CSV reconciliation failed")

    inserted_records = 0
    skipped_records = 0

    with get_connection() as connection:
        for batch_number, batch in enumerate(
            create_batches(valid_records, BATCH_SIZE), start=1
        ):
            batch_values = prepare_batch_values(batch)
            batch_inserted = 0

            try:
                with connection.transaction():
                    with connection.cursor() as cursor:
                        for values in batch_values:
                            cursor.execute(INSERT_ENCOUNTER_SQL, values)
                            batch_inserted += cursor.rowcount

                # Update totals only after the transaction succeeds.
                inserted_records += batch_inserted
                skipped_records += len(batch_values) - batch_inserted

                print(f"Batch {batch_number} committed")

            except Exception:
                connection.rollback()
                raise

    print("Inserted records:", inserted_records)
    print("Skipped records:", skipped_records)


if __name__ == "__main__":
    load_all_encounters()