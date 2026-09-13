# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Phạm Khắc Tú
> **Mã Sinh Viên / Mã Học viên:** 2A202602866
> **Chủ đề Lựa chọn:** Trợ lý Học vụ & Tra cứu Lịch thi VinUni

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 5 / 5 | Yêu cầu gồm nhiều bước nối tiếp: xác định sinh viên, tra cứu GPA/lịch thi/cố vấn, rồi dùng kết quả để đặt lịch tư vấn. |
| **2. Tool Interaction** | 5 / 5 | Agent phải gọi MCP Server để truy vấn dữ liệu học vụ và thực hiện hành động tạo lịch hẹn. |
| **3. Dynamic Decision** | 4 / 5 | Việc đặt lịch phụ thuộc kết quả tra cứu: chỉ tiếp tục khi sinh viên tồn tại và dùng đúng cố vấn từ Observation. |
| **4. Long Horizon Goal** | 4 / 5 | Agent giữ mã sinh viên, thời gian mong muốn và mục tiêu tư vấn xuyên suốt một chuỗi xử lý nhiều bước. |
| **TỔNG ĐIỂM AGENTIC FIT** | **18 / 20** | *Bài toán đạt trên 12/20 và rất phù hợp triển khai Agentic System.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dưới đây là trace TC04 đa bước được sinh từ Gemini 3.6 Flash qua API thật:

```json
[
  {
    "step": 1,
    "query": "Hãy tra cứu GPA, lịch thi và tên cố vấn của sinh viên SV2026001, sau đó đặt lịch hẹn tư vấn với đúng cố vấn vào lúc 14:00 15/09/2026.",
    "action_type": "TOOL_EXECUTION",
    "thought": "Gemini quyết định gọi công cụ 'academic_query' với tham số: {\"student_id\": \"SV2026001\"}",
    "tool_name": "academic_query",
    "arguments": {
      "student_id": "SV2026001"
    },
    "observation": {
      "status": "SUCCESS",
      "student_id": "SV2026001",
      "data": {
        "full_name": "Nguyễn Văn An",
        "gpa": 3.85,
        "advisor": "PGS.TS Nguyễn Văn A",
        "exam_schedule": [
          {
            "course_code": "AI301",
            "datetime": "08:00 20/09/2026",
            "room": "C101"
          },
          {
            "course_code": "CS202",
            "datetime": "13:30 23/09/2026",
            "room": "B203"
          }
        ]
      }
    },
    "latency_ms": 2153.68
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "thought": "Gemini quyết định gọi công cụ 'schedule_appointment' với tham số: {\"datetime_str\": \"14:00 15/09/2026\", \"student_id\": \"SV2026001\", \"advisor_name\": \"PGS.TS Nguyễn Văn A\"}",
    "tool_name": "schedule_appointment",
    "arguments": {
      "student_id": "SV2026001",
      "datetime_str": "14:00 15/09/2026",
      "advisor_name": "PGS.TS Nguyễn Văn A"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-SV2026001-99",
      "message": "Đặt lịch thành công cho sinh viên SV2026001 với PGS.TS Nguyễn Văn A vào lúc 14:00 15/09/2026."
    },
    "latency_ms": 7565.3
  },
  {
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "thought": "Tổng hợp kết quả từ MCP Server thành công.",
    "output": "Sinh viên SV2026001 (Nguyễn Văn An), lớp AI-K4, GPA 3.85, trạng thái Đang học, cố vấn PGS.TS Nguyễn Văn A. Lịch thi: AI301 - Agentic AI, 08:00 20/09/2026, phòng C101; CS202 - Cấu trúc dữ liệu, 13:30 23/09/2026, phòng B203. Đặt lịch thành công cho sinh viên SV2026001 với PGS.TS Nguyễn Văn A vào lúc 14:00 15/09/2026.",
    "latency_ms": 10.0
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 5 lượt.
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
