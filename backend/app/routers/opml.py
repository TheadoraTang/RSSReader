from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from app.schemas import OPMLImportReport
from app.services import opml_service

router = APIRouter()


@router.post("/import", response_model=OPMLImportReport)
async def import_opml(file: UploadFile = File(...)):
    try:
        return await opml_service.import_opml(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/export")
def export_opml():
    return Response(content=opml_service.export_opml(), media_type="application/xml")

