from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.base import ActivityLog, File, User
from app.auth.deps import get_current_user
from datetime import datetime, timedelta, timezone
import io
import openpyxl

router = APIRouter()


@router.get("/summary")
async def activity_summary(
    period: str = Query("week", pattern="^(week|month)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    if period == "week":
        since = now - timedelta(days=7)
    else:
        since = now - timedelta(days=30)

    # --- File-based stats ---
    result = await db.execute(
        select(File).where(File.created_at >= since)
    )
    all_files = result.scalars().all()

    total_uploads = len(all_files)
    uploads_by_section = {}
    uploads_by_classification = {}
    for f in all_files:
        s = f.section or "Unknown"
        uploads_by_section[s] = uploads_by_section.get(s, 0) + 1
        c = f.classification or "Unknown"
        uploads_by_classification[c] = uploads_by_classification.get(c, 0) + 1

    # Approved files in period
    result_app = await db.execute(
        select(File).where(
            and_(File.created_at >= since, File.status == "Approved")
        )
    )
    approved_files = result_app.scalars().all()
    total_approvals = len(approved_files)
    approvals_by_section = {}
    approvals_by_classification = {}
    for f in approved_files:
        s = f.section or "Unknown"
        approvals_by_section[s] = approvals_by_section.get(s, 0) + 1
        c = f.classification or "Unknown"
        approvals_by_classification[c] = approvals_by_classification.get(c, 0) + 1

    # Rejected files in period
    result_rej = await db.execute(
        select(File).where(
            and_(File.created_at >= since, File.status == "Rejected")
        )
    )
    rejected_files = result_rej.scalars().all()
    total_rejections = len(rejected_files)

    # Current pending files (all time, not just period)
    result_pend = await db.execute(
        select(File).where(File.status == "Pending").order_by(File.created_at.asc())
    )
    pending_files = result_pend.scalars().all()
    total_pending = len(pending_files)

    # --- Activity log (file actions only, no logins) ---
    result_logs = await db.execute(
        select(ActivityLog)
        .where(
            and_(
                ActivityLog.timestamp >= since,
                ActivityLog.action.in_(["upload", "approve", "reject"]),
            )
        )
        .order_by(ActivityLog.timestamp.desc())
    )
    logs = result_logs.scalars().all()

    daily_counts = {}
    for log in logs:
        day = log.timestamp.strftime("%Y-%m-%d") if log.timestamp else "unknown"
        daily_counts[day] = daily_counts.get(day, 0) + 1

    # Timeline by action type
    timeline_by_action = {"upload": {}, "approve": {}, "reject": {}}
    for log in logs:
        day = log.timestamp.strftime("%Y-%m-%d") if log.timestamp else "unknown"
        a = log.action
        if a in timeline_by_action:
            timeline_by_action[a][day] = timeline_by_action[a].get(day, 0) + 1

    return {
        "period": period,
        "since": since.isoformat(),
        "totalUploads": total_uploads,
        "totalApprovals": total_approvals,
        "totalRejections": total_rejections,
        "totalPending": total_pending,
        "uploadsBySection": uploads_by_section,
        "uploadsByClassification": uploads_by_classification,
        "approvalsBySection": approvals_by_section,
        "approvalsByClassification": approvals_by_classification,
        "byDate": dict(sorted(daily_counts.items())),
        "timelineByAction": timeline_by_action,
        "pendingFiles": [
            {
                "id": f.id,
                "fileName": f.file_name,
                "section": f.section,
                "classification": f.classification,
                "uploadedBy": f.uploaded_by,
                "uploadDate": f.created_at.isoformat() if f.created_at else None,
                "daysPending": (now - f.created_at).days if f.created_at else 0,
            }
            for f in pending_files
        ],
        "recentActivity": [
            {
                "id": log.id,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs[:50]
        ],
    }


@router.get("/export")
async def export_activity(
    period: str = Query("week", pattern="^(week|month)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    if period == "week":
        since = now - timedelta(days=7)
    else:
        since = now - timedelta(days=30)

    result = await db.execute(
        select(File).where(File.created_at >= since).order_by(File.created_at.desc())
    )
    files = result.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Files_{period}"

    ws.append(["ID", "File Name", "Section", "Classification", "Status", "Upload Date", "Uploaded By"])
    for f in files:
        ws.append([
            f.id, f.file_name, f.section, f.classification, f.status,
            f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "",
            f.uploaded_by,
        ])

    ws2 = wb.create_sheet("Summary")
    ws2.append(["Files Summary"])
    ws2.append([f"Period: Last {period}"])
    ws2.append([])

    total = len(files)
    approved = sum(1 for f in files if f.status == "Approved")
    pending = sum(1 for f in files if f.status == "Pending")
    rejected = sum(1 for f in files if f.status == "Rejected")
    ws2.append(["Total Files", total])
    ws2.append(["Approved", approved])
    ws2.append(["Pending", pending])
    ws2.append(["Rejected", rejected])

    ws2.append([])
    ws2.append(["Approvals by Section"])
    sections = {}
    for f in files:
        if f.status == "Approved":
            s = f.section or "Unknown"
            sections[s] = sections.get(s, 0) + 1
    ws2.append(["Section", "Count"])
    for s, c in sorted(sections.items(), key=lambda x: -x[1]):
        ws2.append([s, c])

    ws2.append([])
    ws2.append(["Approvals by Classification"])
    classes = {}
    for f in files:
        if f.status == "Approved":
            c = f.classification or "Unknown"
            classes[c] = classes.get(c, 0) + 1
    ws2.append(["Classification", "Count"])
    for c, cnt in sorted(classes.items(), key=lambda x: -x[1]):
        ws2.append([c, cnt])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=files_{period}_{now.strftime('%Y%m%d')}.xlsx"},
    )
