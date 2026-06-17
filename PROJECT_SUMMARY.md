# Data Vision — Complete Project Summary

## Project Overview
Enterprise file management system with role-based access, approval workflow, notifications, drill-down analytics, area/category-based access control, semantic PDF search with vector embeddings, OCR for scanned PDFs, and background summarization.

---

## 1. AUTHENTICATION & ACCESS
- Login with CPF (employee ID) + password
- JWT token-based session (1h expiry, refresh token 7d)
- bcrypt password hashing
- Session persists via browser `sessionStorage`
- 5 pre-seeded users with distinct roles

## 2. USER ROLES (4 roles, fixed IDs 1-4)
| Role | ID | Sees | Can Do |
|------|----|------|--------|
| Admin | 1 | All 4 classifications | Full control, user management, settings |
| Ops Manager | 2 | General + Sensitive | Approve/reject files |
| Data Creator | 3 | General + own uploads | Upload files, view own |
| Viewer | 4 | General only | Download approved files |

## 3. USER MANAGEMENT (Admin)
- Table of all users with roles, CPF, name, section, location
- Change user role via dropdown
- Only role named "admin" is immutable (cannot be changed)
- Any user can be promoted to admin
- Grant temporary classification access — auto-expires in 1 hour
- Expired permissions auto-filtered from API

## 4. SIDEBAR NAVIGATION (role-specific)
**Admin (11):** Dashboard, Upload File, File Records, Pending Approval, Approved Files, Rejected Files, Reports, Activity, Users, Settings, Logout

**Ops Manager (8):** Dashboard, Upload File, File Records, Pending Approval, Approved Files, Rejected Files, Reports, Logout

**Data Creator (5):** Dashboard, Upload File, My Files, Reports, Logout

**Viewer (5):** Dashboard, File Records, Approved Files, Reports, Logout

## 5. FILE UPLOAD
- 7 dropdown fields: Section, Category (53), Season (70+), Block (5), File Type (7), Data Type (4), Classification (4)
- All dropdowns stored in `lookups` DB table — managed via Settings page
- File saved to disk: `Myuploads/{category_sanitized}/{classification_sanitized}/{filename}`
- File data also stored in DB as `file_data` (BYTEA column) for redundancy
- Original filename preserved on disk
- 53 categories × 5 classifications → 265 folders pre-created on disk
- Upload performance: ~0.3–0.7s warm (model pre-loaded at startup)

## 6. FILE RECORDS
- Tabular view: S.No, File Name, Category, Classification, Section, Season, Uploaded By, Status, Actions
- Search by file name
- Filter by status: All / Pending / Approved / Rejected
- Classification badges with colors: General (green), Sensitive (orange), Confidential (red), Highly Confidential (purple)
- Download approved files; View restricted files
- File detail modal with summary, metadata, action buttons

## 7. APPROVAL WORKFLOW
1. Data Creator uploads → status = Pending
2. Ops Manager / Admin reviews in Pending Approval page
3. Approve — optional classification change at approval time
4. Reject — mandatory reason required
5. Approval → notification: "Your file X has been approved by Y"
6. Rejection → notification: "Your file X was rejected by Y. Reason: ..."

## 8. NOTIFICATIONS
- Bell icon in header with red unread count badge
- Click bell → dropdown shows all notifications
- Mark individual notification as read (✔ button)
- "Mark all read" button
- Auto-polls every 15 seconds
- Notification types: approval, rejection (with reason)

## 9. DASHBOARD
- Role-specific stats cards: total files, pending, approved, rejected counts
- Bar chart — monthly file uploads (last 12 months)
- Gradient stat card design
- Clickable stat cards → drill-down to filtered file modals

## 10. REPORTS
- Monthly file upload statistics
- Bar chart visualization
- Available to all roles
- Excel export with 2 sheets (detail + summary)

## 11. ACTIVITY ANALYTICS
- File-centric stats: totalUploads, totalApprovals, totalRejections, totalPending
- Uploads/Approvals by Section and Classification (horizontal bar charts)
- Pending files table with age highlighting (>48h)
- Activity timeline (daily breakdown)
- Recent file action log
- Period toggle: week / month

## 12. SETTINGS — DROPDOWN MANAGER (Admin)
- 7 lookup types: Sections, Categories, Seasons, Blocks, File Types, Data Types, Classifications
- Add / Edit / Delete values
- Changes reflect instantly in upload forms
- 156+ pre-seeded values

## 13. FILE STORAGE SYSTEM
- **Disk:** `Myuploads/{category}/{classification}/{filename}` (original name)
- **DB:** `file_data` column (BYTEA) as redundancy
- All IDs are clean auto-increment integers (no UUIDs anywhere)
- Primary/foreign keys across all tables use integers

## 14. DATABASE (PostgreSQL 15 + pgvector)
- Docker container on port 5433 (`backend-db-1`)
- pgvector extension installed for vector embeddings (384 dims)
- 13 tables: `users`, `roles`, `files`, `approvals`, `classifications`, `lookups`, `notifications`, `user_permissions`, `activity_logs`, `document_chunks`, `kg_entities`, `kg_relationships`, `ai_audit_logs`
- pgAdmin on port 5050 (admin@ongc.com / admin123)

## 15. BACKEND (Python FastAPI)
- REST API on port 8000
- SQLAlchemy async ORM + asyncpg driver
- Routes: auth, users, files, approvals, notifications, reports, permissions, activity, lookups, dashboard, database, ai
- System Python 3.14 (no venv)
- uvicorn with hot reload

## 16. FRONTEND (React + Vite)
- Vite dev server on port 5173
- Vite proxy: `/api` → `http://localhost:8000`
- Same-origin `window.open` for PDF viewing (no popup blocker)
- React functional components with hooks
- Axios for API calls with token interceptor

## 17. PDF HANDLING
- **Text PDFs:** PyMuPDF extracts text → embedding → summary pipeline
- **Scanned PDFs:** Auto-detected (<50 chars from PyMuPDF) → Tesseract OCR (eng+hin, 300 DPI)
- **OCR pipeline:** pdf2image → Pillow preprocessing (grayscale, median denoise, binarize) → Tesseract PSM 6 + OEM 3
- **File viewing:** Browser's native PDF viewer via `window.open('/api/files/view/{id}?token={token}')`
- Content-Disposition: inline, Content-Type: application/pdf

## 18. SEARCH
- **Keyword search:** SQL `ILIKE` on file name + search_text
- **Vector search:** BAAI/bge-small-en-v1.5 embeddings (384 dims), cosine distance via pgvector
- Hybrid merge: both methods run in parallel, deduplicated
- Results show snippets with "Exact" (blue badge) or "Related" (green badge)
- No API key needed — fully local

## 19. SUMMARIZATION
- Model: BAAI/bge-small-en-v1.5 (same as embeddings) — TextRank algorithm
- Extractive summarization on sentence embeddings
- Chunks at 250 sentences for large documents
- Runs as `BackgroundTasks` after upload response (non-blocking)

## 20. EMBEDDING MODEL
- Model: `BAAI/bge-small-en-v1.5` from sentence-transformers
- 384 dimensions, normalized vectors
- Pre-loaded at server startup (~8.5s) for zero cold-start delay
- Singleton pattern via `get_model()` in `embeddings.py`

## 21. UI/DESIGN SYSTEM
- Font: Segoe UI, system-ui, Arial, sans-serif
- Dark blue header gradient (#0b3d91 → #1565c0)
- Dark sidebar (#1a2632)
- Card-based layout with box shadows
- Table text 14px, small elements 13px, tiny 12px
- Main content padding: 20px 32px
- Footer hidden after login
- Buttons with shadows + hover transitions
- Toast notifications for success/error feedback

## 22. DELETED / REMOVED FEATURES
- Search/AI Chat endpoints removed (chat + AI chat tables deleted)
- Login tracking/deletion removed from activity logs
- pdf.js custom viewer removed (uses native browser viewer instead)

## 23. ADMIN CREDENTIALS
| CPF | Password | Name | Role |
|-----|----------|------|------|
| 100001 | admin123 | — | Admin |
| 100005 | Rucha | — | Admin |
| 100018 | gpops | Sanjay | Ops Manager (GP) |
| 100019 | relops | Ravi | Ops Manager (Rel) |
| 100027 | assetops | Vikas | Ops Manager (Asset) |
| 100003 | user123 | Mahavir | Data Creator (GP-36) |
| 100004 | view123 | — | Viewer |

## 24. KEY DESIGN DECISIONS
- All IDs are integers (no UUIDs anywhere)
- Admin role immutable by role name "admin"
- Permission grants expire after 1 hour (hardcoded, no cleanup job)
- Section (department) and Location (geo area) are separate fields
- `section_config` table keys on department name for auto-deriving user defaults
- File on disk uses original filename; DB has BYTEA backup
- Upload directory: `/Users/ruchatejaskumargandhi/Downloads/Myuploads/`
- Docker PostgreSQL with pgvector on port 5433
- No external API keys for search/summarization (fully local)
- Model pre-loaded at startup to avoid cold-start delay

## 25. CURRENT STATE
- **Total files:** 21 (files 1-23 + 32, excluding deleted)
- **Status:** 9 pending, 10 approved, 2 rejected
- **Files with search_text:** 15 (PDFs only)
- **Files with summaries:** 16
- **Files with embeddings:** 15
- **5 non-PDFs** (CSV, xlsx) — no search_text/extraction
- **File 32** (FIS_Accounts_2020-21.pdf) — garbled OCR (low-quality scan)
- **All 21 files** return HTTP 200 on view/pdfviewer endpoints

## 26. CRITICAL FILES
| File | Purpose |
|------|---------|
| `backend/app/main.py` | App entry, routes, CORS, model pre-load |
| `backend/app/routes/files.py` | Upload, view, search, approval, pdf viewer |
| `backend/app/utils/ocr.py` | Tesseract OCR for scanned PDFs |
| `backend/app/utils/embeddings.py` | BAAI/bge-small-en-v1.5 embedding model |
| `backend/app/utils/summarize.py` | TextRank summarization on embeddings |
| `backend/app/utils/pdf_extract.py` | PyMuPDF text extraction |
| `backend/app/config.py` | Settings (DB, model, upload dir) |
| `backend/app/database.py` | Async session factory, DB URL |
| `src/App.jsx` | Main React component |
| `src/api.js` | API client (fetch + auth) |
| `vite.config.js` | Vite proxy config |
| `docker-compose.yml` | PostgreSQL + pgAdmin containers |

## 27. TECHNICAL SPECS
- **Backend:** Python 3.14, FastAPI, SQLAlchemy async, asyncpg
- **Frontend:** React 18, Vite 6, Axios
- **Database:** PostgreSQL 15 + pgvector (Docker, port 5433)
- **Embeddings:** BAAI/bge-small-en-v1.5 (384 dims, sentence-transformers)
- **OCR:** Tesseract 5.5.2, pdf2image (poppler), Pillow
- **Vector dims:** 384 (matching bge-small-en-v1.5)
- **Git remote:** `https://github.com/Rucha1811/ongc-new.git`
