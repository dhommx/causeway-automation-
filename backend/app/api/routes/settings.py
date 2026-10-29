from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_actor
from app.api.schemas import SettingsOut, SettingsSave
from app.config import get_settings
from app.db import get_db
from app.services import settings as settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


def to_out(db: Session) -> SettingsOut:
    return SettingsOut(
        data_folder=str(settings_service.data_folder(db)),
        default_data_folder=str(settings_service.default_data_folder()),
        upload_keep_days=get_settings().upload_keep_days,
    )


@router.get("", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db)):
    return to_out(db)


@router.put("", response_model=SettingsOut)
def save_settings(
    body: SettingsSave,
    db: Session = Depends(get_db),
    actor: str = Depends(current_actor),
):
    try:
        if body.data_folder is None:
            settings_service.reset_data_folder(db, actor)
        else:
            settings_service.set_data_folder(db, body.data_folder, actor)
    except settings_service.SettingsError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return to_out(db)
