"""streamlit_compat — กันหน้าเว็บค้าง "Stop" ถาวรบน Streamlit ที่ใช้เซิร์ฟเวอร์ Starlette (1.5x+)

เคสจริง (25-10-2026 · v1.12.4 · bundle มี Streamlit 1.63.0): โปรเจกต์ที่ Raw มีหลายพันตอน
เปิดแอปแล้วหน้าเว็บขึ้น "Stop" ค้าง ทุกอย่างจาง กดอะไรไม่ได้ (console มีแค่ ConnectionResetError ตอนปิดแท็บ)

ต้นเหตุ: Streamlit (Starlette) จำกัดคิวส่งข้อความต่อ browser ไว้ 500 ข้อความ
(`starlette_server_config.WEBSOCKET_MAX_SEND_QUEUE_SIZE`) — rerun เดียวที่สร้าง element หลายพันชิ้น
เร็วกว่าที่ browser อ่านทัน → คิวเต็ม → เซิร์ฟเวอร์ถือว่า client หลุดแล้วเลิกส่งเงียบ ๆ
แต่ไม่ปิด WebSocket ฝั่ง browser → browser รอข้อความ "รันเสร็จ" ตลอดไป
(วัดจริง: Raw 2,000 ไฟล์ = คิวเต็มทุกครั้ง · ขยายคิวแล้วโหลดครบใน ~8 วิ)

INKEXTRACT เป็นแอปในเครื่องที่มีผู้ใช้คนเดียว — ข้อจำกัดนี้มีไว้กันหน่วยความจำเซิร์ฟเวอร์
ตอนมีผู้ใช้พร้อมกันจำนวนมาก จึงไม่จำเป็น → ขยายคิวของ session ปัจจุบัน + connection ถัดไป

ใช้ API ภายในของ Streamlit — ทุกขั้นห่อ try/except: เวอร์ชันที่ไม่มีของพวกนี้ = ไม่ทำอะไร
(ต้นเหตุจริงฝั่งแอป = render widget ต่อไฟล์ทุกไฟล์ — แท็บตรวจต้นฉบับแบ่งหน้าแล้ว นี่คือกันเหนียว)
"""
from __future__ import annotations

SEND_QUEUE_LIMIT = 100_000


def raise_ws_send_queue_limit(limit: int = SEND_QUEUE_LIMIT) -> bool:
    """ขยายคิวส่งข้อความของ WebSocket — คืน True ถ้าปรับได้อย่างน้อยหนึ่งจุด

    เรียกจาก app.py ทุก rerun (ถูก — แค่อ่าน/เขียนตัวแปร) ก่อน render อะไรหนัก ๆ
    """
    patched = False
    # connection ใหม่ (เช่น กด F5) — Queue อ่านค่าจาก global ของโมดูลตอนสร้าง client
    try:
        from streamlit.web.server.starlette import starlette_websocket as _ws
        if getattr(_ws, "WEBSOCKET_MAX_SEND_QUEUE_SIZE", limit) < limit:
            _ws.WEBSOCKET_MAX_SEND_QUEUE_SIZE = limit
        patched = True
    except Exception:
        pass
    # connection ปัจจุบัน — client ถูกสร้างก่อน script รัน จึงต้องขยายคิวที่มีอยู่แล้วตรง ๆ
    try:
        from streamlit.runtime import Runtime
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx(suppress_warning=True)
        if ctx is not None:
            info = Runtime.instance()._session_mgr.get_active_session_info(ctx.session_id)
            queue = getattr(getattr(info, "client", None), "_send_queue", None)
            if queue is not None and 0 < queue.maxsize < limit:
                queue._maxsize = limit
                patched = True
    except Exception:
        pass
    return patched
