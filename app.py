import os
import json
import requests
import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from docxtpl import DocxTemplate
from parsers import extract_text_from_file

app = FastAPI(title="SHTP-IC Proposal AI Engine Backend")

# Cho phép CORS cho frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.environ.get("MODEL_NAME", "qwen2.5:7b")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/", response_class=HTMLResponse)
def read_index():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>SHTP-IC Proposal AI Engine Server Running</h1>"

@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """
    Endpoint nhận danh sách các file thô và trích xuất toàn bộ text sạch.
    """
    all_texts = []
    file_summary = []

    for file in files:
        content = await file.read()
        extracted = extract_text_from_file(content, file.filename)
        all_texts.append(f"=== TÀI LIỆU: {file.filename} ===\n{extracted}")
        file_summary.append({"filename": file.filename, "size": len(content), "char_count": len(extracted)})

    combined_text = "\n\n".join(all_texts)
    return {
        "status": "success",
        "files": file_summary,
        "raw_text": combined_text[:30000] # Giới hạn ngữ cảnh 30k kí tự cho Ollama
    }

@app.post("/api/generate")
async def generate_proposal(raw_text: str = Form(...)):
    """
    Endpoint kết nối với Ollama Local AI (Qwen 2.5) để trích xuất & dự thảo theo JSON format.
    """
    prompt = f"""
Bạn là chuyên gia thẩm định dự án công nghệ cao SHTP-IC. Hãy đọc DỮ LIỆU THÔ bên dưới và trích xuất/dự thảo các nội dung chi tiết theo định dạng JSON duy nhất.

DỮ LIỆU THÔ:
---
{raw_text}
---

Yêu cầu trả về duy nhất định dạng JSON chuẩn (không giải thích thêm):
{{
  "ten_du_an": "Tên dự án đầy đủ...",
  "san_pham_chinh": "Tên các sản phẩm/dịch vụ chính...",
  "cong_nghe_chinh": "Các công nghệ cốt lõi...",
  "linh_vuc": "Lĩnh vực đăng ký...",
  "van_de_giai_phap": "Vấn đề và giải pháp chi tiết...",
  "tinh_cap_thiet": "Tính cấp thiết...",
  "muc_tieu_ktxh": "Mục tiêu kinh tế xã hội...",
  "muc_tieu_khcn": "Mục tiêu khoa học công nghệ...",
  "minh_chung_san_pham": "Giải trình thông số kỹ thuật...",
  "quy_trinh_san_pham": "Cấu phần & Lưu đồ hoạt động...",
  "tinh_nang_vuot_troi": "Chất lượng & Thay thế nhập khẩu...",
  "minh_chung_cong_nghe": "Hiện trạng ứng dụng công nghệ...",
  "quy_trinh_cong_nghe": "Các bước quy trình kỹ thuật...",
  "tinh_kha_thi_ky_thuat": "Đánh giá tính khả thi...",
  "bao_mat_mo_rong": "Bảo mật & Tính mở rộng...",
  "tiem_nang_thi_truong": "Tình hình thị trường & Dự báo nhu cầu...",
  "doi_thu_1": "Đối thủ ngoại: Tên, Giá, Điểm mạnh/yếu...",
  "doi_thu_2": "Đối thủ nội: Tên, Giá, Điểm mạnh/yếu...",
  "loi_the_canh_tranh": "Các lợi thế cạnh tranh cốt lõi..."
}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )
        if response.status_code == 200:
            res_json = response.json()
            ai_output = json.loads(res_json.get("response", "{}"))
            return {"status": "success", "data": ai_output}
        else:
            raise HTTPException(status_code=500, detail=f"Lỗi kết nối Ollama: {response.text}")
    except Exception as e:
        # Trả về fallback dữ liệu nếu Ollama chưa chạy
        return {
            "status": "warning",
            "message": f"Không kết nối được Ollama tại {OLLAMA_URL} ({str(e)}). Trả về dữ liệu mẫu.",
            "data": {
                "ten_du_an": "Hệ thống Tự động hóa Giám sát và Cảnh báo Sớm trong Nông nghiệp Công nghệ cao ứng dụng IoT và AI",
                "san_pham_chinh": "Thiết bị cảm biến SmartAgri Gateway & Nền tảng SaaS Quản trị Nông trại",
                "cong_nghe_chinh": "Công nghệ Mạng cảm biến không dây (WSN), Trí tuệ nhân tạo (AI/Computer Vision)",
                "linh_vuc": "Công nghiệp điện tử, vi mạch bán dẫn & Công nghệ IoT",
                "van_de_giai_phap": "Dự án cung cấp giải pháp tích hợp các đầu đo IoT thu thập dữ liệu thời gian thực...",
                "tinh_cap_thiet": "Xu hướng chuyển đổi số nông nghiệp tại TP.HCM và cả nước đòi hỏi giải pháp Việt hóa...",
                "minh_chung_san_pham": "Gateway đạt chuẩn IP67, tích hợp 8 kênh cảm biến RS485 độ chính xác 98.5%...",
                "quy_trinh_san_pham": "Sensor Node -> Gateway IoT Edge -> Cloud MQTT -> AI Engine -> Relay Controller -> Web/App...",
                "tinh_nang_vuot_troi": "Tích hợp AI chẩn đoán sâu bệnh Việt hóa trực tiếp tại vi mạch. Giá rẻ hơn 60%...",
                "minh_chung_cong_nghe": "Công nghệ ứng dụng mạng cuộn CNN (YOLOv8 & MobileNetV3) xử lý hình ảnh thời gian thực...",
                "quy_trinh_cong_nghe": "Bước 1: Thu thập ảnh; Bước 2: Chuẩn hóa; Bước 3: AI Edge suy luận; Bước 4: Khuyến nghị...",
                "tinh_kha_thi_ky_thuat": "Giải quyết triệt để nỗi đau phát hiện sâu bệnh muộn của nông dân...",
                "bao_mat_mo_rong": "Bảo mật chuẩn TLS 1.3/AES-256; Kiến trúc Docker Microservices mở rộng 50,000 kết nối...",
                "tiem_nang_thi_truong": "Thị trường nông nghiệp thông minh Việt Nam ước tính đạt 500 triệu USD...",
                "doi_thu_1": "Netafim (Israel) | Giá 20,000 USD | Điểm yếu: Giá đắt, không có AI nông nghiệp Việt",
                "doi_thu_2": "NextFarm (VN) | Giá 100 triệu VNĐ | Điểm yếu: Chưa có AI chẩn đoán bệnh tại thiết bị",
                "loi_the_canh_tranh": "Công nghệ AI Edge Computing nhận diện sâu bệnh độc quyền Việt hóa."
            }
        }

@app.post("/api/export-word")
async def export_word(payload: dict):
    """
    Endpoint nhận dữ liệu từ UI và render ra file Word .docx hoàn chỉnh.
    """
    template_path = os.path.join(BASE_DIR, "template_shtpic.docx")
    if not os.path.exists(template_path):
        from word_engine import create_shtpic_template
        create_shtpic_template(template_path)

    doc = DocxTemplate(template_path)
    doc.render(payload)

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=Thuyet_Minh_Du_An_SHTPIC_Final.docx"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8086, reload=True)
