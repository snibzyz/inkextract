# INKEXTRACT — ภาพรวมโฟลเดอร์ (Workspace + Project)

เอกสารนี้สรุป **โครงที่แอปคาดหวัง** ให้ตรงกับ `modules/paths.py` และ `modules/project_manager.py`
ใช้เป็นต้นแบบเวลาสร้าง workspace มือ / ตรวจว่าโฟลเดอร์ครบหรือไม่

ออกแบบตามแนวทาง INKIDEA — PascalCase folder names + multi-project layout

---

## 1) รากของระบบ (สิ่งที่อยู่ข้างนอก project root)

```text
<INKEXTRACT_ROOT>/
├── .app/                      # source code (Python + Streamlit)
│   ├── inkideaex.png          # logo (ติดมากับ source — กันโดนลบ)
│   ├── VERSION                # current version (e.g. 1.0.6)
│   └── ...
├── .config/                   # shared config + log (ไม่ใช่ per-project)
│   ├── settings.json
│   ├── user_preferences.json
│   ├── projects.json          # registry — รายชื่อโปรเจกต์ + active
│   ├── exclude.txt            # regex patterns
│   └── app.log
├── .claude/                   # Claude-specific notes (CLAUDE.md ฯลฯ)
├── workspace/                 # โปรเจกต์เริ่มต้น (legacy default — ลบไม่ได้)
└── projects/                  # โปรเจกต์ที่ user สร้างเพิ่ม (พหูพจน์ของ project)
    ├── <slug-A>/              # เช่น 'ติดหนี้สามสิบล้าน'
    ├── <slug-B>/              # หรือ 1, 2, 3, ...
    └── ...
```

**หมายเหตุ migration:**
- ชื่อเก่า `workspaces/` (พหูพจน์ของ workspace) → ย้ายเป็น `projects/` อัตโนมัติตอน startup
- ชื่อโฟลเดอร์ย่อยเก่า (`0-input`, `1-fix`, …) → rename เป็น PascalCase (`Input`, `Fix`, …) อัตโนมัติ

---

## 2) โครงหนึ่งโปรเจกต์ (`workspace/` หรือ `projects/<slug>/`)

ทุกโฟลเดอร์ย่อยถูก scaffold อัตโนมัติตอนเปิดแอป (ผ่าน `paths.ensure_dirs()`)

```text
<project_root>/
├── Raw/                       # ต้นฉบับจีน (สำหรับ Smart Matching หาบรรทัดที่ AI ข้ามแปล)
├── Input/                     # ดราฟแปลที่มี [A]/[B] interleave (เข้าสู่ขั้นตรวจ)
├── Fix/                       # ผลหลังแก้ไข error
├── Clean/                     # เกลา + ทำสะอาด (รวม .txt / .md / .docx)
├── Finish/                    # ฉบับเผยแพร่ (จบรอบแล้ว)
├── Merge/                     # ไฟล์ที่รวมหลายตอน
├── Separate/                  # ไฟล์ที่แยกตอน
├── Import/                    # user-supplied corrections (วาง chunks ที่แก้แล้ว)
│   └── import_errors.txt      # สำเนาของ Output/error_trans.txt — แก้ในนี้แทน chunks ก็ได้
├── Output/                    # ผลลัพธ์ระบบ (error_trans.txt + chunks, vocab.txt)
├── Vocab/                     # คำศัพท์ของเรื่องนี้
├── Style/                     # บันทึกสำนวน (เช่น style-notes.txt)
├── Prompt/                    # prompt templates (เช่น fix.md)
├── Temp/                      # archive รอบเก่า
└── Error/
    └── error_trans/           # ข้อความที่แยกไปแปลแก้
```

---

## 3) แมปโฟลเดอร์ ↔ ขั้นตอน / แท็บ

| โฟลเดอร์ | บทบาทหลัก |
|---|---|
| `Raw` | ไฟล์จีนต้นฉบับ — ใช้ใน Manuscript scan + Missing translation matching |
| `Input` | ดราฟแปลที่ AI ส่งมา (มี `[A]/[B]`) — เข้าสู่แท็บ "ตรวจสอบและแก้ไข" |
| `Fix` | ไฟล์หลัง apply correction จาก Import |
| `Clean` | ผ่าน clean step — ตัด `[A]`, vocab section ออก เหลือเฉพาะคำแปล |
| `Finish` | ฉบับเผยแพร่ ปิดรอบ |
| `Merge` / `Separate` | รวม / แยกตอน |
| `Output` | ผลลัพธ์ระบบ — `error_trans.txt`, `error_trans_001.txt`, `vocab.txt` |
| `Import` | user-supplied corrections + `import_errors.txt` — อ่านก่อน `Output` ตอน import |
| `Vocab` | คำศัพท์เรื่องนี้ (vocab.txt) |
| `Style` | สำนวน/style notes ที่อยากให้ AI ใช้ |
| `Prompt` | prompt templates (fix.md ฯลฯ) |
| `Temp` | archive รอบที่ปิดแล้ว |
| `Error/error_trans` | ข้อความที่แยกออกไปแปลใหม่ |

---

## 4) Flow การตรวจและแก้ไข

```
Raw  -> Input  ->  ตรวจ  ->  Output/error_trans.txt + chunks
                                    |
                                   AI แก้
                                    |
                                Import/  -> นำเข้า ->  Fix/
                                                          |
                                                       Clean/
                                                          |
                                                       Finish/
```

---

## 5) ความสัมพันธ์กับโค้ด

| ส่วน | ไฟล์ |
|---|---|
| Path resolver (multi-project) | `modules/paths.py` |
| Registry + create/rename/delete project | `modules/project_manager.py` |
| Migration (workspaces/ → projects/, lowercase → PascalCase) | `modules/project_manager._migrate_legacy_subdir_names` |
| Scaffold standard subdirs | `paths.ensure_dirs()` (ดูที่ `_DATA_DIR_KEYS_UNIQUE`) |

ถ้าแก้โครงโฟลเดอร์ใน `_SUBDIR_NAMES` **ควรอัปเดตเอกสารนี้** ให้ตรงกัน
