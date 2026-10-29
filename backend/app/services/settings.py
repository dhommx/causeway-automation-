"""Portal-wide settings changed from the Settings screen. Today: the data folder."""

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import audit, storage
from app.models import AppSetting

DATA_FOLDER = "data_folder"


class SettingsError(ValueError):
    pass


def default_data_folder() -> Path:
    return Path(get_settings().data_root).resolve()


def data_folder(db: Session) -> Path:
    """Where new files and runs are saved: the folder chosen in the portal, or the default."""
    row = db.get(AppSetting, DATA_FOLDER)
    return Path(row.value["path"]) if row else default_data_folder()


def set_data_folder(db: Session, value: str, actor: str) -> Path:
    """Change the data folder for new uploads and runs. Older files stay where they are."""
    value = value.strip()
    if not value:
        raise SettingsError("Enter a folder path.")
    folder = Path(value).expanduser()
    if not folder.is_absolute():
        raise SettingsError("Enter a full path, e.g. /srv/pie/Data or D:\\PIE\\Data.")
    try:
        storage.check_writable(folder)
    except OSError as exc:
        raise SettingsError(
            f"The portal can't save files in {folder}: {exc.strerror or exc}."
        ) from exc

    old = data_folder(db)
    row = db.get(AppSetting, DATA_FOLDER)
    if row is None:
        row = AppSetting(key=DATA_FOLDER, value={}, actor=actor)
        db.add(row)
    row.value, row.actor = {"path": str(folder)}, actor
    db.flush()
    audit.record(
        db,
        "settings.data_folder",
        "setting",
        DATA_FOLDER,
        {"from": str(old), "to": str(folder)},
        actor,
    )
    return folder


def reset_data_folder(db: Session, actor: str) -> Path:
    """Go back to the default data folder."""
    row = db.get(AppSetting, DATA_FOLDER)
    if row is not None:
        old = row.value["path"]
        db.delete(row)
        db.flush()
        audit.record(
            db,
            "settings.data_folder",
            "setting",
            DATA_FOLDER,
            {"from": old, "to": str(default_data_folder())},
            actor,
        )
    return default_data_folder()
