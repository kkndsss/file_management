import os, json, shutil
import tkinter as tk
from tkinter import messagebox
from llama_cpp import Llama

# ===== 0. 기본 설정 =====
MODEL_PATH = "hyperclovax-seed-text-instruct-1.5b-q4_k_m.gguf"  # 네 경로로 바꿔
TEST_ROOT = os.path.abspath("./filetalk_test")
os.makedirs(TEST_ROOT, exist_ok=True)

# ===== 1. LLM 로드 =====
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_threads=8,
)

TOOL_MAP = {
    "1": "create_folder",
    "2": "create_file",
    "3": "move_file",
}

# ===== 2. LLM에게 툴만 고르게 =====
def llm_pick_tool(user_text: str) -> str:
    prompt = f"""너는 로컬 파일관리 전용 LLM이다.
아래 사용자 요청을 보고 **번호 하나만** 골라라.

1. 폴더 만들기 (예: 폴더 만들어줘, 디렉토리 생성)
2. 파일 만들기 (예: txt 만들어, 빈 파일 만들기)
3. 파일/폴더 이동 (예: a.txt를 down으로 옮겨)

다른 글자, 설명, 따옴표 없이 번호만.
요청: {user_text}
번호:"""
    out = llm(prompt, max_tokens=8, temperature=0.1)
    num = out["choices"][0]["text"].strip()
    return TOOL_MAP.get(num, "unknown")

# ===== 3. LLM에게 arguments만 고르게 =====
def llm_make_args(user_text: str, tool: str) -> dict:
    if tool == "create_folder":
        schema = '{"name": "폴더이름"}'
    elif tool == "create_file":
        schema = '{"path": "파일이름.txt", "content": ""}'
    else:  # move_file
        schema = '{"src": "원본파일", "dst": "목적지", "dry_run": true}'

    prompt = f"""너는 파일관리 LLM이다.
아래 요청을 {tool} 툴의 arguments로만 JSON 형식으로 써라.
출력은 반드시 이 예시의 키만 사용한다.
예시: {schema}
설명, 말줄임, 코드블록 모두 금지.

요청: {user_text}
JSON:"""
    out = llm(prompt, max_tokens=256, temperature=0.1)
    txt = out["choices"][0]["text"].strip()
    txt = txt.replace("```json", "").replace("```", "").strip()
    try:
        args = json.loads(txt)
    except Exception:
        args = {}
    return args

# ===== 4. 실행기 =====
def under_root(p: str) -> str:
    # 모델이 이상한 경로 줘도 파일명만 써서 TEST_ROOT 밑으로
    name = os.path.basename(p)
    return os.path.join(TEST_ROOT, name)

def run_cmd(cmd: dict) -> str:
    tool = cmd.get("tool")
    args = cmd.get("arguments", {})

    if tool == "create_folder":
        name = args.get("name", "new_folder")
        path = os.path.join(TEST_ROOT, name)
        os.makedirs(path, exist_ok=True)
        return f"폴더 생성: {path}"

    if tool == "create_file":
        raw = args.get("path", "new.txt")
        path = under_root(raw)
        content = args.get("content", "")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"파일 생성: {path}"

    if tool == "move_file":
        src = under_root(args.get("src", ""))
        dst = under_root(args.get("dst", ""))
        dry = args.get("dry_run", True)
        if dry:
            return f"[DRY RUN] {src} -> {dst}"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(src):
            return f"소스 파일 없음: {src}"
        shutil.move(src, dst)
        return f"이동 완료: {src} -> {dst}"

    return "지원하지 않는 tool"

# ===== 5. UI =====
root = tk.Tk()
root.title("Filetalk PoC (3툴)")
tk.Label(root, text=f"테스트 폴더: {TEST_ROOT}").pack(padx=10, pady=5)

entry = tk.Entry(root, width=70)
entry.pack(padx=10, pady=10)

text = tk.Text(root, height=12, width=70)
text.pack(padx=10, pady=5)

state = {"cmd": None}

def on_parse():
    user = entry.get().strip()
    if not user:
        return
    tool = llm_pick_tool(user)
    args = llm_make_args(user, tool) if tool != "unknown" else {}
    # TEST_ROOT 강제 주입
    if tool == "create_file" and "path" in args:
        args["path"] = under_root(args["path"])
    if tool == "move_file":
        if "src" in args:
            args["src"] = under_root(args["src"])
        if "dst" in args:
            args["dst"] = under_root(args["dst"])
    cmd = {"tool": tool, "arguments": args}
    state["cmd"] = cmd
    text.delete("1.0", tk.END)
    text.insert(tk.END, json.dumps(cmd, ensure_ascii=False, indent=2))

def on_exec():
    cmd = state.get("cmd")
    if not cmd:
        messagebox.showinfo("알림", "먼저 해석하세요.")
        return
    res = run_cmd(cmd)
    messagebox.showinfo("결과", res)

btns = tk.Frame(root); btns.pack(pady=5)
tk.Button(btns, text="명령 해석하기", command=on_parse).pack(side=tk.LEFT, padx=5)
tk.Button(btns, text="실제로 실행", command=on_exec).pack(side=tk.LEFT, padx=5)

root.mainloop()
