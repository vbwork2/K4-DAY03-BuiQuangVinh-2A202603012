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
        "published_at": "2023-05-01",

        "content": """
        Retrieval-Augmented Generation combines information retrieval
        with large language models. It allows external knowledge to be
        retrieved before response generation.
        """,

        "tags": [
            "rag",
            "retrieval",
            "llm"
        ],

        "claims": [
            "RAG combines retrieval with language generation.",
            "External knowledge can improve factual grounding."
        ],

        "references": []
    },


    "DOC002": {
        "title": "Advantages of Retrieval-Augmented Generation",
        "published_at": "2024-02-10",

        "content": """
        Later RAG systems showed that knowledge can be updated without
        retraining the language model. They can also provide evidence
        from retrieved documents.
        """,

        "tags": [
            "rag",
            "retrieval",
            "advantages"
        ],

        "claims": [
            "RAG can update knowledge without retraining.",
            "RAG improves factual grounding.",
            "RAG can provide source evidence."
        ],

        "references": [
            "DOC001"
        ]
    },


    "DOC003": {
        "title": "Limitations of Retrieval-Augmented Generation",
        "published_at": "2025-03-15",

        "content": """
        Recent research highlights that retrieval quality strongly
        affects RAG performance. Poor retrieval can introduce irrelevant
        context, while complex retrieval pipelines increase latency.
        """,

        "tags": [
            "rag",
            "retrieval",
            "limitations"
        ],

        "claims": [
            "RAG performance depends strongly on retrieval quality.",
            "Poor retrieval can introduce irrelevant information.",
            "RAG pipelines introduce additional latency."
        ],

        "references": [
            "DOC001",
            "DOC002"
        ]
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
