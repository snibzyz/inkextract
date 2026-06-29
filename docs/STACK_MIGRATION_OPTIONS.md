# INKEXTRACT — Stack Migration Options

> **คำถามจาก user:** "เปลี่ยน stack ให้สวยกว่านี้ได้ไหม?"
>
> **บริบท:** ปัจจุบันใช้ Streamlit (Python) — UI สวยได้แต่จำกัด · workspace มี INKIDEA / INKCRAW / INKTTS ที่เป็น Electron + React อยู่แล้ว

---

## TL;DR

**3 ทางเลือก ตามลำดับความสมเหตุสมผล:**

1. **อยู่กับ Streamlit + iterate UI** (recommended ระยะสั้น) — 1-2 weeks
2. **Port to Electron + React** (recommended ระยะยาว · match family stack) — 3-6 weeks
3. **NiceGUI / Reflex / Solara** (อยู่ใน Python · UI ดีกว่า Streamlit) — 2-3 weeks

---

## 1. ข้อจำกัดของ Streamlit ปัจจุบัน

### 1.1 ที่ทำได้ดี
- Hot reload สำหรับการพัฒนา
- Python only — ไม่ต้องรู้ JS
- Auto serialize state ผ่าน `st.session_state`
- มี widget พื้นฐานครบ (selectbox, button, etc.)

### 1.2 ที่ติดขัด (จากที่เพิ่งเจอ)
- **CSS override ยาก** — baseweb (react-window virtualization) ใช้ inline style + class hash → ต้อง `!important` + selector tricks
- **No native folder picker** — ต้อง tkinter workaround (ไม่ทำงานบน server)
- **Rerun ทั้ง script ทุกครั้ง** — กดปุ่ม = re-execute ทั้งหน้า (slow)
- **State stale** — เช่น stale `has_errors` (fixed in 1.4.2 by rerun, then fixed properly in 1.5.4)
- **Layout limited** — ไม่มี flexbox/grid จริงจัง · ใช้ `st.columns` ที่ inflexible
- **No real component lifecycle** — ไม่มี mount/unmount → state cleanup ลำบาก
- **Theme switch ไม่ smooth** — ต้อง refresh page หลายครั้ง
- **Dropdown virtual scroll** — มี trick ต้องใช้ position:relative + !important (Phase 1.5.4)

### 1.3 ที่ Streamlit ทำไม่ได้ (หรือยากมาก)
- Real-time collaborative editing
- Drag-and-drop reorder ที่ smooth
- Animation/transition แบบ React Spring
- Native window controls (min/max/close custom)
- Modal dialogs ที่แท้จริง (มีแต่ `st.dialog` ใหม่ๆ ที่ยังจำกัด)
- Right-click context menus
- Keyboard shortcuts ที่ระดับ widget

---

## 2. ตัวเลือกที่ 1 — อยู่กับ Streamlit + Iterate (RECOMMENDED ระยะสั้น)

**เวลาที่ใช้:** 1-2 weeks (ตาม `UI_UX_REDESIGN_PLAN.md` Phase 1-3)
**ความเสี่ยง:** ต่ำ
**ค่าใช้จ่าย:** 0 (ไม่ต้อง learning curve)

### Pros
- ไม่ต้องเขียนใหม่ — แค่ปรับ UI/UX ตาม plan ที่มี
- ฟีเจอร์ทั้งหมด (merge_mode, AB/Normal flow, etc.) อยู่ครบแล้ว
- User test ได้ทันที — ไม่ต้องรอ release ใหญ่

### Cons
- ติดเพดาน Streamlit (CSS override, no native dialogs, etc.)
- ไม่ match family (INKIDEA stack)
- ความสวยจำกัดที่ Streamlit's design system

### ใครเหมาะใช้
- ถ้า user satisfied กับ Streamlit "ที่สวยขึ้นแล้ว" หลัง Phase 3
- ถ้า budget เวลาน้อย

---

## 3. ตัวเลือกที่ 2 — Port to Electron + React (RECOMMENDED ระยะยาว)

**เวลาที่ใช้:** 3-6 weeks (full port + feature parity)
**ความเสี่ยง:** สูง (full rewrite)
**ค่าใช้จ่าย:** Learning curve ของ Electron + React + IPC patterns

### Pros — สำคัญมาก
- **Match family stack** — INKIDEA, INKCRAW, INKTTS ทุกตัวใช้แล้ว
- **มี .shared/ template พร้อม** — `.shared/ui/` มี 8 React primitives สำเร็จ
- **UI control เต็มที่** — flex, grid, animations, modals, drag-drop
- **Native desktop feel** — title bar custom, system tray, file dialogs จริง
- **Faster** — ไม่มี server rerun cycle
- **Reusable patterns** — copy patterns จาก INKIDEA/INKCRAW ได้
- **Bundle distribution** — portable .exe + autoupdate (เหมือนตัวอื่น)

### Cons
- Full rewrite ของทั้ง UI layer
- ต้องสร้าง IPC bridge: Electron main ↔ Python backend (proofreader logic)
- Build pipeline ใหม่ (pnpm + electron-builder + ปรับ Start.bat)
- Test ต้องทำใหม่ทั้งหมด (Playwright on Electron vs Streamlit)

### Architecture proposal
```
INKEXTRACT/
├── .app/
│   ├── shell/                 ← NEW: Electron + React (copy from .shared/)
│   │   ├── electron/
│   │   │   ├── main.cjs
│   │   │   ├── preload.cjs
│   │   │   └── ipc/proofreader.cjs  ← spawn python subprocess
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── tabs/
│   │   │   │   ├── ProjectTab.tsx
│   │   │   │   ├── ManuscriptTab.tsx
│   │   │   │   ├── VocabTab.tsx
│   │   │   │   ├── ProofTab.tsx
│   │   │   │   └── FilesTab.tsx
│   │   │   └── ui/  (จาก .shared/ui/)
│   │   └── package.json
│   ├── python/                 ← KEEP: business logic in Python
│   │   ├── proofreader.py
│   │   ├── file_processor.py
│   │   └── api.py              ← NEW: HTTP/IPC API wrapper
│   └── (deprecated streamlit tabs)
```

### IPC strategy
**Option A** — spawn python subprocess + JSON over stdin/stdout
```javascript
const py = spawn('python', ['api.py'])
py.stdin.write(JSON.stringify({action: 'analyze_normal', dir: '...'}))
py.stdout.on('data', d => /* parse result */)
```

**Option B** — embedded HTTP server (Python FastAPI)
```javascript
fetch('http://localhost:8765/analyze_normal', {body: ...})
```

Option B แนะนำ — clean separation, debug ง่ายกว่า, ใช้ feature เต็มของ FastAPI

### Migration phases
```
Phase A (week 1): scaffold .app/shell/ + basic Electron window + 1 tab dummy
Phase B (week 2-3): port Normal mode (highest priority)
Phase C (week 4): port AB mode
Phase D (week 5): port Project + Manuscript + Vocab tabs
Phase E (week 6): file management tabs + final polish
```

### ใครเหมาะใช้
- ถ้า user committed กับ INKEXTRACT ระยะยาว
- ถ้าต้องการ match brand consistency กับ INKIDEA family
- ถ้ามี budget 3-6 weeks

---

## 4. ตัวเลือกที่ 3 — NiceGUI / Reflex / Solara (Pythonic web alternative)

**เวลาที่ใช้:** 2-3 weeks
**ความเสี่ยง:** กลาง
**ค่าใช้จ่าย:** Learning curve ของ framework ใหม่

### Pros
- อยู่ใน Python — ไม่ต้องสอน team JS
- UI สวยกว่า Streamlit มาก (NiceGUI ใช้ Quasar/Vue, Reflex ใช้ React, Solara ใช้ React)
- Real-time updates (NiceGUI)
- Layout flexible กว่ามาก

### Cons
- ยังเป็น web — ไม่ใช่ desktop จริง
- ไม่ match family stack (Electron)
- Reflex/Solara ยังใหม่ — community ยังเล็ก
- ไม่มี native dialogs

### ตัวเลือกย่อย

#### 3a. NiceGUI (แนะนำที่สุดถ้าเลือกทางนี้)
- ใช้ Quasar (Vue 3) — UI สวยมาก
- API คล้าย Streamlit แต่ flexible กว่า
- มี native window mode (ใช้ pywebview)
- Bundle เป็น .exe ได้
- Code:
  ```python
  from nicegui import ui
  ui.tabs(['Project', 'Manuscript', ...])
  ui.button('วิเคราะห์', on_click=analyze)
  ui.run(native=True, title='INKEXTRACT')
  ```

#### 3b. Reflex (formerly Pynecone)
- ใช้ Next.js เบื้องหลัง
- State management แบบ React
- Compile ออกเป็น static + Python backend

#### 3c. Solara
- ใช้ React (ipyleaflet, ipywidgets ecosystem)
- เหมาะกับ data science > business app

### ใครเหมาะใช้
- ถ้าต้องการ UI ดีขึ้นแต่ไม่อยากเขียน JS
- ถ้า team only Python
- ถ้าไม่ต้อง match Electron family

---

## 5. Decision Matrix

| Criteria | Streamlit (current) | Electron + React | NiceGUI |
|---|---|---|---|
| **UI/UX สวย** | ★★ | ★★★★★ | ★★★★ |
| **Performance** | ★★ | ★★★★★ | ★★★★ |
| **Native feel** | ★ | ★★★★★ | ★★★ |
| **Match family** | ✗ | ✓ | ✗ |
| **Migration effort** | None | High (3-6w) | Medium (2-3w) |
| **Learning curve** | None | High (React+IPC) | Medium (Vue/NG patterns) |
| **Future-proof** | ★★ | ★★★★★ | ★★★ |
| **Bundle size** | Big (Streamlit + Python) | Big (Electron + Chromium) | Small (NiceGUI) |
| **Cost (subscription)** | Free | Free | Free |

---

## 6. คำแนะนำของผม

### Path A — Pragmatic (ถ้า budget เวลาน้อย)
**1-2 weeks:** ทำ Phase 1-3 ของ `UI_UX_REDESIGN_PLAN.md`
- ปรับ Streamlit UI ให้สวยที่สุดเท่าที่ทำได้
- Verify ทุกอย่างด้วย Playwright
- Ship + ดู feedback

**ถ้า user satisfied:** จบ
**ถ้า user ยัง not satisfied:** ค่อยพิจารณา Path B

### Path B — Long-term (RECOMMENDED ถ้า INKEXTRACT จะเป็น core product)
**6 weeks:** Port to Electron + React (Option 2)
- Phase A-E ตามข้างบน
- Match family stack — share code/components กับ INKIDEA
- 1.x = Streamlit (deprecated), 2.x = Electron (new)
- ค่อยๆ migrate users — ไม่ต้องทิ้ง Streamlit ทันที

### Path C — Middle ground (ถ้าอยาก hybrid)
**2-3 weeks:** Migrate to NiceGUI (Option 3a)
- UI สวยขึ้นเลย โดยไม่ต้อง learn JS
- bundle เป็น native window (pywebview)
- ถ้าต่อมาอยาก Electron — port ง่ายกว่า (HTML/CSS reuse ได้บางส่วน)

---

## 7. Estimated comparison — UI components

| Component | Streamlit | Electron+React | NiceGUI |
|---|---|---|---|
| Folder picker | tkinter workaround | native dialog | native dialog |
| Drag-drop reorder | ✗ | dnd-kit / framer-motion | Quasar sortable |
| Step indicator | custom HTML hack | shadcn Stepper | Quasar QStepper |
| Live progress | rerun-based | WebSocket | reactive |
| Modal | st.dialog (จำกัด) | react-modal | Quasar QDialog |
| Toast | st.toast (basic) | sonner / react-hot-toast | Quasar Notify |
| Code editor | st.code (read-only) | Monaco / CodeMirror | Monaco |
| Diff viewer | ไม่มี | react-diff-viewer | manual |

---

## 8. Risk-adjusted recommendation

ถ้า:
- งานเร่ง / budget น้อย → **Path A** (Streamlit + Phase 1-3)
- พร้อม invest 6 weeks → **Path B** (Electron + React)
- ต้องสวยขึ้นเร็ว, ไม่ต้อง match family → **Path C** (NiceGUI)

**ของผม:** ถ้า user มี time → **Path B** เพราะ:
- INKEXTRACT จะอยู่ในตระกูล INK ที่ stack เดียวกัน
- ใช้ `.shared/` template ที่มีอยู่แล้ว ลด effort
- Maintain ง่ายระยะยาว
- ลด tech debt (Streamlit ทุกอย่างต้อง workaround)

---

## 9. Quick start — Path B (Electron) — สำหรับ reference

ถ้าตัดสินใจเลือก Path B:

```powershell
# 1. ดู template ที่มีอยู่
cd "Z:\Mega Project\.shared"
cat checklist-new-app.md

# 2. Scaffold .app/shell/
cd "Z:\Mega Project\INKEXTRACT\.app"
mkdir shell
xcopy /E /I "..\..\.shared\config\*" shell\
xcopy /E /I "..\..\.shared\src\*" shell\src\
xcopy /E /I "..\..\.shared\ui\*" shell\src\ui\
xcopy /E /I "..\..\.shared\electron\*" shell\electron\

# 3. Find-replace placeholders
# {{APP_LOWER}} → inkextract
# {{APP_UPPER}} → INKEXTRACT
# {{APP_NAME}} → INKEXTRACT
# {{VITE_PORT}} → 5673 (จอง port ใน .shared/ports.md)
# {{GITHUB_*}} → snibzyz/inkextract

# 4. Install
pnpm install

# 5. Run dev
pnpm dev
```

ดู `.shared/checklist-new-app.md` ใน workspace สำหรับ step-by-step

---

**คำถามที่ต้อง decide ก่อนตัดสินใจ:**

1. INKEXTRACT จะอยู่ระยะยาวไหม (ยังจะพัฒนาต่ออีก 6+ เดือนไหม)?
2. มี budget 3-6 weeks สำหรับ migration ไหม?
3. user (= คุณ) อยากมาเป็น family เดียวกับ INKIDEA / INKCRAW / INKTTS ไหม?
4. ความสำคัญของ UI สวย vs ความเร็วในการ ship ฟีเจอร์ใหม่?

**ถ้าตอบ ใช่ → ใช่ → ใช่ → UI สวย** = ไป Electron
**ถ้าตอบ ไม่แน่ใจ → จำกัด → ไม่จำเป็น → ship เร็ว** = อยู่ Streamlit + Phase 1-3

---

**Doc created:** 2026-05-16
**Status:** Decision pending — รอ user pick path
