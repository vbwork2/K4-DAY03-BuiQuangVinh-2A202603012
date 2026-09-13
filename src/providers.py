"""
LLM PROVIDERS
Hỗ trợ:
- Mock Offline
- Google Gemini
- OpenAI

Có hỗ trợ Native Tool Calling + multi-step ReAct context.
"""

import os
import sys
import re
import json
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv


if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


load_dotenv()


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def serialize_context(context: Optional[List[Dict[str, Any]]]) -> str:
    """
    Chuyển lịch sử Action/Observation thành text
    để gửi lại LLM ở vòng ReAct tiếp theo.
    """

    if not context:
        return "Chưa có Action/Observation nào."

    blocks = []

    for index, event in enumerate(context, start=1):
        tool_name = event.get("tool_name", "")
        arguments = event.get("arguments", {})
        observation = event.get("observation", {})

        blocks.append(
            f"""
STEP {index}
Action: {tool_name}
Arguments:
{json.dumps(arguments, ensure_ascii=False, indent=2)}

Observation:
{json.dumps(observation, ensure_ascii=False, indent=2)}
""".strip()
        )

    return "\n\n".join(blocks)


def build_agent_prompt(
    user_query: str,
    context: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Prompt được gửi lại ở mỗi vòng ReAct.
    """

    history = serialize_context(context)

    return f"""
YÊU CẦU GỐC CỦA NGƯỜI DÙNG:
{user_query}

LỊCH SỬ ACTION / OBSERVATION:
{history}

Hãy quyết định BƯỚC TIẾP THEO.

Quy tắc:
- Nếu chưa đủ dữ liệu, hãy gọi Tool phù hợp.
- Nếu search_documents đã trả về tài liệu nhưng cần nội dung,
  hãy dùng read_document.
- Nếu yêu cầu tổng hợp nhiều nguồn, hãy đọc ít nhất 2 tài liệu liên quan
  trước khi đưa ra kết luận nếu có đủ tài liệu.
- Không gọi lại cùng một Tool với cùng tham số nếu dữ liệu đó đã có.
- Không được bịa nội dung tài liệu.
- Nếu đã đủ dữ liệu, trả lời Final Answer.
- Trong Final Answer, hãy ghi rõ Document ID / nguồn đã sử dụng.
""".strip()


# ==============================================================================
# BASE PROVIDER
# ==============================================================================

class BaseLLMProvider:

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:
        raise NotImplementedError

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError


# ==============================================================================
# MOCK PROVIDER
# ==============================================================================

class MockOfflineProvider(BaseLLMProvider):
    """
    Mock Provider dùng để test ReAct Loop mà không tốn API.

    Đây KHÔNG phải kết quả nghiệm thu cuối cùng.
    """

    def __init__(self):
        self.model_name = "Offline-Mock-Document-Agent"

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:
        return (
            "[Mock Response] Đây là phản hồi offline dùng để kiểm thử "
            "logic chương trình. Khi nghiệm thu hãy sử dụng API LLM thật."
        )

    # ------------------------------------------------------------------
    # Helpers dành cho mock
    # ------------------------------------------------------------------

    def _find_tool_events(
        self,
        context: Optional[List[Dict[str, Any]]],
        tool_name: str
    ) -> List[Dict[str, Any]]:

        return [
            event
            for event in (context or [])
            if event.get("tool_name") == tool_name
        ]

    def _read_document_ids(
        self,
        context: Optional[List[Dict[str, Any]]]
    ) -> set:

        ids = set()

        for event in self._find_tool_events(context, "read_document"):
            doc_id = (
                event
                .get("arguments", {})
                .get("document_id")
            )

            if doc_id:
                ids.add(doc_id.upper())

        return ids

    def _latest_search_results(
        self,
        context: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:

        events = self._find_tool_events(
            context,
            "search_documents"
        )

        if not events:
            return []

        observation = events[-1].get(
            "observation",
            {}
        )

        return observation.get(
            "results",
            []
        )

    def _successful_documents(
        self,
        context: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:

        documents = []

        for event in self._find_tool_events(
            context,
            "read_document"
        ):
            observation = event.get(
                "observation",
                {}
            )

            if observation.get("status") == "SUCCESS":
                documents.append(observation)

        return documents

    # ------------------------------------------------------------------
    # Mock ReAct
    # ------------------------------------------------------------------

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:

        context = context or []

        query_lower = prompt.lower()

        # ==============================================================
        # TC05 / explicit document ID
        # ==============================================================

        document_ids = re.findall(
            r"\bDOC\d+\b",
            prompt.upper()
        )

        # Nếu user chỉ định trực tiếp document
        if document_ids:
            requested_doc = document_ids[0]

            read_ids = self._read_document_ids(context)

            if requested_doc not in read_ids:
                return {
                    "type": "tool_call",
                    "tool_name": "read_document",
                    "arguments": {
                        "document_id": requested_doc
                    },
                    "thought": (
                        f"Cần đọc {requested_doc} trước khi "
                        f"có thể trả lời yêu cầu."
                    )
                }

            # Đã gọi read_document -> tìm observation
            for event in reversed(context):
                if (
                    event.get("tool_name") == "read_document"
                    and event.get(
                        "arguments",
                        {}
                    ).get(
                        "document_id",
                        ""
                    ).upper() == requested_doc
                ):
                    observation = event.get(
                        "observation",
                        {}
                    )

                    if observation.get("status") == "NOT_FOUND":
                        return {
                            "type": "text",
                            "content": (
                                f"Không tìm thấy tài liệu "
                                f"{requested_doc} trong kho tài liệu."
                            ),
                            "thought": (
                                "Tool trả về NOT_FOUND nên không "
                                "được tự tạo nội dung tài liệu."
                            )
                        }

                    if observation.get("status") == "SUCCESS":
                        title = observation.get(
                            "title",
                            ""
                        )

                        content = observation.get(
                            "content",
                            ""
                        )

                        return {
                            "type": "text",
                            "content": (
                                f"Tóm tắt {requested_doc} — {title}:\n\n"
                                f"{content.strip()}\n\n"
                                f"Nguồn: {requested_doc}"
                            ),
                            "thought": (
                                "Đã có nội dung tài liệu và có thể "
                                "tạo câu trả lời cuối cùng."
                            )
                        }

        # ==============================================================
        # TC04: Multi-document synthesis
        # ==============================================================

        is_synthesis = any(
            keyword in query_lower
            for keyword in [
                "tổng hợp",
                "ưu điểm",
                "hạn chế",
                "so sánh",
                "nhiều tài liệu"
            ]
        )

        if is_synthesis:

            search_events = self._find_tool_events(
                context,
                "search_documents"
            )

            # Chưa search -> search trước
            if not search_events:
                return {
                    "type": "tool_call",
                    "tool_name": "search_documents",
                    "arguments": {
                        "query": (
                            "Retrieval-Augmented Generation "
                            "RAG advantages limitations"
                        ),
                        "top_k": 3
                    },
                    "thought": (
                        "Cần tìm nhiều tài liệu liên quan trước "
                        "khi tổng hợp."
                    )
                }

            search_results = self._latest_search_results(
                context
            )

            read_ids = self._read_document_ids(
                context
            )

            # Đọc lần lượt các tài liệu search được
            for result in search_results:
                doc_id = result.get(
                    "document_id",
                    ""
                ).upper()

                if doc_id and doc_id not in read_ids:
                    return {
                        "type": "tool_call",
                        "tool_name": "read_document",
                        "arguments": {
                            "document_id": doc_id
                        },
                        "thought": (
                            f"Cần đọc {doc_id} để có nội dung "
                            f"thực tế phục vụ tổng hợp."
                        )
                    }

            # Đã đọc tài liệu -> tổng hợp
            documents = self._successful_documents(
                context
            )

            if documents:
                source_lines = []
                evidence_lines = []

                for doc in documents:
                    doc_id = doc.get(
                        "document_id",
                        ""
                    )

                    title = doc.get(
                        "title",
                        ""
                    )

                    content = doc.get(
                        "content",
                        ""
                    ).strip()

                    source_lines.append(
                        f"- {doc_id}: {title}"
                    )

                    evidence_lines.append(
                        f"[{doc_id}] {content}"
                    )

                final_answer = (
                    "Tổng hợp từ các tài liệu đã đọc:\n\n"
                    + "\n\n".join(evidence_lines)
                    + "\n\nNguồn đã sử dụng:\n"
                    + "\n".join(source_lines)
                )

                return {
                    "type": "text",
                    "content": final_answer,
                    "thought": (
                        "Đã đọc các nguồn liên quan và đủ dữ liệu "
                        "để tổng hợp kết quả."
                    )
                }

        # ==============================================================
        # TC02: Search documents
        # ==============================================================

        is_search = (
            "tìm" in query_lower
            and "tài liệu" in query_lower
        )

        if is_search:

            search_events = self._find_tool_events(
                context,
                "search_documents"
            )

            if not search_events:
                return {
                    "type": "tool_call",
                    "tool_name": "search_documents",
                    "arguments": {
                        "query": (
                            "Retrieval-Augmented Generation RAG"
                        ),
                        "top_k": 3
                    },
                    "thought": (
                        "Người dùng yêu cầu tìm tài liệu nên "
                        "cần sử dụng search_documents."
                    )
                }

            results = self._latest_search_results(
                context
            )

            if not results:
                return {
                    "type": "text",
                    "content": (
                        "Không tìm thấy tài liệu phù hợp "
                        "trong kho tài liệu."
                    ),
                    "thought": (
                        "Search không trả về kết quả."
                    )
                }

            lines = []

            for result in results:
                lines.append(
                    f"- {result.get('document_id')}: "
                    f"{result.get('title')}"
                )

            return {
                "type": "text",
                "content": (
                    "Các tài liệu tìm thấy:\n"
                    + "\n".join(lines)
                ),
                "thought": (
                    "Đã nhận được danh sách tài liệu từ "
                    "search_documents."
                )
            }

        # ==============================================================
        # TC01: Direct answer
        # ==============================================================

        return {
            "type": "text",
            "content": (
                "Trí tuệ nhân tạo (AI) là lĩnh vực nghiên cứu "
                "và phát triển các hệ thống máy tính có khả năng "
                "thực hiện những nhiệm vụ thường cần trí thông minh "
                "của con người, chẳng hạn như nhận dạng, suy luận, "
                "học từ dữ liệu và xử lý ngôn ngữ."
            ),
            "thought": (
                "Đây là câu hỏi kiến thức chung nên không cần gọi Tool."
            )
        }


# ==============================================================================
# GEMINI
# ==============================================================================

class GeminiProvider(BaseLLMProvider):

    def __init__(
        self,
        api_key: str = None,
        model: str = None
    ):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
        )

        self.model_name = (
            model
            or os.getenv("LLM_MODEL")
            or "gemini-2.5-flash"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:

        if (
            not self.api_key
            or self.api_key == "your_gemini_api_key_here"
        ):
            return (
                "[Gemini Error] Chưa cấu hình "
                "GEMINI_API_KEY."
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=self.api_key
            )

            config = types.GenerateContentConfig(
                system_instruction=(
                    system_prompt
                    if system_prompt
                    else None
                ),
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            return response.text or ""

        except Exception as e:
            return f"[Gemini Exception]: {e}"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:

        if (
            not self.api_key
            or self.api_key == "your_gemini_api_key_here"
        ):
            print(
                "ℹ️ Không có Gemini API Key. "
                "Fallback sang MockOfflineProvider."
            )

            return MockOfflineProvider().generate_with_tools(
                prompt,
                tools_schema,
                system_prompt,
                context
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=self.api_key
            )

            declarations = []

            for tool in tools_schema:
                declarations.append({
                    "name": tool["name"],
                    "description": tool.get(
                        "description",
                        ""
                    ),
                    "parameters": tool.get(
                        "parameters",
                        {}
                    )
                })

            config = types.GenerateContentConfig(
                system_instruction=(
                    system_prompt
                    if system_prompt
                    else None
                ),
                tools=[
                    {
                        "function_declarations":
                            declarations
                    }
                ],
                temperature=0.1
            )

            react_prompt = build_agent_prompt(
                prompt,
                context
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=react_prompt,
                config=config
            )

            function_calls = getattr(
                response,
                "function_calls",
                None
            )

            if function_calls:
                call = function_calls[0]

                args = (
                    dict(call.args)
                    if getattr(call, "args", None)
                    else {}
                )

                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": (
                        f"Gemini chọn Tool '{call.name}' "
                        f"với tham số "
                        f"{json.dumps(args, ensure_ascii=False)}."
                    )
                }

            return {
                "type": "text",
                "content": response.text or "",
                "thought": (
                    "Gemini xác định dữ liệu hiện tại "
                    "đã đủ để trả lời."
                )
            }

        except Exception as e:
            print(
                f"⚠️ Gemini API error: {e}"
            )

            print(
                "⚠️ Fallback sang MockOfflineProvider."
            )

            return MockOfflineProvider().generate_with_tools(
                prompt,
                tools_schema,
                system_prompt,
                context
            )


# ==============================================================================
# OPENAI
# ==============================================================================

class OpenAIProvider(BaseLLMProvider):

    def __init__(
        self,
        api_key: str = None,
        model: str = None
    ):
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
        )

        self.model_name = (
            model
            or os.getenv("LLM_MODEL")
            or "gpt-4o-mini"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:

        if (
            not self.api_key
            or self.api_key == "your_openai_api_key_here"
        ):
            return (
                "[OpenAI Error] Chưa cấu hình "
                "OPENAI_API_KEY."
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key
            )

            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.2
            )

            return (
                response
                .choices[0]
                .message
                .content
                or ""
            )

        except Exception as e:
            return f"[OpenAI Exception]: {e}"

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
        context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:

        if (
            not self.api_key
            or self.api_key == "your_openai_api_key_here"
        ):
            print(
                "ℹ️ Không có OpenAI API Key. "
                "Fallback sang MockOfflineProvider."
            )

            return MockOfflineProvider().generate_with_tools(
                prompt,
                tools_schema,
                system_prompt,
                context
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key
            )

            tools = []

            for tool in tools_schema:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get(
                            "description",
                            ""
                        ),
                        "parameters": tool.get(
                            "parameters",
                            {}
                        )
                    }
                })

            react_prompt = build_agent_prompt(
                prompt,
                context
            )

            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": react_prompt
            })

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1
            )

            message = (
                response
                .choices[0]
                .message
            )

            if message.tool_calls:
                call = message.tool_calls[0]

                arguments = (
                    json.loads(
                        call.function.arguments
                    )
                    if call.function.arguments
                    else {}
                )

                return {
                    "type": "tool_call",
                    "tool_name": (
                        call.function.name
                    ),
                    "arguments": arguments,
                    "thought": (
                        f"OpenAI chọn Tool "
                        f"'{call.function.name}' với "
                        f"{json.dumps(arguments, ensure_ascii=False)}."
                    )
                }

            return {
                "type": "text",
                "content": message.content or "",
                "thought": (
                    "OpenAI xác định dữ liệu hiện tại "
                    "đã đủ để trả lời."
                )
            }

        except Exception as e:
            print(
                f"⚠️ OpenAI API error: {e}"
            )

            print(
                "⚠️ Fallback sang MockOfflineProvider."
            )

            return MockOfflineProvider().generate_with_tools(
                prompt,
                tools_schema,
                system_prompt,
                context
            )


# ==============================================================================
# PROVIDER FACTORY
# ==============================================================================

def get_llm_provider() -> BaseLLMProvider:

    provider_type = os.getenv(
        "LLM_PROVIDER",
        "mock"
    ).lower()

    if provider_type == "gemini":

        key = os.getenv(
            "GEMINI_API_KEY"
        )

        if (
            key
            and key != "your_gemini_api_key_here"
        ):
            return GeminiProvider()

        return MockOfflineProvider()

    if provider_type == "openai":

        key = os.getenv(
            "OPENAI_API_KEY"
        )

        if (
            key
            and key != "your_openai_api_key_here"
        ):
            return OpenAIProvider()

        return MockOfflineProvider()

    return MockOfflineProvider()