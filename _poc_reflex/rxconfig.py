import reflex as rx

# Frontend/Backend ports — เลือก range ที่ไม่ชนกับ:
#   - Streamlit (8501)
#   - INK family Electron Vite (5173, 5273, ..., 5573)
#   - Reflex defaults (3000, 8000) — เคยมี orphan socket ค้าง
config = rx.Config(
    app_name="inkextract_poc",
    frontend_port=4500,
    backend_port=4501,
    tailwind=None,
    show_built_with_reflex=False,
)
