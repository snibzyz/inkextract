# INKEXTRACT POC — Reflex

> Proof-of-concept ของ Project tab ทำด้วย [Reflex](https://reflex.dev) (Python → Next.js + React)
> เทียบกับ Streamlit เพื่อดูว่า "modern web feel" เป็นยังไง

## โครงสร้าง

```
_poc_reflex/
├── rxconfig.py                       Reflex config
├── inkextract_poc/
│   ├── __init__.py
│   └── inkextract_poc.py             ทั้งแอป (state + components)
├── Install.bat                       ติดตั้ง reflex (รันครั้งเดียว)
├── Start.bat                         รัน dev server
└── README.md                         (คุณกำลังอ่าน)
```

## วิธีรัน (ครั้งแรก)

```powershell
# 1. ติดตั้ง (ครั้งเดียว) — ใช้ .venv ของ INKEXTRACT
.\Install.bat

# 2. รัน dev server
.\Start.bat
```

แล้วเปิด browser ที่ **http://localhost:3500**

## สิ่งที่ POC แสดง

- **Top brand bar** — amber gradient + version chip
- **Active project bar** — slim 1-line context indicator
- **Stats card** — collapsible KPI summary
- **Tab navigation** — 5 tabs (โปรเจกต์ · ตรวจต้นฉบับ · …)
- **Active project hero card** — gradient amber + big name + path code box + action buttons
- **Project list** — radio icon + name + path + active state (border ส้ม + tint bg + "กำลังใช้งาน" badge)
- **Create new form** — toggle expand + form + toast notification

## State management

ใช้ `rx.State` class — Python class แบบ pure Pydantic
- `State.projects` — list of dicts
- `State.active_id` — string
- `State.switch_project(id)` — event handler ทำงานบน backend, sync state ไป frontend อัตโนมัติ
- ไม่มี rerun pattern เหมือน Streamlit — กดปุ่มเรียก method ตรง ๆ

## เทียบกับ Streamlit (port 8501)

| feature | Streamlit | Reflex POC |
|---|---|---|
| Look & feel | Dashboard | Modern web app (SaaS) |
| State | session_state dict | typed class |
| Interactivity | rerun ทั้งหน้า | partial update ผ่าน socket |
| Component library | จำกัด (st.*) | Radix UI + Lucide icons |
| Theme switching | reload page | smooth toggle |
| Hot reload | ✓ | ✓ (auto via vite) |
| Bundle desktop | server ผ่าน browser | export static + electron/tauri |

## Port

- Frontend (vite dev): **4500**
- Backend (granian WS): **4501**

หลีกเลี่ยง: Streamlit (8501), INK Electron Vite (5173-5573), Reflex defaults (3000/8000)

## ฟีเจอร์ที่ยังไม่ port (POC จงใจสั้น)

- Other 4 tabs (ตรวจต้นฉบับ, คำศัพท์, ตรวจสอบและแก้ไข, จัดการไฟล์) — เป็น tab nav แต่ไม่มีเนื้อหา
- Real folder picker (ตอนนี้แค่ toast)
- จริงๆ wire ขึ้น project_manager ของ INKEXTRACT (ใช้ mock data)

## ถ้าจะ port เต็มแอป

ดู `.docs/STACK_MIGRATION_OPTIONS.md` Section 4 — Reflex section
ประมาณ 2-3 weeks สำหรับ 5 tabs + IPC ไป business logic Python
