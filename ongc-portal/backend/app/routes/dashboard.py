from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from app.database import get_db
from app.models.base import File, User, UserPermission
from app.auth.deps import get_current_user

router = APIRouter()

async def _get_scope_files(db: AsyncSession, user: User) -> list:
    """Return files visible to the current user based on their role."""
    result = await db.execute(
        select(File).options(selectinload(File.uploader))
    )
    all_files = result.scalars().all()

    if user.role.name == "admin":
        return list(all_files)

    if user.role.name == "ops_manager":
        mu_res = await db.execute(
            select(User.id).where(User.ops_manager_id == user.id)
        )
        managed_user_ids = {row[0] for row in mu_res.all()}

        ma_res = await db.execute(
            select(User.area).where(
                User.ops_manager_id == user.id,
                User.area.isnot(None),
                User.area != "",
            )
        )
        managed_areas = {row[0] for row in ma_res.all()}
        if user.area:
            managed_areas.add(user.area)

        scoped = []
        for f in all_files:
            if f.uploaded_by == user.id:
                scoped.append(f)
                continue
            in_managed = f.uploaded_by in managed_user_ids or (managed_areas and f.section in managed_areas)
            if in_managed:
                scoped.append(f)
        return scoped

    # Data Creator / Viewer
    scoped = []
    for f in all_files:
        if f.uploaded_by == user.id:
            scoped.append(f)
            continue
        matches_area = not user.area or f.section == user.area
        matches_category = not user.user_category or f.category == user.user_category
        has_filter = user.area or user.user_category
        if has_filter and not (matches_area or matches_category):
            continue
        scoped.append(f)
    return scoped


@router.get("/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    files = await _get_scope_files(db, current_user)

    total = len(files)
    approved = sum(1 for f in files if f.status == "Approved")
    pending  = sum(1 for f in files if f.status == "Pending")
    rejected = sum(1 for f in files if f.status == "Rejected")

    by_section = {}
    by_type = {}
    by_classification = {}

    for f in files:
        if f.section:
            by_section[f.section] = by_section.get(f.section, 0) + 1
        if f.file_type:
            by_type[f.file_type] = by_type.get(f.file_type, 0) + 1
        if f.classification:
            by_classification[f.classification] = by_classification.get(f.classification, 0) + 1

    recent_activity = sorted(
        files,
        key=lambda x: x.upload_date or x.created_at,
        reverse=True
    )[:5]

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "bySection": by_section,
        "byType": by_type,
        "byClassification": by_classification,
        "recentActivity": [
            {
                "id": f.id,
                "fileName": f.file_name,
                "section": f.section,
                "category": f.category,
                "uploadedByName": f.uploader.name if f.uploader else str(f.uploaded_by),
                "uploadDate": f.upload_date.isoformat() if f.upload_date else None,
                "status": f.status,
            }
            for f in recent_activity
        ]
    }
