# 🟠 INKEXTRACT

เครื่องมือจัดการนิยายแปลแบบครบวงจร — ตรวจ • คัด • รวม • แยก • คำศัพท์
ใช้งานง่ายผ่านเบราว์เซอร์

---

## ⚡ ติดตั้งเร็ว — แค่กดรัน

ไม่ต้องลง Python, ไม่ต้องลง pip, ไม่ต้องสร้าง venv — bundle มาให้พร้อมแล้ว

### 🪟 Windows

1. ดาวน์โหลด → [Releases ล่าสุด](https://github.com/snibzyz/inkextract/releases/latest) → `INKEXTRACT-windows-x64.zip`
2. คลิกขวา zip → **Extract All...** (อย่าใช้ "Open" เปิด zip เฉย ๆ)
3. เข้าโฟลเดอร์ที่แตก → ดับเบิลคลิก `Start.bat`
   - ถ้า SmartScreen เตือน → กด **More info** → **Run anyway** (เกิดกับ unsigned app ทั่วไป)
4. เบราว์เซอร์เปิดอัตโนมัติ ✓

### 🍎 macOS

1. ดาวน์โหลด → [Releases ล่าสุด](https://github.com/snibzyz/inkextract/releases/latest)
   - **Apple Silicon (M1/M2/M3/M4)** → `INKEXTRACT-macos-arm64.zip`
   - **Intel Mac** → `INKEXTRACT-macos-x64.zip`
2. ดับเบิลคลิก zip เพื่อแตกไฟล์ (Finder ทำให้อัตโนมัติ)
3. เข้าโฟลเดอร์ → **คลิกขวาที่ `Start.command` → Open → Open** (ครั้งแรกเท่านั้น)
4. เบราว์เซอร์เปิดอัตโนมัติ ✓

> 🔄 **Auto-update**: โปรแกรมเช็ค GitHub releases ทุกครั้งที่เปิด — ถ้ามีเวอร์ชันใหม่ → banner ขึ้นด้านบน → กด **Update now** → รีสตาร์ท Start = ใช้ตัวใหม่
>
> 🛠️ **อยากแก้โค้ดเอง?** → ดู [Developer setup](#-developer-setup-สำหรับคนที่อยากแก้โค้ด) ด้านล่าง

---

### 🟡 โหลด "Source code (zip)" มาแทน?

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
| 📋 **ตรวจต้นฉบับ** | สแกนไฟล์ในโฟลเดอร์ — เน้นไฟล์ที่เล็กผิดปกติ + เรียงเลขใหม่ |
| 📖 **คำศัพท์** | จัดการ vocab — ตัดซ้ำ / หาคำขัดแย้ง / กรองความถี่ / เรียงตามต่าง ๆ |
| ✓ **ตรวจสอบและแก้ไข** | หาตัวอักษรต่างประเทศ / อังกฤษ / ตัวเลขในไฟล์แปล (มี 3 โหมด) |
| 📁 **จัดการไฟล์** | รวม / แยก / สร้าง / แปลง (TXT↔MD↔DOCX) / ตรวจรูปแบบ / ลบ |

---

## วางไฟล์ที่ไหน

ทุกอย่างอยู่ในโฟลเดอร์ **`workspace/`**

```
workspace/
├── 0-input/        ← วางไฟล์ต้นฉบับที่นี่ (.txt)
├── 1-fix/          ← ไฟล์ที่แก้ไขแล้ว (auto-fill)
├── 2-clean/        ← ไฟล์สะอาด (auto-fill)
├── 3-merge/        ← ไฟล์รวมหลายตอน (auto-fill)
├── 4-separate/     ← ไฟล์แยกตอน (auto-fill)
├── output/         ← ผลลัพธ์ต่าง ๆ
└── vocab/          ← วางไฟล์คำศัพท์ที่นี่
```

---

## แก้ปัญหา

| ปัญหา | แก้ยังไง |
|---|---|
| เปิดโปรแกรมแล้วไม่มีอะไรขึ้น | รอ 10-20 วินาที เบราว์เซอร์จะเปิดเอง |
| Win: SmartScreen เตือน | กด **More info** → **Run anyway** (เกิดกับ unsigned app ทั่วไป) |
| Mac: บอกว่าเปิดไม่ได้ / damaged | คลิกขวาที่ `Start.command` → Open → Open (ครั้งแรกเท่านั้น) |
| Auto-update ไม่ทำงาน | เช็คว่าเครื่องต่ออินเทอร์เน็ตอยู่ และไม่ถูก firewall บล็อก github.com |
| อยากย้อนเวอร์ชัน | ดาวน์โหลด zip ของเวอร์ชันที่ต้องการจาก [Releases](https://github.com/snibzyz/inkextract/releases) → ทับโฟลเดอร์เดิม |

---

## 🛠️ Developer setup (สำหรับคนที่อยากแก้โค้ด)

Launcher ตัวเดียว (`Start.bat` / `Start.command`) ใช้ได้ทั้ง dev และ user — ฉลาดพอจะตรวจ environment เอง:

```
1. มี python/        ?  → ใช้ตัวที่ bundle มาให้  (โหมด end-user)
2. มี .venv/         ?  → ใช้ venv                (โหมด dev)
3. fallback          →  ใช้ system Python + เตือน
```

ขั้นตอนตั้งครั้งแรก (dev clone source):

### Windows
```powershell
git clone https://github.com/snibzyz/inkextract
cd inkextract
python -m venv .venv
.venv\Scripts\pip install -r .app\requirements.txt
# จากนี้กด Start.bat รันได้เลย เหมือน user
```

### macOS / Linux
```bash
git clone https://github.com/snibzyz/inkextract
cd inkextract
python3 -m venv .venv
.venv/bin/pip install -r .app/requirements.txt
# จากนี้ Start.command รันได้เลย เหมือน user
```

---

## การตั้งค่าขั้นสูง

ไฟล์ตั้งค่าอยู่ในโฟลเดอร์ **`.config/`** (ซ่อน)

| ไฟล์ | หน้าที่ |
|---|---|
| `exclude.txt` | อักขระ/pattern ที่ไม่ต้องการให้นับเป็นข้อผิดพลาด (รองรับ regex) |

แก้ผ่าน UI ได้เลย — ที่ tab `ตรวจสอบและแก้ไข` → ขยาย "การตั้งค่ารูปแบบยกเว้น"

> 🍎 **Mac**: โฟลเดอร์ที่ขึ้นต้นด้วย `.` ถูกซ่อน — กด **Cmd+Shift+.** เพื่อแสดง

---

## ข้อกำหนดระบบ

- Windows 10/11 (x64) — bundle รวม Python มาแล้ว ไม่ต้องลงเอง
- macOS 11+ (Apple Silicon หรือ Intel) — bundle รวม Python มาแล้ว ไม่ต้องลงเอง
- อินเทอร์เน็ต (ตอนตรวจ update เท่านั้น — ใช้งานออฟไลน์ได้)
- (Dev only) Python 3.10+ ถ้ารันจาก source

---

## License

MIT — ใช้ได้เสรี
