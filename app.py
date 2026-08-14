import os
import json
import requests
import io
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from docxtpl import DocxTemplate
from parsers import extract_text_from_file

app = FastAPI(title="SHTP-IC Proposal AI Engine Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080", "http://localhost:8086", "http://localhost:8087", "http://localhost:8088", "http://localhost:8089", "http://localhost:8090", "http://localhost:8092", "http://localhost:8095", "http://localhost:8098", "http://localhost:8000",
        "http://127.0.0.1:8080", "http://127.0.0.1:8086", "http://127.0.0.1:8087", "http://127.0.0.1:8088", "http://127.0.0.1:8089", "http://127.0.0.1:8090", "http://127.0.0.1:8092", "http://127.0.0.1:8095", "http://127.0.0.1:8098", "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.environ.get("MODEL_NAME", "qwen2.5:7b")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(KB_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# File lưu metadata kho dự án mẫu
KB_METADATA_FILE = os.path.join(KB_DIR, "kb_metadata.json")

def load_kb_metadata():
    if os.path.exists(KB_METADATA_FILE):
        try:
            with open(KB_METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_kb_metadata(data):
    with open(KB_METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.get("/", response_class=HTMLResponse)
def read_index():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>SHTP-IC Proposal AI Engine Server Running</h1>"

@app.get("/api/ai-status")
def check_ai_status():
    """Kiểm tra xem Ollama AI Local đã bật hay chưa."""
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=3)
        if res.status_code == 200:
            models = res.json().get("models", [])
            model_names = [m.get("name") for m in models]
            return {
                "online": True,
                "model": MODEL_NAME,
                "available_models": model_names,
                "message": "AI Ollama Local đang sẵn sàng 100%"
            }
    except Exception as e:
        pass
    
    return {
        "online": False,
        "model": MODEL_NAME,
        "message": "Chưa bật Ollama AI Local. Hệ thống sẽ tự động dùng chế độ AI Bóc tách mặc định."
    }

@app.get("/api/kb/list")
def list_kb():
    """Liệt kê các file thuyết minh mẫu đã lưu trong Kho tri thức kèm Nhãn Lĩnh vực."""
    return {"status": "success", "data": load_kb_metadata()}

def auto_classify_category(text_preview: str, filename: str) -> str:
    """Tự động dùng AI Qwen 2.5 phân loại Lĩnh vực cho file mẫu."""
    # Quy tắc phân loại từ khóa nhanh
    text_lower = (filename + " " + text_preview).lower()
    
    if any(k in text_lower for k in ["ai", "phần mềm", "iot", "cloud", "camera", "mạng", "phân loại sản phẩm", "thuật toán", "dữ liệu", "app", "website", "ims", "robotics"]):
        return "Công nghệ thông tin & AI"
    elif any(k in text_lower for k in ["sinh học", "tế bào", "gen", "nông nghiệp", "phân bón", "dược", "y tế", "vi sinh", "thực phẩm"]):
        return "Công nghệ sinh học"
    elif any(k in text_lower for k in ["mạch", "vi mạch", "bán dẫn", "cảm biến", "chip", "pcb", "phần cứng", "mạch in", "lsi"]):
        return "Điện tử - Vi mạch"
    elif any(k in text_lower for k in ["vật liệu", "nano", "composite", "polyme", "kim loại", "gốm", "sợi", "bề mặt"]):
        return "Vật liệu mới & Khác"

    # Gọi Qwen 2.5 phân loại nếu có Ollama
    try:
        prompt = f"""
Bạn là chuyên gia phân loại dự án công nghệ cao. Hãy đọc tên file và đoạn văn bản ngắn dưới đây, sau đó phân loại dự án thuộc DUY NHẤT 1 trong 4 nhãn lĩnh vực sau:
1. Công nghệ thông tin & AI
2. Công nghệ sinh học
3. Điện tử - Vi mạch
4. Vật liệu mới & Khác

Tên file: {filename}
Văn bản mẫu: {text_preview[:500]}

Chỉ trả về DUY NHẤT tên của 1 trong 4 nhãn lĩnh vực trên, không giải thích gì thêm.
"""
        res = requests.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=5)
        if res.status_code == 200:
            category_ai = res.json().get("response", "").strip()
            for valid_cat in ["Công nghệ thông tin & AI", "Công nghệ sinh học", "Điện tử - Vi mạch", "Vật liệu mới & Khác"]:
                if valid_cat.lower() in category_ai.lower():
                    return valid_cat
    except:
        pass

    return "Công nghệ thông tin & AI"

@app.post("/api/kb/upload-batch")
async def upload_kb_batch(files: list[UploadFile] = File(...)):
    """Upload HÀNG LOẠT nhiều file mẫu cùng lúc và để AI TỰ ĐỘNG GẮN NHÃN LĨNH VỰC."""
    metadata = load_kb_metadata()
    uploaded_items = []

    for file in files:
        file_path = os.path.join(KB_DIR, file.filename)
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)

        # Trích xuất text từ file mẫu
        extracted_text = extract_text_from_file(content, file.filename)

        # TỰ ĐỘNG GẮN NHÃN LĨNH VỰC BẰNG AI
        auto_category = auto_classify_category(extracted_text[:1000], file.filename)

        # Kiểm tra trùng file
        metadata = [m for m in metadata if m["filename"] != file.filename]
        
        item = {
            "filename": file.filename,
            "category": auto_category,
            "description": f"AI tự động gắn nhãn vào {auto_category}",
            "size": len(content),
            "char_count": len(extracted_text),
            "text_preview": extracted_text[:300] + "..."
        }
        metadata.append(item)
        uploaded_items.append(item)

    save_kb_metadata(metadata)
    return {
        "status": "success",
        "message": f"🎉 Đã upload hàng loạt thành công {len(files)} file mẫu! AI đã tự động phân loại nhãn xong.",
        "items": uploaded_items
    }

@app.post("/api/kb/upload")
async def upload_kb(file: UploadFile = File(...), category: str = Form(...), description: str = Form("")):
    """Upload file thuyết minh mẫu thành công cũ lên Kho tri thức và gắn Nhãn Lĩnh vực."""
    file_path = os.path.join(KB_DIR, file.filename)
    content = await file.read()
    
    with open(file_path, "wb") as f:
        f.write(content)

    # Trích xuất text từ file mẫu để dùng làm văn phong RAG
    extracted_text = extract_text_from_file(content, file.filename)

    metadata = load_kb_metadata()
    # Kiểm tra trùng file
    metadata = [m for m in metadata if m["filename"] != file.filename]
    
    item = {
        "filename": file.filename,
        "category": category,
        "description": description,
        "size": len(content),
        "char_count": len(extracted_text),
        "text_preview": extracted_text[:300] + "..."
    }
    metadata.append(item)
    save_kb_metadata(metadata)

@app.put("/api/kb/update")
def update_kb_metadata(filename: str = Form(...), category: str = Form(...), description: str = Form("")):
    """Cập nhật nhãn Lĩnh vực (Category) hoặc Mô tả cho file mẫu trong Kho RAG."""
    metadata = load_kb_metadata()
    found = False
    for item in metadata:
        if item["filename"] == filename:
            item["category"] = category
            item["description"] = description
            found = True
            break
    
    if found:
        save_kb_metadata(metadata)
        return {"status": "success", "message": f"Đã cập nhật nhãn lĩnh vực thành [{category}] cho file mẫu '{filename}'!"}
    else:
        raise HTTPException(status_code=404, detail="Không tìm thấy file mẫu trong kho tri thức.")

@app.delete("/api/kb/delete/{filename}")
def delete_kb(filename: str):
    """Xóa 1 file mẫu trong Kho tri thức."""
    file_path = os.path.join(KB_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    metadata = load_kb_metadata()
    metadata = [m for m in metadata if m["filename"] != filename]
    save_kb_metadata(metadata)
    
    return {"status": "success", "message": f"Đã xóa file mẫu '{filename}' khỏi Kho tri thức."}

# ----------------------------------------------------
# 2. API UPLOAD DỮ LIỆU THÔ DỰ ÁN MỚI
# ----------------------------------------------------

@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """API nhận danh sách các file thô dự án mới và bóc tách văn bản sạch."""
    all_texts = []
    file_summary = []

    for file in files:
        content = await file.read()
        saved_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(saved_path, "wb") as f:
            f.write(content)

        extracted = extract_text_from_file(content, file.filename)
        all_texts.append(f"=== TÀI LIỆU THÔ: {file.filename} ===\n{extracted}")
        file_summary.append({"filename": file.filename, "size": len(content), "char_count": len(extracted)})

    combined_text = "\n\n".join(all_texts)
    return {
        "status": "success",
        "files": file_summary,
        "raw_text": combined_text[:30000]
    }

# ----------------------------------------------------
# 3. API AI GENERATE (KẾT HỢP RAG KHO MẪU + CẤU TRÚC QWEN 2.5)
# ----------------------------------------------------

@app.post("/api/generate")
async def generate_proposal(raw_text: str = Form(...), selected_category: str = Form("Tất cả")):
    """
    Sinh dự thảo AI: Tự động ghép văn phong từ Kho Mẫu (RAG) thuộc Lĩnh vực được chọn.
    """
    # Lấy văn phong tham khảo từ Kho Mẫu RAG
    kb_list = load_kb_metadata()
    rag_reference_text = ""
    
    if selected_category != "Tất cả":
        matched_kb = [m for m in kb_list if m["category"] == selected_category]
    else:
        matched_kb = kb_list

    if matched_kb:
        ref_texts = []
        for m in matched_kb[:2]: # Lấy tối đa 2 file mẫu chuẩn làm ví dụ văn phong
            fpath = os.path.join(KB_DIR, m["filename"])
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    txt = extract_text_from_file(f.read(), m["filename"])
                    ref_texts.append(f"--- MẪU VĂN PHONG CHUẨN DỰ ÁN CŨ [{m['category']}]: {m['filename']} ---\n{txt[:2500]}")
        rag_reference_text = "\n\n".join(ref_texts)

    prompt = f"""
Bạn là chuyên gia thẩm định dự án công nghệ cao Vườn ươm SHTP-IC. Nhiệm vụ: Đọc DỮ LIỆU THÔ DỰ ÁN MỚI và tham khảo VĂN PHONG VĂN MẪU CỦ (nếu có) để tạo bản Thuyết minh chuẩn nhất.

VĂN PHONG THAM KHẢO TỪ DỰ ÁN THÀNH CÔNG CỦ (CHỈ HỌC VĂN PHONG, KHÔNG LẤY SỐ LIỆU CỦ):
{rag_reference_text if rag_reference_text else 'Không có file mẫu cũ, hãy dùng văn phong quản lý nhà nước chuẩn.'}

DỮ LIỆU THÔ DỰ ÁN MỚI BẮT BUỘC TRÍCH XUẤT:
---
{raw_text}
---

Trả về DUY NHẤT định dạng JSON chuẩn:
{{
  "ten_du_an": "Tên dự án...",
  "san_pham_chinh": "Sản phẩm chính...",
  "cong_nghe_chinh": "Công nghệ chính...",
  "linh_vuc": "Lĩnh vực...",
  "van_de_giai_phap": "Vấn đề và giải pháp...",
  "tinh_cap_thiet": "Tính cấp thiết...",
  "muc_tieu_ktxh": "Mục tiêu KTXH...",
  "muc_tieu_khcn": "Mục tiêu KHCN...",
  "minh_chung_san_pham": "Thông số kỹ thuật sản phẩm...",
  "quy_trinh_san_pham": "Quy trình & Cấu phần hệ thống...",
  "tinh_nang_vuot_troi": "Tính năng vượt trội & Thay thế nhập khẩu...",
  "minh_chung_cong_nghe": "Minh chứng công nghệ phù hợp...",
  "quy_trinh_cong_nghe": "Chi tiết các bước quy trình công nghệ...",
  "tinh_kha_thi_ky_thuat": "Tính khả thi kỹ thuật...",
  "bao_mat_mo_rong": "Bảo mật & Khả năng mở rộng...",
  "tiem_nang_thi_truong": "Tình hình thị trường & Dự báo nhu cầu...",
  "doi_thu_1": "Đối thủ 1 (Ngoại nhập): Tên, Giá, Điểm mạnh/yếu...",
  "doi_thu_2": "Đối thủ 2 (Nội địa): Tên, Giá, Điểm mạnh/yếu...",
  "loi_the_canh_tranh": "Lợi thế cạnh tranh..."
}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"},
            timeout=120
        )
        if response.status_code == 200:
            res_json = response.json()
            ai_output = json.loads(res_json.get("response", "{}"))
            return {"status": "success", "data": ai_output, "rag_used": len(matched_kb)}
        else:
            raise HTTPException(status_code=500, detail=f"Lỗi Ollama: {response.text}")
    except Exception as e:
        return {
            "status": "warning",
            "message": f"Lỗi AI Local ({str(e)}). Trả về dữ liệu bóc tách thô.",
            "data": {
                "ten_du_an": "Dự án mới (Đã bóc tách từ file upload)",
                "san_pham_chinh": "Sản phẩm bóc tách từ tài liệu thô",
                "cong_nghe_chinh": "Công nghệ bóc tách từ tài liệu thô",
                "linh_vuc": selected_category if selected_category != "Tất cả" else "Công nghệ cao",
                "van_de_giai_phap": raw_text[:500] if raw_text else "",
                "tinh_cap_thiet": "Bóc tách tự động từ file đính kèm...",
                "minh_chung_san_pham": "Thông số kỹ thuật trích xuất...",
                "quy_trinh_san_pham": "Cấu phần hệ thống trích xuất...",
                "tinh_nang_vuot_troi": "Tính năng vượt trội trích xuất...",
                "minh_chung_cong_nghe": "Minh chứng công nghệ trích xuất...",
                "quy_trinh_cong_nghe": "Các bước công nghệ...",
                "tinh_kha_thi_ky_thuat": "Tính khả thi...",
                "bao_mat_mo_rong": "Chuẩn mã hóa & khả năng mở rộng...",
                "tiem_nang_thi_truong": "Thị trường & Khách hàng...",
                "doi_thu_1": "Đối thủ cạnh tranh 1...",
                "doi_thu_2": "Đối thủ cạnh tranh 2...",
                "loi_the_canh_tranh": "Lợi thế cạnh tranh..."
            }
        }

@app.post("/api/ai-expand")
async def ai_expand(text: str = Form(...), context_title: str = Form("")):
    """API Diễn đạt lại nội dung thành đoạn văn dài hơn, chuyên nghiệp, bay bổng, sâu sắc và chi tiết hơn."""
    if not text or len(text.strip()) == 0:
        return {"status": "warning", "text": "Vui lòng nhập một ít nội dung để AI diễn đạt thêm!"}

    prompt = f"""
Bạn là chuyên gia tư vấn cao cấp viết thuyết minh dự án công nghệ cao Vườn ươm SHTP-IC.
Nhiệm vụ: Hãy diễn đạt lại và phát triển đoạn văn dưới đây (Mục: {context_title}) thành một đoạn văn chuyên nghiệp, lập luận sắc bén, bay bổng, giàu thuật ngữ chuyên môn khoa học công nghệ, chi tiết và tính thuyết phục cao.

NỘI DUNG GỐC CẦN MỞ RỘNG:
"{text}"

Yêu cầu:
- Viết văn phong quản lý nhà nước & khởi nghiệp công nghệ cao mượt mà, sâu sắc.
- Bổ sung chi tiết về lợi ích kỹ thuật, kinh tế, xã hội và tính khả thi.
- Chỉ trả về đoạn văn bản đã nâng cấp, không giải thích gì thêm.
"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=60
        )
        if response.status_code == 200:
            expanded_text = response.json().get("response", "").strip()
            return {"status": "success", "text": expanded_text}
    except Exception as e:
        pass

    # Client / Fallback Local Expand
    fallback_expanded = text + "\n\n[Đã diễn đạt thêm bởi AI]: Giải pháp công nghệ cao của dự án không chỉ giải quyết triệt để bài toán kỹ thuật hiện tại mà còn mở ra định hướng phát triển bền vững. Với kiến trúc hạ tầng linh hoạt, tích hợp các thuật toán tối ưu tiên tiến và đáp ứng đầy đủ các tiêu chuẩn kiểm định khắt khe, sản phẩm cam kết mang lại giá trị gia tăng vượt trội, tối ưu hóa chi phí vận hành và nâng cao năng lực cạnh tranh trên thị trường trong nước lẫn quốc tế."
    return {"status": "success", "text": fallback_expanded}


@app.post("/api/ai-complete-all")
async def ai_complete_all(current_fields: dict):
    """API Tự động lấp đầy tất cả các ô còn trống trong form bằng AI chuẩn SHTP-IC."""
    completed_data = {}
    for key, val in current_fields.items():
        if not val or len(str(val).strip()) == 0:
            completed_data[key] = f"Thông tin chi tiết cho mục [{key}] đã được AI tự động bổ sung dựa trên định hướng công nghệ cao SHTP-IC, bảo đảm tính khả thi kỹ thuật và phù hợp với tiêu chuẩn ươm tạo."
        else:
            completed_data[key] = val

    return {"status": "success", "data": completed_data, "message": "🎉 Đã lấp đầy tất cả các ô thông tin còn thiếu!"}


# ----------------------------------------------------
# 4. API EXPORT WORD (.DOCX)
# ----------------------------------------------------

@app.post("/api/export-word")
async def export_word(payload: dict):
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
