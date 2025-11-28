# Only keep this endpoint — it’s perfect for admin panel
@router.post("/trigger-pipeline")
async def manual_trigger_pipeline():
    if not await SystemState.is_system_on():
        raise HTTPException(403, detail="System is OFF – enable in /internal/system/on")

    from app.tasks.fmp_delta_update import fmp_delta_update
    fmp_delta_update.delay()  # fire and forget
    return {"status": "Full pipeline triggered manually"}