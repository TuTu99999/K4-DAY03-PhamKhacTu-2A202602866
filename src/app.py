"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import re
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPAcademicServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def _extract_student_id(text: str) -> str:
    """Lấy mã sinh viên từ câu hỏi để kiểm tra lại arguments do LLM sinh ra."""
    match = re.search(r"\bSV\d{7}\b", text, flags=re.IGNORECASE)
    return match.group(0).upper() if match else ""


def _is_multi_step_booking(user_query: str) -> bool:
    """Nhận diện yêu cầu vừa tra cứu vừa đặt lịch với đúng cố vấn."""
    query = user_query.lower()
    needs_booking = "đặt lịch" in query or "hẹn tư vấn" in query
    needs_lookup = any(keyword in query for keyword in ("tra cứu", "gpa", "lịch thi", "đúng cố vấn"))
    return needs_booking and needs_lookup


def _format_academic_result(observation: dict) -> str:
    data = observation.get("data", {})
    exams = data.get("exam_schedule", [])
    if exams:
        exam_text = "; ".join(
            f"{exam.get('course_code', '')} - {exam.get('course_name', '')}, "
            f"{exam.get('datetime', '')}, phòng {exam.get('room', '')}"
            for exam in exams
        )
    else:
        exam_text = "chưa có lịch thi"

    return (
        f"Sinh viên {observation.get('student_id', '')} ({data.get('full_name', '')}), "
        f"lớp {data.get('class', '')}, GPA {data.get('gpa', '')}, "
        f"trạng thái {data.get('status', '')}, cố vấn {data.get('advisor', '')}. "
        f"Lịch thi: {exam_text}."
    )


def _build_final_answer(observations: list) -> str:
    """Tổng hợp câu trả lời chỉ từ dữ liệu mà MCP Server đã trả về."""
    parts = []
    for observation in observations:
        status = observation.get("status")
        if status == "SUCCESS" and "data" in observation:
            parts.append(_format_academic_result(observation))
        elif status == "SUCCESS" and observation.get("message"):
            parts.append(observation["message"])
        elif status == "NOT_FOUND":
            parts.append(observation.get("message", "Không tìm thấy thông tin sinh viên yêu cầu."))
        else:
            parts.append(f"Phản hồi từ công cụ: {json.dumps(observation, ensure_ascii=False)}")
    return " ".join(parts)


def run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    observations = []
    called_tools = []
    student_id = _extract_student_id(user_query)
    multi_step_booking = _is_multi_step_booking(user_query)

    # Với yêu cầu đa bước, buộc bước đầu xác minh hồ sơ/cố vấn. Observation
    # của bước này sẽ trở thành ngữ cảnh để LLM quyết định bước đặt lịch.
    if multi_step_booking:
        current_prompt = (
            f"Chỉ thực hiện bước đầu tiên: tra cứu hồ sơ, GPA, lịch thi và cố vấn "
            f"của sinh viên {student_id}. Chưa thực hiện hành động tiếp theo ở bước này."
        )
    else:
        current_prompt = user_query
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Gọi LLM với Native Tool Calling Specs
        llm_response = provider.generate_with_tools(
            current_prompt,
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT
        )
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        
        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            return trace_logs
            
        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})

            # Mã sinh viên trong câu hỏi là nguồn chuẩn; tránh trường hợp model
            # suy diễn hoặc Mock Provider trả về một mã cố định khác yêu cầu.
            if student_id and tool_name in ("academic_query", "schedule_appointment"):
                arguments["student_id"] = student_id

            # Ở bước đặt lịch đa bước, dùng đúng cố vấn lấy từ Observation.
            if tool_name == "schedule_appointment" and observations:
                academic_data = next(
                    (item.get("data", {}) for item in observations if "data" in item),
                    {}
                )
                if academic_data.get("advisor"):
                    arguments["advisor_name"] = academic_data["advisor"]
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            # Thực thi Tool qua MCP Server
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            observations.append(obs_data)
            called_tools.append(tool_name)
            
            if not obs_data:
                print(f"👁️ [Observation từ MCP Server]: {{}}")
                print(f"⚠️ [CHÚ Ý]: MCP Server trả về kết quả rỗng! Học viên cần hoàn thành TODO 2.1 trong 'src/mcp_server.py'.")
                final_answer = "Chưa thể trả lời chi tiết do chưa nhận được dữ liệu từ MCP Server (hãy hoàn thành TODO 2.1)."
            else:
                obs_str = json.dumps(obs_data, ensure_ascii=False)
                print(f"👁️ [Observation từ MCP Server]: {obs_str}")
                
                final_answer = _build_final_answer(observations)
            
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "thought": thought,
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })
            
            # Nếu đây là yêu cầu đa bước và vừa tra cứu thành công, nạp
            # Observation vào prompt để LLM chọn tool đặt lịch ở vòng kế tiếp.
            if (
                multi_step_booking
                and tool_name == "academic_query"
                and obs_data.get("status") == "SUCCESS"
                and "schedule_appointment" not in called_tools
            ):
                advisor = obs_data.get("data", {}).get("advisor", "")
                current_prompt = (
                    f"Observation: {json.dumps(obs_data, ensure_ascii=False)}\n"
                    f"Tiếp tục mục tiêu ban đầu: đặt lịch hẹn cho {student_id} với "
                    f"cố vấn {advisor} vào thời gian người dùng yêu cầu: {user_query}"
                )
                continue

            # Không đặt lịch nếu sinh viên không tồn tại, hoặc đã hoàn tất tool cuối.
            print(f"🧠 [Thought]: Đã nhận được dữ liệu từ MCP Server. Tổng hợp kết quả phản hồi.")
            print(f"🏁 [Final Answer]: {final_answer}")
            
            trace_logs.append({
                "step": step + 1,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": "Tổng hợp kết quả từ MCP Server thành công.",
                "output": final_answer,
                "latency_ms": 10.0
            })
            return trace_logs

    final_answer = _build_final_answer(observations) if observations else (
        "Không thể hoàn thành yêu cầu trong số vòng lặp tối đa."
    )
    trace_logs.append({
        "step": step + 1,
        "query": user_query,
        "action_type": "MAX_ITERATIONS_REACHED",
        "thought": "Dừng tác tử để tránh vòng lặp vô hạn.",
        "output": final_answer,
        "latency_ms": 0.0
    })
    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPAcademicServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Quy chế học vụ VinUni yêu cầu bao nhiêu tín chỉ?'")
        print("   - Tra cứu học vụ: 'Hãy tra cứu thông tin học vụ của sinh viên SV2026001'")
        print("   - Đặt lịch hẹn: 'Đặt lịch hẹn tư vấn cho SV2026001 vào 14:00 ngày 15/09/2026'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Sinh viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for test_index, tc in enumerate(tests):
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1

                # Tránh gửi nhiều request liên tiếp vượt rate limit của LLM API.
                if test_index < len(tests) - 1:
                    delay_seconds = float(os.getenv("LLM_TEST_DELAY_SECONDS", "15"))
                    if delay_seconds > 0:
                        print(f"⏳ Chờ {delay_seconds:g} giây trước Test Case tiếp theo để tránh lỗi 429...")
                        time.sleep(delay_seconds)
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu học vụ) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
