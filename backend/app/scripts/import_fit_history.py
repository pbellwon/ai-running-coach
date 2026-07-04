from app.db.database import SessionLocal, Base, engine
from app.db.models import WorkoutDB, LapDB, RecordDB
from app.services.fit_importer import FITImporter

Base.metadata.create_all(bind=engine)

importer = FITImporter("data/imports/trainingpeaks_fit")
files = importer.list_files()

print("=== PaceMind FIT Import TEST ===")
print(f"Total files found: {len(files)}")

db = SessionLocal()

created_workouts = 0
created_laps = 0
created_records = 0
skipped = 0
failed = 0

for file in files:
    try:
        print(f"PROCESSING: {file.name}", flush=True)

        exists = db.query(WorkoutDB).filter_by(source_file=file.name).first()
        if exists:
            skipped += 1
            print(f"SKIPPED: {file.name}", flush=True)
            continue

        decoded = importer.decode_file(file)
        session = decoded["session"]

        if not session:
            failed += 1
            print(f"FAILED: {file.name} | no session", flush=True)
            continue

        workout = WorkoutDB(
            source_file=file.name,
            start_time=session.get("start_time") or session.get("timestamp"),
            sport=str(session.get("sport")),
            distance_km=(session.get("total_distance") or 0) / 1000,
            duration_sec=session.get("total_elapsed_time"),
            avg_hr=session.get("avg_heart_rate"),
            max_hr=session.get("max_heart_rate"),
            records_count=decoded["records_count"],
            laps_count=decoded["laps_count"],
        )

        db.add(workout)

        for index, lap in enumerate(decoded["laps"], start=1):
            db.add(
                LapDB(
                    workout_file=file.name,
                    lap_number=index,
                    distance_m=lap.get("total_distance"),
                    elapsed_time_sec=lap.get("total_elapsed_time"),
                    avg_hr=lap.get("avg_heart_rate"),
                    max_hr=lap.get("max_heart_rate"),
                )
            )
            created_laps += 1

        for record in decoded["records"]:
            db.add(
                RecordDB(
                    workout_file=file.name,
                    timestamp=record.get("timestamp"),
                    latitude=record.get("position_lat"),
                    longitude=record.get("position_long"),
                    heart_rate=record.get("heart_rate"),
                    cadence=record.get("cadence"),
                    altitude=record.get("enhanced_altitude") or record.get("altitude"),
                    speed=record.get("enhanced_speed") or record.get("speed"),
                )
            )
            created_records += 1

        db.commit()
        created_workouts += 1

        print(
            f"IMPORTED: {file.name} | "
            f"laps={decoded['laps_count']} records={decoded['records_count']}",
            flush=True,
        )

    except Exception as e:
        db.rollback()
        failed += 1
        print(f"FAILED: {file.name} | {e}", flush=True)

db.close()

print("---")
print(f"Checked files: 1")
print(f"Created workouts: {created_workouts}")
print(f"Created laps: {created_laps}")
print(f"Created records: {created_records}")
print(f"Skipped: {skipped}")
print(f"Failed: {failed}")