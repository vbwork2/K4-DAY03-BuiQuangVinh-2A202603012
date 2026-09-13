# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Bùi Quang Vinh
> **Mã Sinh Viên / Mã Học viên:** 2A202603012
> **Chủ đề Lựa chọn:** Trợ lý tìm kiếm, tóm tắt và tổng hợp tài liệu

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 5 / 5 | Agent phải thực hiện chuỗi bước tìm kiếm tài liệu → lựa chọn tài liệu phù hợp → đọc nội dung → đánh giá thông tin → tổng hợp câu trả lời cuối cùng. |
| **2. Tool Interaction** | 5 / 5 | Agent cần sử dụng các công cụ `search_documents` và `read_document` thông qua MCP Server để truy xuất dữ liệu thay vì chỉ dựa vào kiến thức của LLM. |
| **3. Dynamic Decision** | 5 / 5 | Tài liệu cần đọc và số bước tiếp theo phụ thuộc trực tiếp vào kết quả của `search_documents` và các Observation trước đó. |
| **4. Long Horizon Goal** | 4 / 5 | Agent phải duy trì mục tiêu tổng hợp ban đầu xuyên suốt nhiều lần gọi công cụ và nhiều Observation trước khi tạo Final Answer. |
| **TỔNG ĐIỂM AGENTIC FIT** | **19 / 20** | Bài toán phù hợp với Agentic System vì yêu cầu multi-step reasoning, tool use và dynamic decision. |
---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
[
  {
    "step": 1,
    "query": "Tìm các tài liệu về RAG và tổng hợp ưu điểm, hạn chế",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "search_documents",
    "arguments": {
      "top_k": 5,
      "query": "RAG"
    },
    "observation": {
      "status": "SUCCESS",
      "query": "RAG",
      "results": [
        {
          "document_id": "DOC001",
          "title": "Introduction to Retrieval-Augmented Generation",
          "score": 1
        },
        {
          "document_id": "DOC002",
          "title": "Advantages of Retrieval-Augmented Generation",
          "score": 1
        },
        {
          "document_id": "DOC003",
          "title": "Limitations of Retrieval-Augmented Generation",
          "score": 1
        }
      ]
    },
    "latency_ms": 990.93
  },
  {
    "step": 2,
    "query": "Tìm các tài liệu về RAG và tổng hợp ưu điểm, hạn chế",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "read_document",
    "arguments": {
      "document_id": "DOC001"
    },
    "observation": {
      "status": "SUCCESS",
      "document_id": "DOC001",
      "title": "Introduction to Retrieval-Augmented Generation",
      "content": "\n        Retrieval-Augmented Generation combines information retrieval\n        with large language models. RAG allows a model to retrieve\n        external knowledge before generating its answer.\n        This can reduce hallucination and improve factual grounding.\n        "
    },
    "latency_ms": 1063.6
  },
  {
    "step": 3,
    "query": "Tìm các tài liệu về RAG và tổng hợp ưu điểm, hạn chế",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "read_document",
    "arguments": {
      "document_id": "DOC002"
    },
    "observation": {
      "status": "SUCCESS",
      "document_id": "DOC002",
      "title": "Advantages of Retrieval-Augmented Generation",
      "content": "\n        RAG allows knowledge to be updated without retraining the model.\n        It can improve factual accuracy and provide evidence from\n        external documents.\n        "
    },
    "latency_ms": 1295.1
  },
  {
    "step": 4,
    "query": "Tìm các tài liệu về RAG và tổng hợp ưu điểm, hạn chế",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "read_document",
    "arguments": {
      "document_id": "DOC003"
    },
    "observation": {
      "status": "SUCCESS",
      "document_id": "DOC003",
      "title": "Limitations of Retrieval-Augmented Generation",
      "content": "\n        RAG depends strongly on retrieval quality.\n        Poor retrieval may provide irrelevant context.\n        RAG systems also introduce additional latency and infrastructure\n        complexity.\n        "
    },
    "latency_ms": 1217.36
  },
  {
    "step": 5,
    "query": "Tìm các tài liệu về RAG và tổng hợp ưu điểm, hạn chế",
    "action_type": "FINAL_ANSWER",
    "thought": "Gemini xác định dữ liệu hiện tại đã đủ để trả lời.",
    "output": "Dựa trên các tài liệu đã được tìm kiếm và đọc (DOC001, DOC002, và DOC003), dưới đây là tổng hợp thông tin về RAG (Retrieval-Augmented Generation), bao gồm định nghĩa, ưu điểm và hạn chế:\n\n### 1. Giới thiệu về RAG (Retrieval-Augmented Generation)\n* **Khái niệm:** RAG kết hợp giữa hệ thống truy xuất thông tin (information retrieval) với các mô hình ngôn ngữ lớn (large language models). Công nghệ này cho phép mô hình truy xuất kiến thức từ bên ngoài trước khi tạo ra câu trả lời (Nguồn: *DOC001*).\n\n### 2. Ưu điểm của RAG\n* **Giảm hiện tượng ảo giác (Hallucination) và cải thiện độ chính xác thực tế:** Giúp mô hình căn cứ vào các dữ liệu thực tế (Nguồn: *DOC001*, *DOC002*).\n* **Cập nhật kiến thức linh hoạt:** Cho phép cập nhật tri thức mới mà không cần phải huấn luyện lại (retraining) toàn bộ mô hình (Nguồn: *DOC002*).\n* **Cung cấp bằng chứng minh bạch:** Có thể trích dẫn và cung cấp bằng chứng từ các tài liệu bên ngoài (Nguồn: *DOC002*).\n\n### 3. Hạn chế của RAG\n* **Phụ thuộc vào chất lượng truy xuất:** Hiệu suất của RAG phụ thuộc rất lớn vào việc truy xuất; nếu quá trình truy xuất kém, hệ thống có thể cung cấp ngữ cảnh không liên quan (Nguồn: *DOC003*).\n* **Độ trễ và độ phức tạp hạ tầng:** Hệ thống RAG làm tăng thêm độ trễ (latency) khi xử lý và làm phức tạp thêm về mặt hạ tầng kỹ thuật (Nguồn: *DOC003*).\n\n---\n**Các nguồn tài liệu đã sử dụng:**\n* `DOC001`: Introduction to Retrieval-Augmented Generation\n* `DOC002`: Advantages of Retrieval-Augmented Generation\n* `DOC003`: Limitations of Retrieval-Augmented Generation",
    "latency_ms": 2979.42
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x ] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 15 lượt.
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
