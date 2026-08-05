# INKEXTRACT — UI/UX Redesign Plan

> **เป้าหมาย:** ออกแบบ UI/UX ใหม่ทั้งเว็บตามหลัก semantic + STEP-based + frontend best practices
>
> **เวอร์ชันที่ plan นี้ผูกอยู่:** เริ่มจาก 1.5.4 (เพิ่งแก้ dropdown row + font tokens เสร็จ)
>
> **เครื่องมือทดสอบ:** Playwright + CDP (verify computed style จริง ไม่ใช่ตาเปล่า)

---

## 0. หลักการ (Design Principles)

ทุก phase ต้องยึด 5 หลักนี้:

1. **Semantic structure** — ใช้ `<h1>`/`<h2>`/`<section>` ตรง role ไม่ใช้ `<div>` ลอยๆ
2. **STEP-based workflow** — ทุก action sequence ต้องมี "ขั้นที่ 1/2/3..." แสดงชัด
3. **Single source of truth** — ห้ามแสดงข้อมูลซ้ำใน 2 ที่ (เช่น project name banner ซ้ำ)
4. **Pipeline-aware defaults** — ปลายทาง suggest step ถัดไป (Input→Fix→Clean→Finish)
5. **Verified by playwright** — ทุกการเปลี่ยนแปลง screenshot + measure ด้วย Playwright + CDP เสมอ — **ห้ามแก้ตาเปล่า**

---

## 1. Current State Analysis (จาก screenshot 1.5.3)

### 1.1 ปัญหาที่ตรวจพบจาก `_screenshots/`

| # | ปัญหา | หลักฐาน | ความสำคัญ |
|---|---|---|---|
| P1 | Orange header สูง ~250px กิน 25% ของ viewport | `light_01_โปรเจกต์.png` | สูง |
| P2 | "Active project" yellow banner ซ้ำกับ section ด้านล่าง | ทุก tab | สูง |
| P3 | KPI stats (4 cards) แสดงตลอด แม้ใน tab ที่ไม่เกี่ยวกับ stats | `light_*` ทุก tab | กลาง |
| P4 | Step indicator ใน Normal mode แสดง ✓ ทั้งที่ยังไม่มี errors | `light_04` | สูง |
| P5 | Dropdown row 40px (เตี้ย) → **แก้แล้วใน 1.5.4** เป็น 52px | verified CDP | แก้แล้ว |
| P6 | Font sizes ไม่ standardize → **แก้แล้วใน 1.5.4** มี tokens | verified | แก้แล้ว |
| P7 | Dark mode contrast ของ orange (KPI numbers) เด่นเกินไป | `dark_04` | ต่ำ |
| P8 | Settings เป็น flat checkbox ไม่ group ตาม purpose | `light_04` | กลาง |
| P9 | Nested expanders ใน Normal mode ทำให้ user สับสน | `light_04` | กลาง |
| P10 | Sub-tabs (โหมด AB / โหมดทั่วไป / ตรวจหลายโฟลเดอร์) ไม่ชัดว่าอยู่ใน main tab ไหน | `light_04` | ต่ำ |

### 1.2 จุดที่ทำได้ดีอยู่แล้ว (อย่าแก้)

-  Main tabs size (52px height หลัง 1.5.3)
-  Button consistency (46px height, orange primary)
-  File management tabs (refactored ใน 1.4.0 — STEP-based + preview)
-  Brand color (orange #F59E0B) — สอดคล้องกับ INKREALM
-  Pipeline-aware folder defaults (1.5.0 onwards)

---

## 2. Phase 1 — Compact + De-duplicate (LOW RISK)

**เป้าหมาย:** ลด visual noise ~30% โดยไม่แก้ logic
**ระยะเวลาประเมิน:** 2-3 hours
**ความเสี่ยง:** ต่ำ (แค่ปรับ layout/CSS — ไม่แก้ flow)
**ไฟล์ที่แตะ:** `.app/modules/ui.py`, `.app/modules/tabs/project.py`, `.app/app.py`

### 2.1 Tasks

#### T1.1 — ย่อ Header banner (P1)
- **ก่อน:** Header ~250px tall (โลโก้ + INKEXTRACT + tagline + install path)
- **หลัง:** Header ~80px (โลโก้ small + INKEXTRACT inline + version chip)
- **ไฟล์:** `ui.py:header()`
- **CSS:**
  ```css
  .ink-header { padding: 0.8rem 1.5rem; min-height: 60px; }
  .ink-header .logo { width: 36px; height: 36px; }
  .ink-header .title { font-size: var(--ink-text-lg); }
  .ink-header .tagline { display: none; }   /* hide on compact */
  .ink-header .install-path { display: none; }
  ```
- **Verify:** screenshot ทุก tab — header ไม่ควรเกิน 80px

#### T1.2 — ลบ "Active project" banner ซ้ำ (P2)
- **ก่อน:** yellow banner "Workspace (เดิม)" แสดงในทุก tab + ใน Project tab มี section "โปรเจกต์ที่ใช้งานอยู่"
- **หลัง:** แสดงเฉพาะใน Project tab — ใน tab อื่น แสดงเป็น text เล็กในมุมขวาบน (status bar)
- **ไฟล์:** `app.py:main()` + `project.py:render_active_bar()`
- **Logic:**
  ```python
  # app.py: render_active_bar() แสดงเฉพาะถ้า current_tab != "โปรเจกต์"
  if active_tab_name != "โปรเจกต์":
      ui.minimal_active_bar()  # compact version
  ```
- **Verify:** screenshot Project tab — แสดง banner; screenshot tab อื่น — ไม่แสดง

#### T1.3 — KPI stats พับเข้า expander (P3)
- **ก่อน:** KPI 4 cards แสดงตลอด
- **หลัง:** `st.expander("สถิติการทำงาน", expanded=False)` — collapsed by default
- **ไฟล์:** `app.py:main()` (หา `ui.stats_cards` หรือ `kpi_row` แล้ว wrap)
- **Verify:** หน้าแรกแสดง expander pinned, click expand เห็น cards

### 2.2 Acceptance criteria

- [ ] Header height < 90px (measure via Playwright)
- [ ] Yellow active banner แสดง 1 ครั้ง/หน้าเสมอ (count `[data-testid="stAlert"]` ที่มี text "โปรเจกต์ที่ใช้งาน")
- [ ] Light + Dark mode ทดสอบทั้งคู่
- [ ] ไม่กระทบ logic — analyze/export/import/fix ของ Normal + AB mode ยังทำงาน

---

## 3. Phase 2 — Consistent STEP Indicator (MEDIUM RISK)

**เป้าหมาย:** Step indicator แสดง state ถูกต้องตามความจริง
**ระยะเวลาประเมิน:** 3-4 hours
**ความเสี่ยง:** กลาง (ต้องคำนวณ state จาก multiple sources)
**ไฟล์ที่แตะ:** `.app/modules/tabs/proof.py` (_render_stepper)

### 3.1 ปัญหา (P4)

ปัจจุบัน stepper:
- AB mode: ✓ → ✓ → ✓ → 4 → 5 (แสดงผิด — ✓ ที่ขั้น 1-3 ทั้งที่ user ยังไม่ทำอะไร)
- Normal mode: คล้ายกัน

ดู `light_04_ตรวจสอบและแก้ไข.png` — ขั้น 1-3 เป็น ✓ เขียว ทั้งที่ user เพิ่งเปิดหน้า

### 3.2 Step state ที่ถูกต้อง

```
ขั้น 1: ตั้งค่า          → ✓ เมื่อ source folder เลือกแล้ว
ขั้น 2: วิเคราะห์         → ✓ เมื่อ found_errors > 0 OR normal_mode_errors > 0
ขั้น 3: ส่งออก           → ✓ เมื่อ Output/error_trans.txt หรือ normal_mode_errors.txt มีอยู่
ขั้น 4: นำเข้า           → ✓ เมื่อ มี corrected_B/corrected_content set ≥ 1
ขั้น 5: แก้ไขไฟล์         → ✓ เมื่อ มี file ใน Fix/ หรือ Finish/ ที่สร้างจาก fix
```

### 3.3 Implementation

แก้ `_ab_step_state()` และ `_normal_step_state()`:
```python
def _ab_step_state(proofreader, export_files_exist):
    has_source = paths.INPUT_DIR.exists() and any(paths.INPUT_DIR.glob("*.txt"))
    has_errors = bool(proofreader.found_errors)
    has_corrections = any(e.get('corrected_B') for e in proofreader.found_errors)
    has_fix_output = paths.FIX_DIR.exists() and any(paths.FIX_DIR.glob("*.txt"))

    done = -1
    if has_source: done = 0
    if has_errors: done = 1
    if export_files_exist: done = 2
    if has_corrections: done = 3
    if has_fix_output: done = 4

    active = min(done + 1, 4)  # next undone step
    return active, done
```

### 3.4 Acceptance criteria

- [ ] เปิดหน้าใหม่ (ยังไม่ analyze): stepper แสดง "1 active, ขั้นอื่นๆ todo (เทา)"
- [ ] หลัง analyze: ขั้น 1+2 = ✓, ขั้น 3 = active
- [ ] หลัง export: ขั้น 1-3 = ✓, ขั้น 4 = active
- [ ] หลัง import: ขั้น 1-4 = ✓, ขั้น 5 = active
- [ ] Light + Dark ทดสอบทั้งคู่
- [ ] AB + Normal mode logic ตรงกัน

---

## 4. Phase 3 — Per-tab Restructure (HIGH RISK, BIG REWRITE)

**ระยะเวลาประเมิน:** 8-12 hours
**ความเสี่ยง:** สูง (แก้ logic + layout ของหลายไฟล์)
**ทำทีละ tab + test ทีละ tab + commit ทีละ tab**

### 4.1 Project tab (`project.py`)

**ปัญหา:**
- KPI cards "สถิติการทำงาน" แสดงข้อมูลของ active project แต่ไม่ชัดว่าเปลี่ยน project ก็เปลี่ยนตามไหม
- ปุ่ม "สร้างโปรเจกต์ใหม่" อยู่ล่างสุด — user หาไม่เจอ
- รายการ project แสดงเป็น list ธรรมดา — ไม่เห็นชัดว่าอันไหน active

**ออกแบบใหม่ (STEP):**

```
┌─ โปรเจกต์ ─────────────────────────────────────────────
│
│ ┌─ Active: Workspace (เดิม) ──────────────────────┐
│ │  E:\Mega Project\INKEXTRACT\workspace             │
│ │  [เปิดโฟลเดอร์]  [เปลี่ยนชื่อ]                    │
│ └────────────────────────────────────────────────┘
│
│ STEP 1 — ดูสถิติ
│   ┌─ ไฟล์ต้นฉบับ ─┐ ┌─ แก้ไข ─┐ ┌─ สะอาด ─┐ ┌─ errors ─┐
│   │      2         │ │    0    │ │    0    │ │    0     │
│   └────────────────┘ └─────────┘ └─────────┘ └──────────┘
│
│ STEP 2 — เลือก/สลับ Project ที่จะใช้งาน
│   ┌─────────────────────────────────────────────┐
│   │ ●  Workspace (เดิม)   [ใช้งานอยู่]   [ลบ]  │  ← card-based
│   │ ○  ProjectA           [สลับไป]       [ลบ]  │
│   │ ○  ProjectB           [สลับไป]       [ลบ]  │
│   │ ─────────────────────────────────────────── │
│   │ [+ สร้าง Project ใหม่]                      │  ← เด่นชัด
│   └─────────────────────────────────────────────┘
│
│ STEP 3 — โฟลเดอร์ย่อย (พับไว้)
│   ▸ [expander] โฟลเดอร์ย่อยของ Workspace (เดิม)
│
│ STEP 4 — ตั้งค่า install root (พับไว้)
│   ▸ [expander] ตำแหน่ง install
└────────────────────────────────────────────────────
```

### 4.2 ตรวจต้นฉบับ tab (`manuscript.py`)

**ปัญหาปัจจุบัน:** มีอยู่แล้วเป็น 2-pane (explorer + preview)
**ปรับปรุง:**
- Pane left ใช้ checkbox + ปุ่มชื่อไฟล์ (clickable) → เคลียร์อยู่แล้ว
- เพิ่ม STEP เหนือ pane

```
ขั้น 1: เลือกโฟลเดอร์ที่จะตรวจ  [folder picker]
ขั้น 2: ตรวจหาไฟล์ขนาดผิดปกติ  [แสดง stats]
ขั้น 3: เลือกไฟล์ที่ต้องการลบ/เรียงเลขใหม่  [explorer + preview]
ขั้น 4: ประมวลผล  [ปุ่ม "ประมวลผล (N)"]
```

### 4.3 คำศัพท์ tab (`vocab.py`)

**ปัญหาปัจจุบัน:** preset cards + composer expander
**ปรับปรุง:**
- ทำให้ STEP 1-4 ชัดเจน (อัปโหลด → สถิติ → เลือกแม่แบบ/ปรับเอง → สร้างไฟล์)
- เพิ่ม helper text "ลากไฟล์มาวางได้เลย"

### 4.4 ตรวจสอบและแก้ไข tab (`proof.py`)

**ปัญหา:** Nested expanders + sub-tabs ทำให้ user สับสน
**ปรับปรุง:**

```
┌─ ตรวจสอบและแก้ไข ────────────────────────────────────
│ [AB mode] [โหมดทั่วไป] [ตรวจหลายโฟลเดอร์]   ← sub-tab
│
│ === stepper === (ใหม่ — แสดง state จริง)
│  ✓ ตั้งค่า → ● วิเคราะห์ → ◯ ส่งออก → ◯ นำเข้า → ◯ แก้ไข
│
│ ── ขั้น 1: ตั้งค่า ──────────────────────────────────
│   เครื่องตรวจ:  ☑ ภาษาต่างประเทศ  ☐ ตัวเลข  ☐ ภาษาอังกฤษ
│   ☑ รวมก่อนตรวจ (กันชื่อไฟล์เพี้ยน — แนะนำ)
│   โฟลเดอร์ต้นทาง: [Clean (แนะนำ)  ▼]
│
│ ── ขั้น 2: วิเคราะห์ ─────────────────────────────────
│   [ วิเคราะห์โหมดทั่วไป ]  ← primary button เด่น
│   เมื่อกดแล้ว: แสดง progress + ผลลัพธ์ + ตาราง errors
│
│ ── ขั้น 3: ส่งออก ───────────────────────────────────
│   chunk lines: [500] | แบ่งเป็น .txt เล็กๆ พอดี AI
│   [ ส่งออกแก้กลับได้ ]
│
│ ── ขั้น 4: นำเข้า ──────────────────────────────────
│   หลัง user/AI แก้ไฟล์ใน Import/ แล้ว → กด
│   [ นำเข้าการแก้ไข ]
│
│ ── ขั้น 5: แก้ไขไฟล์ ────────────────────────────────
│   โฟลเดอร์ปลายทาง: [Finish (แนะนำ)  ▼]
│   [ แก้ไขไฟล์ ]
│
│ ── สรุปผล ─────────────────────────────────────────
│   [tab: ผลลัพธ์ล่าสุด] [tab: รายการบรรทัด] [tab: log]
└────────────────────────────────────────────────────
```

**Key changes:**
- เปลี่ยน 4-column action grid → vertical STEP layout (อ่านง่ายกว่า)
- Settings ใน STEP 1 ไม่ใช่กระจายตามหน้า
- Status box เปลี่ยนเป็น tab — ไม่ขัด flow

### 4.5 จัดการไฟล์ tab (`files_sub/*`)

**ทำเสร็จแล้วใน 1.4.0** — STEP-based + preview + folder picker
**ปรับเพิ่ม Phase 3:**
- เพิ่ม top-level stepper ในแต่ละ sub-tab
- Standardize "Skip first N lines" option (เพิ่มใหม่)

---

## 5. Testing Strategy

### 5.1 Playwright automated visual test

ทุก phase end ต้องรันทั้ง 3 sets:

```python
# Set 1: screenshot all tabs (light + dark)
python _audit_ui.py

# Set 2: measure widget sizes
# (verify: tabs >= 50px, buttons >= 46px, dropdown row >= 52px)

# Set 3: end-to-end flow test
# (verify: analyze → export → import → fix ทำงานครบ)
```

### 5.2 Acceptance per phase

| Phase | KPI | Pass criteria |
|---|---|---|
| 1 | Header height | < 90px (all tabs) |
| 1 | Active banner count | ≤ 1 per page |
| 2 | Step indicator accuracy | ตรงกับ state จริง 100% |
| 3 | New layout works | Full flow (5 steps) ผ่านทุก mode |

### 5.3 Regression check

หลังทุก phase:
- รัน `_test_full_flow.py` (analyze→export→import→fix) — 39/40 ขึ้น
- รัน `_test_merge_mode.py` — 27/27
- รัน `_test_real_scenarios.py` — 25/25

---

## 6. Rollout Plan

```
1.5.5 — Phase 1.T1 (header compact)
1.5.6 — Phase 1.T2 (de-duplicate banner)
1.5.7 — Phase 1.T3 (KPI expander)
1.6.0 — Phase 2 complete (stepper fix)
1.7.0 — Phase 3 partial (Project + Proof restructure)
1.8.0 — Phase 3 complete (all 5 tabs)
2.0.0 — UI/UX redesign complete + ENG translation guide (optional)
```

ทุก release ต้อง:
- Verify ด้วย Playwright + CDP
- Screenshot before/after
- Bump VERSION + tag + push (autoupdate triggers)

---

## 7. Risk Mitigation

| Risk | Mitigation |
|---|---|
| แก้แล้วพัง main flow | รัน regression tests ก่อน commit ทุกครั้ง |
| User confused กับ layout ใหม่ | Phase 3 ทำทีละ tab, ขอ user feedback ระหว่างทาง |
| Streamlit cache CSS เก่า | restart server ทุกครั้งหลังแก้ CSS + verify via Playwright |
| Theme switch ไม่ทำงาน | ทดสอบทั้ง light + dark mode ทุก phase |
| Dark mode contrast bad | screenshot dark + ส่ง user ตรวจ |

---

## 8. Files Touched (Reference)

| File | Phase ที่กระทบ |
|---|---|
| `.app/modules/ui.py` | 1 (header CSS) |
| `.app/app.py` | 1 (active banner conditional) |
| `.app/modules/tabs/project.py` | 1, 3 |
| `.app/modules/tabs/proof.py` | 2 (stepper), 3 (restructure) |
| `.app/modules/tabs/manuscript.py` | 3 |
| `.app/modules/tabs/vocab.py` | 3 |
| `.app/modules/tabs/files_sub/*` | (already done in 1.4.0) |

---

## 9. Anti-patterns to Avoid

ห้ามทำสิ่งเหล่านี้:

1. **ห้ามแก้ตาเปล่า** — ทุก CSS เปลี่ยนต้อง verify ด้วย Playwright + CDP
2. **ห้าม assume Streamlit reload module** — ทุกครั้งที่แก้ ui.py ต้อง restart server
3. **ห้ามใช้ selector แบบเฉพาะเจาะจง** เช่น `.st-emotion-cache-xxxx` (random class)
4. **ห้ามแก้หลาย tab พร้อมกัน** — ทีละ tab + test + commit
5. **ห้ามลบ test scripts** ที่ใช้ verify (`_audit_ui.py`)

---

## 10. Quick Reference — เริ่มต้น Phase ใหม่

```powershell
# 1. Start dev server
cd .app
python -m streamlit run app.py --server.port 8599 --server.headless true

# 2. Verify CSS reload works
# (edit ui.py, restart server, check via _audit_ui.py)

# 3. Implement Phase task
# (edit files, syntax check, test)

# 4. Audit visually
cd ..
python _audit_ui.py
# review _screenshots/ folder

# 5. Run regression tests
python _test_full_flow.py
python _test_merge_mode.py

# 6. Commit + push
git add ...
git commit -m "1.X.Y — Phase N.T..."
git tag -a v1.X.Y -m "..."
git push origin main v1.X.Y
```

---

**Plan วันที่:** 2026-05-16
**Status:** Draft — รอ user approve scope แต่ละ Phase ก่อนเริ่ม
**Last verified version:** 1.5.4 (dropdown 52px, font tokens, theme cleanup)
