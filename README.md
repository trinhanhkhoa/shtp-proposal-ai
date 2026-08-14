# SHTP-IC Proposal AI Engine

Hệ thống AI Hỗ trợ Lập Dự thảo Thuyết minh Dự án Ươm tạo tại Vườn ươm Doanh nghiệp Công nghệ cao (SHTP-IC) chuẩn theo **Quyết định 23/2026/QĐ-TTg**.

## 🌟 Tính năng chính
1. **Local Open-Source AI (Qwen 2.5):** Xử lý hoàn toàn Miễn phí 100%, offline trên máy tính (MacBook M1/Windows) không tốn tiền Token và đảm bảo an toàn dữ liệu 100%.
2. **Bóc tách Dữ liệu thô Đa định dạng:** Đọc và tổng hợp tự động từ file PDF, Word, PowerPoint (Pitch Deck), Text.
3. **Chuẩn hóa Form Thuyết minh SHTP-IC 11 Trang:**
   - **Mục II.2 (Kỹ thuật & Sản phẩm):** Trích xuất chi tiết bảng Phụ lục QĐ 23/2026/QĐ-TTg, quy trình hoạt động, cấu phần hệ thống, thuật toán AI.
   - **Mục II.5 (Thị trường & Đối thủ):** Phân tích chi tiết 2 đối thủ cạnh tranh (Ngoại nhập & Nội địa), mô hình kinh doanh & dự ước doanh thu.
   - **Mục III.2 (Danh mục Đề xuất Hỗ trợ):** Tích chọn danh sách nhu cầu (Cơ sở vật chất, SHTT, ISO, Thử nghiệm đo lường...) để AI tự động điền các ô tương ứng vào Word.
4. **Export Word (.docx) Chuẩn:** Điền trực tiếp dữ liệu vào file mẫu `.docx` giữ nguyên 100% định dạng khung viền, font chữ.

## 🚀 Hướng dẫn Chạy Local Demo
```bash
# Bật server chạy ứng dụng demo UI
python3 -m http.server 8082 --directory .
```
Truy cập vào trình duyệt: `http://localhost:8082`

## 🛠 Công nghệ Sử dụng
- Frontend: HTML5, CSS3, Vanilla JS, FontAwesome icons.
- Backend Core: Python (FastAPI / Streamlit / docxtpl).
- AI Model: Ollama Local (Qwen 2.5 7B / 14B Instruct).
