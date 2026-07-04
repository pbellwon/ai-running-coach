from pathlib import Path
import gzip
import fitdecode


def fit_message_to_dict(frame):
    return {
        field.name: field.value
        for field in frame.fields
    }


class FITImporter:
    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)

    def list_files(self):
        return list(self.folder_path.glob("*.FIT.gz"))

    def load_files(self):
        files = self.list_files()

        return {
            "total_files": len(files),
            "sample": [f.name for f in files[:5]],
        }

    def decode_file(self, file: Path):
        records = []
        sessions = []
        laps = []

        with gzip.open(file, "rb") as gz:
            with fitdecode.FitReader(gz) as fit:
                for frame in fit:
                    if frame.frame_type != fitdecode.FIT_FRAME_DATA:
                        continue

                    if frame.name == "record":
                        records.append(fit_message_to_dict(frame))

                    elif frame.name == "session":
                        sessions.append(fit_message_to_dict(frame))

                    elif frame.name == "lap":
                        laps.append(fit_message_to_dict(frame))

        return {
            "file": file.name,
            "records": records,
            "sessions": sessions,
            "laps": laps,
            "records_count": len(records),
            "sessions_count": len(sessions),
            "laps_count": len(laps),
            "first_record": records[0] if records else None,
            "session": sessions[0] if sessions else None,
        }

    def decode_one_file(self):
        file = self.list_files()[0]
        return self.decode_file(file)