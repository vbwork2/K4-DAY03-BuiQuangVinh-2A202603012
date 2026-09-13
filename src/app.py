"""
DOCUMENT RESEARCH & SYNTHESIS REACT AGENT

Flow:

User Query
    ↓
LLM
    ↓
Tool Call
    ↓
MCP Server
    ↓
Observation
    ↓
LLM lần tiếp theo
    ↓
Tool tiếp / Final Answer
"""

import json
import os
import sys
import time

from dotenv import load_dotenv


# ==============================================================================
# PATH / ENCODING
# ==============================================================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_DIR = os.path.dirname(
    CURRENT_DIR
)

sys.path.append(CURRENT_DIR)


if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(
            encoding="utf-8"
        )
    except Exception:
        pass


load_dotenv()


# ==============================================================================
# IMPORT PROJECT MODULES
# ==============================================================================

from mcp_server import MCPAcademicServer

from prompts import (
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)

from providers import get_llm_provider


# ==============================================================================
# CONFIG
# ==============================================================================

def load_test_cases():
    """
    Load config/test_cases.json
    """

    config_path = os.path.join(
        PROJECT_DIR,
        "config",
        "test_cases.json"
    )

    if not os.path.exists(config_path):

        example_path = os.path.join(
            PROJECT_DIR,
            "config",
            "test_cases.example.json"
        )

        if not os.path.exists(example_path):
            raise FileNotFoundError(
                "Không tìm thấy test_cases.json "
                "hoặc test_cases.example.json"
            )

        print(
            "⚠️ Chưa có config/test_cases.json."
        )

        print(
            "⚠️ Đang dùng test_cases.example.json."
        )

        config_path = example_path

    with open(
        config_path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# ==============================================================================
# TRACE
# ==============================================================================

def save_waterfall_trace(
    trace_data: list
):
    """
    Save ReAct trace.
    """

    docs_dir = os.path.join(
        PROJECT_DIR,
        "docs"
    )

    os.makedirs(
        docs_dir,
        exist_ok=True
    )

    trace_path = os.path.join(
        docs_dir,
        "trace_waterfall.json"
    )

    with open(
        trace_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            trace_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"\n📊 Đã lưu Waterfall Trace:"
        f"\n   {trace_path}"
    )


# ==============================================================================
# BASELINE CHATBOT
# ==============================================================================

def run_baseline_chatbot(
    user_query: str,
    provider
):

    print(
        "\n💬 [CHATBOT BASELINE]"
    )

    print(
        f"👤 Query: {user_query}"
    )

    response = provider.generate(
        user_query,
        system_prompt=REACT_AGENT_SYSTEM_PROMPT
    )

    print(
        f"\n🤖 Response:\n{response}"
    )


# ==============================================================================
# REACT AGENT
# ==============================================================================

def run_react_agent(
    user_query: str,
    provider,
    mcp_server: MCPAcademicServer
) -> list:
    """
    Multi-step ReAct Loop.

    Quan trọng:
    Sau Tool Observation KHÔNG break.

    Observation được append vào context,
    sau đó LLM được gọi lại.
    """

    print(
        "\n=================================================="
    )

    print(
        "🤖 DOCUMENT RESEARCH & SYNTHESIS AGENT"
    )

    print(
        "=================================================="
    )

    print(
        f"👤 Query: {user_query}"
    )

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    step = 0

    trace_logs = []

    context = []

    tools_list = mcp_server.list_tools()

    # chống loop cùng một tool mãi mãi
    tool_call_counter = {}

    final_answer_generated = False

    # ------------------------------------------------------------------
    # ReAct Loop
    # ------------------------------------------------------------------

    while step < MAX_ITERATIONS:

        step += 1

        print(
            f"\n--- 🔄 ReAct Step "
            f"{step}/{MAX_ITERATIONS} ---"
        )

        start_time = time.time()

        llm_response = (
            provider.generate_with_tools(
                user_query,
                tools_list,
                system_prompt=(
                    REACT_AGENT_SYSTEM_PROMPT
                ),
                context=context
            )
        )

        latency_ms = round(
            (
                time.time()
                - start_time
            ) * 1000,
            2
        )

        response_type = llm_response.get(
            "type"
        )

        thought = llm_response.get(
            "thought",
            "Đang quyết định bước tiếp theo."
        )

        print(
            f"🧠 [Thought Summary]: {thought}"
        )

        # ==============================================================
        # CASE 1: FINAL ANSWER
        # ==============================================================

        if response_type == "text":

            content = llm_response.get(
                "content",
                ""
            )

            print(
                f"\n🏁 [Final Answer]\n{content}"
            )

            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": content,
                "latency_ms": latency_ms
            })

            final_answer_generated = True

            break

        # ==============================================================
        # CASE 2: TOOL CALL
        # ==============================================================

        if response_type == "tool_call":

            tool_name = llm_response.get(
                "tool_name"
            )

            arguments = llm_response.get(
                "arguments",
                {}
            )

            print(
                f"🛠️ [Action]: "
                f"{tool_name}"
            )

            print(
                "📦 [Arguments]: "
                + json.dumps(
                    arguments,
                    ensure_ascii=False
                )
            )

            # ----------------------------------------------------------
            # Validate tool
            # ----------------------------------------------------------

            available_tools = {
                tool.get("name")
                for tool in tools_list
            }

            if tool_name not in available_tools:

                observation = {
                    "status": "UNKNOWN_TOOL",
                    "message": (
                        f"Tool '{tool_name}' "
                        f"không tồn tại."
                    )
                }

            else:

                # ------------------------------------------------------
                # Duplicate detection
                # ------------------------------------------------------

                call_signature = (
                    tool_name
                    + ":"
                    + json.dumps(
                        arguments,
                        ensure_ascii=False,
                        sort_keys=True
                    )
                )

                tool_call_counter[
                    call_signature
                ] = (
                    tool_call_counter.get(
                        call_signature,
                        0
                    )
                    + 1
                )

                # Nếu model gọi giống hệt > 1 lần
                if (
                    tool_call_counter[
                        call_signature
                    ] > 1
                ):

                    observation = {
                        "status":
                            "DUPLICATE_CALL_BLOCKED",

                        "message": (
                            "Tool này với cùng "
                            "tham số đã được gọi trước đó. "
                            "Hãy sử dụng Observation đã có "
                            "hoặc chọn bước tiếp theo."
                        )
                    }

                else:

                    # --------------------------------------------------
                    # MCP CALL
                    # --------------------------------------------------

                    try:

                        mcp_response = (
                            mcp_server.call_tool(
                                tool_name,
                                arguments
                            )
                        )

                        observation = (
                            mcp_response.get(
                                "result",
                                {}
                            )
                        )

                    except Exception as error:

                        observation = {
                            "status":
                                "MCP_EXECUTION_ERROR",

                            "message":
                                str(error)
                        }

            # ----------------------------------------------------------
            # Print observation
            # ----------------------------------------------------------

            print(
                "👁️ [Observation]:"
            )

            print(
                json.dumps(
                    observation,
                    ensure_ascii=False,
                    indent=2
                )
            )

            # ----------------------------------------------------------
            # Trace
            # ----------------------------------------------------------

            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type":
                    "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": observation,
                "latency_ms": latency_ms
            })

            # ----------------------------------------------------------
            # QUAN TRỌNG:
            # observation được đưa trở lại context
            # ----------------------------------------------------------

            context.append({
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": observation
            })

            # KHÔNG BREAK
            # LLM tiếp tục suy luận vòng sau

            continue

        # ==============================================================
        # CASE 3: INVALID PROVIDER RESPONSE
        # ==============================================================

        print(
            "⚠️ Provider trả về response "
            "không hợp lệ:"
        )

        print(
            json.dumps(
                llm_response,
                ensure_ascii=False,
                indent=2
            )
        )

        trace_logs.append({
            "step": step,
            "query": user_query,
            "action_type":
                "PROVIDER_ERROR",
            "output": llm_response,
            "latency_ms": latency_ms
        })

        break

    # ------------------------------------------------------------------
    # Nếu model dùng hết MAX_ITERATIONS
    # ------------------------------------------------------------------

    if not final_answer_generated:

        message = (
            "Agent đã đạt giới hạn số bước "
            "ReAct trước khi tạo được "
            "Final Answer."
        )

        print(
            f"\n⚠️ {message}"
        )

        trace_logs.append({
            "step": step + 1,
            "query": user_query,
            "action_type":
                "MAX_ITERATIONS_REACHED",
            "output": message
        })

    return trace_logs


# ==============================================================================
# INTERACTIVE MODE
# ==============================================================================

def run_interactive(
    provider,
    mcp_server
):

    print(
        "\n🎮 INTERACTIVE MODE"
    )

    print(
        "Gợi ý:"
    )

    print(
        "- Tìm tài liệu về RAG."
    )

    print(
        "- Đọc DOC001 và tóm tắt."
    )

    print(
        "- Tìm các tài liệu về RAG và "
        "tổng hợp ưu điểm, hạn chế."
    )

    print(
        "- Đọc DOC999."
    )

    print(
        "\nGõ exit để thoát.\n"
    )

    while True:

        try:

            query = input(
                "👤 User: "
            ).strip()

            if (
                not query
                or query.lower()
                in ["exit", "quit"]
            ):

                print(
                    "👋 Kết thúc."
                )

                break

            logs = run_react_agent(
                query,
                provider,
                mcp_server
            )

            save_waterfall_trace(
                logs
            )

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print(
                "\n👋 Kết thúc."
            )

            break


# ==============================================================================
# TEST SUITE
# ==============================================================================

def run_test_suite(
    provider,
    mcp_server
):

    tests = load_test_cases()

    all_traces = []

    completed = 0

    print(
        "\n🧪 RUNNING TEST SUITE"
    )

    print(
        f"Total: {len(tests)} test cases"
    )

    for test in tests:

        print(
            "\n\n"
            "##################################################"
        )

        print(
            f"🧪 {test['id']}"
        )

        print(
            f"Type: {test['type']}"
        )

        print(
            f"Complexity: "
            f"{test['complexity']}"
        )

        print(
            f"Expected: "
            f"{test['expected_behavior']}"
        )

        print(
            "##################################################"
        )

        question = test[
            "question"
        ].strip()

        if question.startswith(
            "TODO"
        ):
            print(
                "⏸️ Test chưa được hoàn thiện."
            )

            continue

        logs = run_react_agent(
            question,
            provider,
            mcp_server
        )

        # add test id vào từng trace
        for log in logs:
            log["test_case_id"] = (
                test["id"]
            )

        all_traces.extend(
            logs
        )

        completed += 1

    print(
        "\n=================================================="
    )

    print(
        "📊 TEST SUITE RESULT"
    )

    print(
        "=================================================="
    )

    print(
        f"Executed: "
        f"{completed}/{len(tests)}"
    )

    if all_traces:
        save_waterfall_trace(
            all_traces
        )


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":

    print(
        "=================================================="
    )

    print(
        "📚 DOCUMENT SUMMARIZATION "
        "& SYNTHESIS REACT AGENT"
    )

    print(
        "=================================================="
    )

    provider = get_llm_provider()

    mcp_server = MCPAcademicServer()

    print(
        f"🔌 LLM Provider: "
        f"{provider.__class__.__name__}"
    )

    print(
        f"🌐 MCP Server: "
        f"{mcp_server.server_name}"
    )

    print(
        f"🛠️ Available Tools: "
        f"{len(mcp_server.list_tools())}"
    )

    # --------------------------------------------------------------
    # Interactive
    # --------------------------------------------------------------

    if "--interactive" in sys.argv:

        run_interactive(
            provider,
            mcp_server
        )

    # --------------------------------------------------------------
    # All tests
    # --------------------------------------------------------------

    elif "--all" in sys.argv:

        run_test_suite(
            provider,
            mcp_server
        )

    # --------------------------------------------------------------
    # Help
    # --------------------------------------------------------------

    else:

        print(
            "\nUsage:"
        )

        print(
            "python src/app.py --all"
        )

        print(
            "python src/app.py --interactive"
        )