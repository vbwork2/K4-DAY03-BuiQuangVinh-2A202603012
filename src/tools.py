"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "search_documents",
        "description": "Tìm kiếm các tài liệu liên quan đến chủ đề hoặc câu hỏi của người dùng.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Nội dung hoặc chủ đề cần tìm kiếm"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Số lượng tài liệu tối đa cần trả về"
                }
            },
            "required": ["query"]
        }
    },

    {
        "name": "read_document",
        "description": "Đọc nội dung đầy đủ của một tài liệu dựa trên document ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "ID của tài liệu cần đọc, ví dụ DOC001"
                }
            },
            "required": ["document_id"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

DOCUMENT_DATABASE = {
    "DOC001": {
        "title": "Introduction to Retrieval-Augmented Generation",
        "content": """
        Retrieval-Augmented Generation combines information retrieval
        with large language models. RAG allows a model to retrieve
        external knowledge before generating its answer.
        This can reduce hallucination and improve factual grounding.
        """,
        "tags": ["rag", "retrieval", "llm"]
    },

    "DOC002": {
        "title": "Advantages of Retrieval-Augmented Generation",
        "content": """
        RAG allows knowledge to be updated without retraining the model.
        It can improve factual accuracy and provide evidence from
        external documents.
        """,
        "tags": ["rag", "advantages"]
    },

    "DOC003": {
        "title": "Limitations of Retrieval-Augmented Generation",
        "content": """
        RAG depends strongly on retrieval quality.
        Poor retrieval may provide irrelevant context.
        RAG systems also introduce additional latency and infrastructure
        complexity.
        """,
        "tags": ["rag", "limitations"]
    },

    "DOC004": {
        "title": "Fine-tuning Large Language Models",
        "content": """
        Fine-tuning modifies model parameters using domain-specific data.
        It can adapt model behavior but requires training resources.
        """,
        "tags": ["fine-tuning", "llm"]
    }
}


def execute_search_documents(query: str, top_k: int = 3) -> str:
    query_words = query.lower().split()

    scored_documents = []

    for doc_id, doc in DOCUMENT_DATABASE.items():

        searchable_text = (
            doc["title"] + " " +
            doc["content"] + " " +
            " ".join(doc.get("tags", []))
        ).lower()

        score = sum(
            1
            for word in query_words
            if word in searchable_text
        )

        if score > 0:
            scored_documents.append({
                "document_id": doc_id,
                "title": doc["title"],
                "score": score
            })

    scored_documents.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return json.dumps({
        "status": "SUCCESS",
        "query": query,
        "results": scored_documents[:top_k]
    }, ensure_ascii=False)


def execute_read_document(document_id: str) -> str:

    document_id = document_id.strip().upper()

    document = DOCUMENT_DATABASE.get(document_id)

    if not document:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy tài liệu {document_id}"
        }, ensure_ascii=False)

    return json.dumps({
        "status": "SUCCESS",
        "document_id": document_id,
        "title": document["title"],
        "content": document["content"]
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "search_documents": execute_search_documents,
    "read_document": execute_read_document
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
