from app.db.database import SessionLocal, Base, engine
from app.db.models import WorkoutDB
from app.services.fit_importer import FITImporter

Base.metadata.create_all(bind=engine)

importer = FITImporter("data/imports/trainingpeaks_fit")
files = importer.list_files()

db = SessionLocal()

created = 0
skipped = 0
failed = 0

for file in files:
    try:
        exists = db.query(WorkoutDB).filter_by(source_file=file.name).first()
        if exists:
            skipped += 1
            continue

        summary = importer.decode_summary(file)
        if summary is None:
            failed += 1
            continue

        workout = WorkoutDB(**summary)
        db.add(workout)
        db.commit()

        created += 1
        print(f"IMPORTED: {file.name}")

    except Exception as e:
        db.rollback()
        failed += 1
        print(f"FAILED: {file.name} | {e}")

db.close()

print("---")
print(f"Total files: {len(files)}")
print(f"Created: {created}")
print(f"Skipped: {skipped}")
print(f"Failed: {failed}")