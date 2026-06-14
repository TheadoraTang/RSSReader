from fastapi import APIRouter, Query

from app.repositories import repository

router = APIRouter()


@router.get("/llm/timeseries")
def llm_timeseries(range: str | None = Query(None)):
    return repository.stats_timeseries(range)


@router.get("/llm")
def llm_stats(range: str | None = Query(None)):
    return repository.stats(range)

