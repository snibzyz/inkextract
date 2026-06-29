# CLAUDE.md — แนวทางทำงานในโปรเจกต์ INKEXTRACT

## ภาษา UI

- **UI ทั้งหมดเป็นภาษาไทยเท่านั้น** — ป้าย, ปุ่ม, help text, error message, toast, caption
- คงรหัสโฟลเดอร์ (`0-input`, `1-fix`, …), ชื่อไฟล์, code identifier, JSON keys ไว้เป็นภาษาอังกฤษตามเดิม
- ข้อความใน docstring / comment ในโค้ด เขียนไทยหรืออังกฤษได้ตามสะดวก แต่ต้องชัดเจน

## ห้ามใช้ Emoji

- **ห้ามใส่ emoji ในข้อความ UI ทุกชนิด**
- ใช้ **Streamlit material icons** แทน: `":material/<icon_name>:"` (รองรับใน `st.tabs()`, `st.button(icon=...)`, `st.header()`)
- ถ้าต้องระบุสถานะ (มี/ไม่มี/ใช้งาน) ให้ใช้ **คำไทย** เช่น `"พร้อม"`, `"ไม่พบ"`, `"กำลังใช้งาน"` แทนเครื่องหมายภาพ
- ห้ามใส่ emoji ใน docstring / comment ของโค้ดด้วย

## โลโก้

- ไฟล์โลโก้: **`.app/inkideaex.png`** — ติดมากับ source code (กันโดนลบ)
- `ui.page_setup()` ใช้เป็น page icon ของ browser tab อัตโนมัติ — **อย่าส่ง `page_icon=...`** เป็น emoji มา override
- `ui.header()` แสดงโลโก้ในแถบส้มด้านบน

## โครงสร้างโปรเจกต์ (Multi-project workspace)

- **`workspace/`** — โปรเจกต์เริ่มต้น (legacy, backward compat) — ลบไม่ได้
- **`projects/<slug>/`** — โปรเจกต์ที่ผู้ใช้สร้างเพิ่ม (พหูพจน์ของ "project" เพื่อไม่ซ้ำกับชื่อ workspace เดิม)
- **`.config/projects.json`** — registry เก็บรายการโปรเจกต์ + active project
- **ห้ามใช้ชื่อ `workspaces/`** (พหูพจน์ของ workspace) — สับสนกับ `workspace/` (เดิม) ระบบ migrate `workspaces/` → `projects/` ให้อัตโนมัติ
- โครงสร้างโฟลเดอร์ย่อยในแต่ละโปรเจกต์ (PascalCase, INKIDEA-style):
  - `Raw/` — ไฟล์ raw จีนต้นฉบับ
  - `Input/` — ไฟล์แปลตั้งต้น (มี `[A]/[B]` interleave)
  - `Fix/` — ไฟล์ที่แก้ไขแล้ว
  - `Clean/` — ไฟล์ที่ทำความสะอาด
  - `Finish/` — ฉบับเผยแพร่ (จบรอบแล้ว)
  - `Merge/` — ไฟล์รวม
  - `Separate/` — ไฟล์ที่แยกตอน
  - `Import/` — ไฟล์ที่ผู้ใช้แก้กลับ (สำหรับ import) — มี `import_errors.txt` ติดมาด้วย
  - `Output/` — ผลลัพธ์ (`error_trans.txt` ฯลฯ)
  - `Vocab/` — ไฟล์คำศัพท์
  - `Style/` — บันทึกสำนวน
  - `Prompt/` — prompt templates (fix.md ฯลฯ) — **singular ไม่มี s**
  - `Temp/` — archive รอบเก่า
  - `Error/error_trans/` — ข้อความที่แยกไปแปลแก้
- **Migration อัตโนมัติ**: ชื่อเก่า lowercase numbered (`0-input`, `1-fix`, …) ถูก rename เป็น PascalCase ตอน startup ผ่าน `_migrate_legacy_subdir_names()` รองรับ NTFS case-only rename ด้วย 2-step
- ดูแม่แบบโครงโฟลเดอร์เต็มที่ [`.app/templates/inkextract-layout/README.md`](../.app/templates/inkextract-layout/README.md)

## Log File

- **`LOG_FILE = .config/app.log`** (shared, ไม่ใช่ per-project)
- ห้ามใส่ log ลง `output/` ของ project — log ปนกันไม่ดี

## การจัดการ Path

- **อย่าใช้ `from modules.paths import INPUT_DIR`** (จะ snapshot ค่าตอน import)
- **ใช้ `from modules import paths` แล้วเข้าถึง `paths.INPUT_DIR`** เสมอ — เพื่อให้ resolve dynamic ตามโปรเจกต์ที่ active
- หลัง `project_manager.set_active_project()` ต้องเรียก:
  - `app_config.reload_paths()` — refresh singleton
  - ลบ processor instances ใน `st.session_state` (proofreader, file_processor, ฯลฯ)
  - `st.rerun()`

## Default Paths (ในแท็บต่างๆ)

- **Manuscript scan**: `paths.RAW_INPUT_DIR` (raw จีน)
- **Proof — Missing translation scan**: `paths.RAW_INPUT_DIR`
- **Import errors**: ลำดับ `paths.IMPORT_FIX_DIR` → fallback `paths.OUTPUT_DIR`
- **Generate / Files**: `paths.INPUT_DIR`
- **Vocab**: `paths.VOCAB_DIR`

## Export Format (`error_trans.txt`)

- เขียน **master เสมอ** (`output/error_trans.txt`)
- เขียน **`5-import/import_errors.txt`** (สำเนาของ master) ทุกครั้ง — เผื่อ user หลงลบ chunks
- ถ้าตั้ง `chunk_lines > 0` เพิ่ม chunks (`error_trans_001.txt`, `_002.txt`, …)
  - **ห้ามตัดกลาง entry** — chunk boundary ต้องลงตัวที่จบ block
  - **Repeat section + file headers** ในทุก chunk ใหม่ (เพื่อ context)
  - ทุก chunk มี header กำกับ `# แก้ไขเฉพาะบรรทัด [B] เท่านั้น (ส่วนที่ X/Y)` + `# part กำกับ: ส่วนที่ X จาก Y`
  - Entry ของกรณี B (AI ข้ามแปล) มี comment `# [กรณี B] แปลไม่ครบ — กรอก [B] ให้ครบ` ก่อนทุก entry

## Import Match Strategy

- **Phase 1 — Exact match** (normalize whitespace แล้วเทียบเป๊ะ) ผ่าน `build_exact_index`
- **Phase 2 — Fuzzy fallback** (bigram similarity) — threshold ตั้งได้จาก UI slider, default `0.95` (แม่นๆ)
- Anti-false-match: ถ้า top-2 ใกล้กัน (Δratio < 0.02) + คนละไฟล์ → reject
- ผู้ใช้วาง chunks ที่แก้แล้วใน `5-import/` หรือแก้ใน `5-import/import_errors.txt` ในที่ → import จะหยิบจากนั้นก่อน fallback `output/`

## เพิ่มฟีเจอร์ใหม่

- เพิ่มเข้า "หน้าเดิม" ก่อน — อย่าสร้าง tab ใหม่ถ้าไม่จำเป็น
- ถ้าต้องสร้าง tab/sub-tab ใหม่ ใช้ `:material/<icon>:` สำหรับ tab label
- ทุก setting ที่ผู้ใช้ตั้ง → persist ผ่าน `preferences_manager.set_setting()`
- Pure modules (algorithm logic) ไม่พึ่ง Streamlit — แยกใส่ `modules/<name>.py` แล้ว UI tab เรียกใช้

## Testing

- Pure modules มี unit test ใน `tests/`
- Streamlit components ทดสอบด้วย mocked `st` (`types.ModuleType('streamlit')` + NoOp class)
- รัน syntax check ก่อน commit: `python -c "import py_compile; py_compile.compile('<path>', doraise=True)"`

<!-- ink-vault-pointer -->
## INK family — cross-project knowledge

แอปนี้เป็นส่วนหนึ่งของตระกูล INK. **ภาพรวม + ความเชื่อมโยงข้ามแอป** อยู่ใน Obsidian vault กลาง (path เต็มใช้ได้จากทุก worktree บนเครื่องนี้):
- `Z:/Mega Project/INK Vault/Home.md` — แผนผังครอบครัว INK (pipeline: INKCRAW→INKMAGIC/INKIDEA→INKTTS→INKREALM)
- `Z:/Mega Project/INK Vault/Apps/INKEXTRACT.md` — ภาพรวมแอปนี้ · `INK Vault/Topics/` — Shared System / Design / Electron / Infra
- docs structure มาตรฐาน (.claude (ซ่อน) + docs + implement) → `Z:/Mega Project/.shared/docs-structure.md`

เมื่อต้องเข้าใจภาพใหญ่ หรือทำงานคร่อมหลายแอป → อ่าน vault ก่อนลงมือ.
