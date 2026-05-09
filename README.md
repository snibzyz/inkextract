# INKEXTRACT

เครื่องมือจัดการนิยายแปลแบบครบวงจร — ตรวจ คัด รวม แยก คำศัพท์ พร้อมระบบหลายโปรเจกต์
ใช้งานง่ายผ่านเบราว์เซอร์

---

## ติดตั้งเร็ว — แค่กดรัน

ไม่ต้องลง Python, ไม่ต้องลง pip, ไม่ต้องสร้าง venv — bundle มาให้พร้อมแล้ว

### Windows

1. ดาวน์โหลด → [Releases ล่าสุด](https://github.com/snibzyz/inkextract/releases/latest) → `INKEXTRACT-windows-x64.zip`
2. คลิกขวา zip → **Extract All...** (อย่าใช้ "Open" เปิด zip เฉย ๆ)
3. เข้าโฟลเดอร์ที่แตก → ดับเบิลคลิก `Start.bat`
   - ถ้า SmartScreen เตือน → กด **More info** → **Run anyway** (เกิดกับ unsigned app ทั่วไป)
4. เบราว์เซอร์เปิดอัตโนมัติ

### macOS

1. ดาวน์โหลด → [Releases ล่าสุด](https://github.com/snibzyz/inkextract/releases/latest)
   - **Apple Silicon (M1/M2/M3/M4)** → `INKEXTRACT-macos-arm64.zip`
   - **Intel Mac** → `INKEXTRACT-macos-x64.zip`
2. ดับเบิลคลิก zip เพื่อแตกไฟล์ (Finder ทำให้อัตโนมัติ)
3. เข้าโฟลเดอร์ → **คลิกขวาที่ `Start.command` → Open → Open** (ครั้งแรกเท่านั้น)
4. เบราว์เซอร์เปิดอัตโนมัติ

> **Auto-update**: โปรแกรมเช็ค GitHub releases ทุกครั้งที่เปิด — ถ้ามีเวอร์ชันใหม่ banner จะขึ้นด้านบน → กด **Update now** → รีสตาร์ท Start = ใช้ตัวใหม่
>
> **อยากแก้โค้ดเอง?** → ดู [Developer setup](#developer-setup) ด้านล่าง

---

### โหลด "Source code (zip)" มาแทน?

ถ้าเผลอโหลด `Source code (zip)` จากหน้า Releases (zip ที่ GitHub gen ให้อัตโนมัติ) แทนที่จะเป็น `INKEXTRACT-windows-x64.zip` — zip ตัวนี้ **ไม่มี Python มาให้** ต้องติดตั้งครั้งเดียวก่อน:

| OS | ขั้นตอน |
|---|---|
| Windows | ติดตั้ง Python จาก [python.org](https://www.python.org/downloads/windows/) (ติ๊ก `Add Python to PATH`) → ดับเบิลคลิก **`Install.bat`** → รอ 1-3 นาที → ดับเบิลคลิก `Start.bat` |
| macOS | ติดตั้ง Python จาก [python.org](https://www.python.org/downloads/macos/) → คลิกขวา **`Install.command`** → Open → Open → รอ 1-3 นาที → ดับเบิลคลิก `Start.command` |

หรือกลับไปโหลด pre-built bundle ที่ถูกต้อง — ไม่ต้องลง Python, ไม่ต้องรัน Install

---

## ฟีเจอร์หลัก

| Tab | ใช้ทำอะไร |
|---|---|
| **โปรเจกต์** | สลับ/สร้าง/ลบโปรเจกต์ — แต่ละโปรเจกต์มีโฟลเดอร์ย่อยของตัวเอง ไม่ปนกัน |
| **ตรวจต้นฉบับ** | สแกนไฟล์ raw จีน — เน้นไฟล์ที่เล็กผิดปกติ + เรียงเลขใหม่ + พรีวิวแบบ VS Code |
| **คำศัพท์** | จัดการ vocab — ตัดซ้ำ หาคำขัดแย้ง กรองความถี่ เรียงตามต่าง ๆ |
| **ตรวจสอบและแก้ไข** | หาข้อผิดพลาดในไฟล์แปล + ตรวจหาบรรทัดที่ AI ข้ามแปล + ส่งออก/นำเข้าเพื่อแก้ |
| **จัดการไฟล์** | รวม / แยก / สร้าง / แปลง (TXT/MD/DOCX) / ตรวจรูปแบบ / ลบ |

---

## ระบบหลายโปรเจกต์

แต่ละเรื่องที่ทำ = 1 โปรเจกต์ ไม่ปนกับเรื่องอื่น

```
INKEXTRACT/
├── workspace/                ← โปรเจกต์เริ่มต้น (ใช้ได้เลย ลบไม่ได้)
│   ├── 0-input/, 1-fix/, ...
│
├── projects/                 ← โปรเจกต์ที่ผู้ใช้สร้างเพิ่ม
│   ├── ติดหนี้สามสิบล้าน/
│   │   ├── 0-input/, 1-fix/, ...
│   └── นิยายอีกเรื่อง/
│       ├── ...
│
└── .config/
    ├── projects.json         ← registry รายชื่อโปรเจกต์ + active
    └── app.log
```

**สลับโปรเจกต์**: แท็บ **"โปรเจกต์"** → กด "สลับไป" ที่โปรเจกต์ที่ต้องการ
**สร้างใหม่**: แท็บ **"โปรเจกต์"** → กรอกชื่อ → กด "สร้างและสลับไปใช้งาน"

---

## โครงสร้างโฟลเดอร์ในแต่ละโปรเจกต์ (INKIDEA-style PascalCase)

```
<project_root>/
├── Raw/            ← วางไฟล์ raw จีนต้นฉบับ (.txt) สำหรับเทียบหาบรรทัดที่ AI ข้ามแปล
├── Input/          ← วางไฟล์แปลตั้งต้น (.txt มี [A]/[B] interleave)
├── Fix/            ← ไฟล์ที่แก้ไขแล้ว (auto-fill)
├── Clean/          ← ไฟล์สะอาด (auto-fill — รวม .txt/.md/.docx)
├── Finish/         ← ฉบับเผยแพร่ (จบรอบแล้ว)
├── Merge/          ← ไฟล์รวมหลายตอน (auto-fill)
├── Separate/       ← ไฟล์แยกตอน (auto-fill)
├── Import/         ← วางไฟล์ที่แก้แล้วกลับมาที่นี่ก่อน Import
│   └── import_errors.txt   ← สำเนาของ Output/error_trans.txt — แก้ในนี้ได้เลย
├── Output/         ← ผลลัพธ์ต่าง ๆ (error_trans.txt, vocab.txt)
├── Vocab/          ← วางไฟล์คำศัพท์ที่นี่
├── Style/          ← บันทึกสำนวน (style-notes.txt)
├── Prompt/         ← prompt templates (fix.md ฯลฯ)
├── Temp/           ← archive รอบเก่า
└── Error/
    └── error_trans/   ← ข้อความที่แยกไปแปลแก้
```

> **Migration อัตโนมัติ**: โปรเจกต์เก่าที่ใช้ `0-input/`, `1-fix/`, `2-clean/`, … (lowercase numbered) จะถูก rename เป็น PascalCase ตอนเปิดแอปครั้งแรกหลังอัปเดต ไม่ต้องทำเอง

ดูเอกสารโครงโฟลเดอร์เต็มได้ที่ [`.app/templates/inkextract-layout/README.md`](.app/templates/inkextract-layout/README.md)

---

## Workflow ตรวจและแก้ไข (โหมด AB)

```
  วางไฟล์แปล (มี [A]/[B]) ใน 0-input/
              ↓
  วางไฟล์ raw จีน ใน 0-input-raw/  (option — ไว้หาบรรทัดที่ AI ข้ามแปล)
              ↓
  แท็บ "ตรวจสอบและแก้ไข" → เริ่มวิเคราะห์
              ↓
  พบข้อผิดพลาด → ส่งออก
              ↓
  สร้าง output/error_trans.txt (master) + chunks (~500 บรรทัด/ไฟล์)
  สร้าง 5-import/import_errors.txt (สำเนา — แก้ในนี้ก็ได้)
              ↓
  ส่งให้ AI แก้บรรทัด [B] → วางผลลัพธ์ใน 5-import/
              ↓
  กด "นำเข้าการแก้ไข"
  (มี slider ปรับ fuzzy threshold — default 0.95 แม่นมาก)
              ↓
  กด "แก้ไขไฟล์" → 1-fix/ พร้อมไฟล์ที่แก้แล้ว
              ↓
  กด "ทำความสะอาดไฟล์" → 2-clean/ พร้อมส่งใช้งาน
```

### ตรวจหาบรรทัดที่ AI ข้ามแปล (Smart Matching)

วาง raw จีนใน `0-input-raw/` (ชื่อไฟล์ตรง/ใกล้กับ `0-input/`) → ติ๊ก **"ตรวจหาบรรทัดที่ AI ข้ามแปล"** ตอนวิเคราะห์ → ระบบใช้ bigram similarity จับคู่บรรทัดต้นฉบับกับ `[A]` ในไฟล์แปล หาบรรทัดที่ AI ข้ามไม่ได้แปล แล้วเพิ่มเข้า `error_trans.txt` ในกลุ่ม **"กรณี B — แปลไม่ครบ"** พร้อม `[B]` ว่างให้กรอก

### Smart Split (~500 บรรทัด/chunk)

ตอนกด **"ส่งออกเพื่อแก้ไข"** ตั้ง `chunk_lines` ได้ ระบบแบ่ง `error_trans_001.txt`, `_002.txt`, … โดย:

- **ห้ามตัดกลาง entry** — chunk จบที่ entry boundary เสมอ
- **Repeat headers** ในทุก chunk ใหม่ (section + ชื่อไฟล์ + part กำกับ X/Y)
- **master เก็บไว้เสมอ** — `error_trans.txt` ฉบับเต็มอยู่ใน `output/` ตลอด

---

## Logo & Branding

โลโก้ของ INKEXTRACT (`inkideaex.png`) อยู่ใน `.app/` — ติดมากับ source code
แสดงเป็น page icon ของ browser tab + ในแถบ header ของแอปอัตโนมัติ

---

## อัปเดต

### Auto-update (อัตโนมัติ)

แอปจะเช็ค GitHub Releases ทุกครั้งที่เปิด — ถ้ามีเวอร์ชันใหม่:

1. มี **banner สีส้ม** ขึ้นด้านบน บอกเวอร์ชันใหม่
2. กด **"Update now"** → ดาวน์โหลด zip ใหม่ → unstage ไว้ใน `.update_pending/`
3. ปิด-เปิดแอปอีกครั้ง (`Start.bat` / `Start.command`) → launcher จะ apply update ก่อนเปิดแอป
4. เสร็จแล้วใช้เวอร์ชันใหม่ทันที

**ทำไม apply ใน launcher ไม่ใช่ใน Python?**
Windows ล็อกไฟล์ `python.exe` ขณะรัน — ถ้าจะแทนที่ตัวเองตอนรันอยู่จะ fail launcher ใช้ `robocopy` (Windows) / `rsync` (macOS) ก่อน Python เริ่มรัน เลยปลอดภัย

### สิ่งที่ "ไม่ถูกแตะ" ตอนอัปเดต

ข้อมูลส่วนตัวคุณจะอยู่ครบเสมอ:

- `workspace/` (โปรเจกต์เริ่มต้น) + ไฟล์ทุกตัวข้างใน
- `projects/<slug>/` (โปรเจกต์ที่สร้างเพิ่ม) + ไฟล์ทุกตัวข้างใน
- `.config/` (settings, exclude, projects.json, app.log)
- `.venv/` (สำหรับ dev) — ไม่ถูกแตะ
- `Start.bat`, `Start.command` — ไม่ถูกแตะ (เพื่อความปลอดภัยตอนรัน)

### อัปเดตด้วยมือ (Manual)

ถ้า auto-update ไม่ทำงาน หรืออยากย้อนเวอร์ชัน:

1. ดาวน์โหลด zip ของเวอร์ชันที่ต้องการจาก [Releases](https://github.com/snibzyz/inkextract/releases)
2. แตก zip ทับโฟลเดอร์เดิม — workspace/, projects/, .config/ จะคงไว้ (อยู่ในโฟลเดอร์เดียวกันกับ zip ที่แตกใหม่)
3. เปิด `Start.bat` / `Start.command` ใช้งานต่อ

### กรณี Source-zip + Install

ถ้าใช้ "Source code (zip)" ของ GitHub (ไม่มี Python bundle):

- หลัง apply update เสร็จ launcher จะ **refresh dependencies** อัตโนมัติ (`pip install -r .app/requirements.txt`)
- ถ้า requirements เปลี่ยน — pip จะติดตั้งของใหม่ครั้งเดียว
- ถ้าไม่เปลี่ยน — pip ตรวจแล้วผ่านในวินาทีเดียว

### Migration อัตโนมัติ

โปรเจกต์เก่าที่เคยอยู่ใน `workspaces/` (พหูพจน์) จะถูก migrate → `projects/` ตอนเปิดแอปครั้งหน้าโดยอัตโนมัติ พร้อมอัพเดต path ใน registry — ไม่ต้องทำเอง

### ตรวจเวอร์ชันปัจจุบัน

อ่านไฟล์ `.app/VERSION` (เช่น `1.0.6`)

---

## แก้ปัญหา

| ปัญหา | แก้ยังไง |
|---|---|
| เปิดโปรแกรมแล้วไม่มีอะไรขึ้น | รอ 10-20 วินาที เบราว์เซอร์จะเปิดเอง |
| Windows: SmartScreen เตือน | กด **More info** → **Run anyway** (เกิดกับ unsigned app ทั่วไป) |
| Mac: บอกว่าเปิดไม่ได้ / damaged | คลิกขวาที่ `Start.command` → Open → Open (ครั้งแรกเท่านั้น) |
| Auto-update ไม่ทำงาน | เช็คว่าเครื่องต่ออินเทอร์เน็ตอยู่ และไม่ถูก firewall บล็อก github.com |
| โปรเจกต์เก่าอยู่ใน `workspaces/` | ระบบ migrate ให้อัตโนมัติตอนเปิดแอปครั้งหน้า → `projects/` พร้อมอัพเดต registry |
| Import กลับมาแล้ว match ไม่เจอ | ปรับ Fuzzy threshold ใน slider ให้ต่ำลง (เช่น 0.85) — ระวัง false match |
| อยากย้อนเวอร์ชัน | ดาวน์โหลด zip ของเวอร์ชันที่ต้องการจาก [Releases](https://github.com/snibzyz/inkextract/releases) → ทับโฟลเดอร์เดิม |

---

## Developer setup

Launcher ตัวเดียว (`Start.bat` / `Start.command`) ใช้ได้ทั้ง dev และ user — ฉลาดพอจะตรวจ environment เอง:

```
1. มี python/        ?  → ใช้ตัวที่ bundle มาให้  (โหมด end-user)
2. มี .venv/         ?  → ใช้ venv                (โหมด dev)
3. fallback          →  ใช้ system Python + เตือน
```

ขั้นตอนตั้งครั้งแรก (dev clone source):

> **หมายเหตุชื่อโฟลเดอร์**: ใช้ `INKEXTRACT` ตัวพิมพ์ใหญ่เป็นชื่อโฟลเดอร์ — ตรงกับชื่อในเอกสาร, path ต่าง ๆ และโครงสร้าง git history (ของแถม `git clone <url> INKEXTRACT` ทำให้ตรงทันที)

### Windows
```powershell
git clone https://github.com/snibzyz/inkextract INKEXTRACT
cd INKEXTRACT
python -m venv .venv
.venv\Scripts\pip install -r .app\requirements.txt
REM จากนี้กด Start.bat รันได้เลย เหมือน user
```

### macOS / Linux
```bash
git clone https://github.com/snibzyz/inkextract INKEXTRACT
cd INKEXTRACT
python3 -m venv .venv
.venv/bin/pip install -r .app/requirements.txt
# จากนี้ Start.command รันได้เลย เหมือน user
```

### โครงสร้างโค้ด

```
.app/
├── app.py                    ← entry point (Streamlit)
├── inkideaex.png             ← logo (ติดมากับ source)
├── modules/
│   ├── paths.py              ← path resolver (multi-project aware)
│   ├── project_manager.py    ← ระบบหลายโปรเจกต์
│   ├── proofreader.py        ← วิเคราะห์ + export/import error_trans
│   ├── error_chunker.py      ← split chunks ตามจำนวนบรรทัด
│   ├── fuzzy_matcher.py      ← bigram similarity สำหรับ import match
│   ├── missing_line_detector.py  ← หาบรรทัดที่ AI ข้ามแปล
│   ├── raw_file_resolver.py  ← จับคู่ไฟล์แปลกับ raw (รองรับช่วงเลขตอน)
│   └── tabs/
│       ├── project.py        ← UI จัดการโปรเจกต์
│       ├── manuscript.py     ← UI ตรวจต้นฉบับ
│       ├── proof.py          ← UI ตรวจสอบและแก้ไข
│       └── ...
└── tests/                    ← unit tests
```

ดูแนวทางและกฎประจำโปรเจกต์เพิ่มเติมที่ [`.claude/CLAUDE.md`](.claude/CLAUDE.md)

---

## การตั้งค่าขั้นสูง

ไฟล์ตั้งค่าอยู่ในโฟลเดอร์ **`.config/`** (ซ่อน) — shared ทุกโปรเจกต์

| ไฟล์ | หน้าที่ |
|---|---|
| `exclude.txt` | อักขระ/pattern ที่ไม่ต้องการให้นับเป็นข้อผิดพลาด (รองรับ regex) |
| `settings.json` | ตั้งค่าทั่วไปของแอป |
| `user_preferences.json` | ค่าที่จำตอนใช้งาน UI (chunk_lines, fuzzy threshold, ...) |
| `projects.json` | registry รายชื่อโปรเจกต์ + active project |
| `app.log` | log การทำงานของแอป |

แก้ผ่าน UI ได้เลย — ที่แท็บ "ตรวจสอบและแก้ไข" → ขยาย "การตั้งค่ารูปแบบยกเว้น"

> **Mac**: โฟลเดอร์ที่ขึ้นต้นด้วย `.` ถูกซ่อน — กด **Cmd+Shift+.** เพื่อแสดง

---

## ข้อกำหนดระบบ

- Windows 10/11 (x64) — bundle รวม Python มาแล้ว ไม่ต้องลงเอง
- macOS 11+ (Apple Silicon หรือ Intel) — bundle รวม Python มาแล้ว ไม่ต้องลงเอง
- อินเทอร์เน็ต (ตอนตรวจ update เท่านั้น — ใช้งานออฟไลน์ได้)
- (Dev only) Python 3.10+ ถ้ารันจาก source

---

## License

MIT — ใช้ได้เสรี
