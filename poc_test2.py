import os
import json
import shutil
import tkinter as tk
from tkinter import messagebox
from llama_cpp import Llama

# =========================
# 설정
# =========================
MODEL_PATH = "hyperclovax-seed-text-instruct-1.5b-q4_k_m.gguf"  # 너 모델 경로로 바꿔
ROOT_DIR = os.path.abspath("./filetalk_root")
os.makedirs(ROOT_DIR, exist_ok=True)

# =========================
# LLM 로드
# =========================
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_threads=8,
)

# =========================
# 프롬프트 (한 방)
# =========================
SYSTEM_PROMPT = """너는 Filetalk용 파일관리 LLM이다.
아래 사용자 요청을 보고 딱 1개의 JSON만 출력한다.

형식:
{
  "tool": "<search_files|summarize_file|create_folder|create_file|move_file>",
  "arguments": { ... }
}

규칙:
- 위 5개 tool만 쓴다. 다른 이름 쓰면 안 된다.
- 경로를 직접 쓰지 말고 가능하면 파일명/폴더명만 써라.
- 경로가 필요하면 "./filetalk_root" 로 시작하게 해라.
- 설명, 말줄임표(...), 코드블록 없이 JSON만 출력한다.
- "찾아줘", "어디", "검색", "목록", "확장자" → search_files
- "요약" → summarize_file
- "폴더" → create_folder
- "파일 만들어", "txt", "생성" → create_file
- "옮겨", "이동", "보내" → move_file

예시)
사용자: 기본 폴더에 down 폴더 만들어줘
→
{
  "tool": "create_folder",
  "arguments": { "name": "down" }
}
"""

ALLOWED_TOOLS = {
    "search_files",
    "summarize_file",
    "create_folder",
    "create_file",
    "move_file",
}

# =========================
# 유틸
# =========================
def to_root_path(name: str) -> str:
    name = os.path.basename(name)
    return os.path.join(ROOT_DIR, name)

# =========================
# LLM → JSON → 보정
# =========================
def llm_parse(user_text: str) -> dict:
    prompt = SYSTEM_PROMPT + "\n사용자: " + user_text + "\n답변:\n"
    out = llm(prompt, max_tokens=256, temperature=0.1, stop=["사용자:"])
    text = out["choices"][0]["text"].strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        cmd = json.loads(text)
    except Exception:
        # 한 번 더 시도
        out2 = llm(prompt + "JSON 형식으로 다시:\n", max_tokens=256, temperature=0.1)
        text2 = out2["choices"][0]["text"].strip().replace("```json", "").replace("```", "").strip()
        try:
            cmd = json.loads(text2)
        except Exception:
            cmd = {"tool": "create_file", "arguments": {"path": "./filetalk_root/new.txt", "content": ""}}

    return normalize_cmd(cmd)

def normalize_cmd(cmd: dict) -> dict:
    tool = cmd.get("tool", "unknown")
    args = cmd.get("arguments", {}) or {}

    # 0) source/destination → src/dst
    if "source" in args:
        args["src"] = args["source"]
    if "destination" in args:
        args["dst"] = args["destination"]

    # 1) 툴 이름 보정
    if tool not in ALLOWED_TOOLS:
        # 이동 힌트 있으면 이동
        if any(k in args for k in ("src", "dst", "source", "destination", "file", "folder")):
            tool = "move_file"
        else:
            tool = "create_file"

    # 2) tool별 보정
    if tool == "create_file":
        # name이 있으면 name이 이김
        if "name" in args and not args.get("path"):
            raw = args["name"]
        else:
            raw = args.get("path", "new.txt")
        raw = os.path.basename(raw)
        path = os.path.join(ROOT_DIR, raw)
        args = {
            "path": path,
            "content": args.get("content", "")
        }

    elif tool == "create_folder":
        name = args.get("name", "new_folder")
        name = os.path.basename(name)
        args = {"name": name}

    elif tool == "move_file":
        # 1) file/folder로 온 경우 (우리가 원하는 형태)
        file_name = args.get("file")
        folder_name = args.get("folder")
        if file_name and folder_name:
            src = os.path.join(ROOT_DIR, os.path.basename(file_name))
            dst_dir = os.path.join(ROOT_DIR, os.path.basename(folder_name))
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(file_name))
            args = {"src": src, "dst": dst, "dry_run": False}
        else:
            # 2) src/dst로 온 경우 → basename만
            src = os.path.basename(args.get("src", ""))
            dst = os.path.basename(args.get("dst", ""))
            src_path = os.path.join(ROOT_DIR, src)
            if dst:
                dst_dir = os.path.join(ROOT_DIR, dst)
                # 폴더 같으면 파일명 붙이기
                if not os.path.splitext(dst_dir)[1]:
                    dst_path = os.path.join(dst_dir, src)
                else:
                    dst_path = dst_dir
            else:
                dst_path = os.path.join(ROOT_DIR, src)
            args = {"src": src_path, "dst": dst_path, "dry_run": False}

    elif tool == "summarize_file":
        p = os.path.basename(args.get("path", "unknown.txt"))
        args = {"path": os.path.join(ROOT_DIR, p), "max_tokens": 200}

    elif tool == "search_files":
        kw = args.get("keywords", [])
        if isinstance(kw, str):
            kw = [kw]
        ext = args.get("ext", [])
        if isinstance(ext, str):
            ext = [ext]
        args = {
            "keywords": kw,
            "ext": ext,
            "top_k": int(args.get("top_k", 100))
        }

    cmd["tool"] = tool
    cmd["arguments"] = args
    return cmd

# =========================
# 실제 실행
# =========================
def run_cmd(cmd: dict) -> str:
    tool = cmd["tool"]
    args = cmd["arguments"]

    if tool == "create_folder":
        path = os.path.join(ROOT_DIR, args["name"])
        os.makedirs(path, exist_ok=True)
        return f"폴더 생성: {path}"

    if tool == "create_file":
        path = args["path"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(args.get("content", ""))
        return f"파일 생성: {path}"

    if tool == "move_file":
        src = args["src"]
        dst = args["dst"]
        dry = args.get("dry_run", False)
        if dry:
            return f"[DRY RUN] {src} -> {dst}"
        if not os.path.exists(src):
            return f"소스 없음: {src}"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        return f"이동 완료: {src} -> {dst}"

    if tool == "search_files":
        keywords = args.get("keywords", [])
        exts = args.get("ext", [])
        top_k = args.get("top_k", 100)
        results = []
        for root, _, files in os.walk(ROOT_DIR):
            for fn in files:
                fpath = os.path.join(root, fn)
                # 이름 필터
                name_ok = all(kw in fn for kw in keywords) if keywords else True
                # 확장자 필터
                if exts:
                    ext_ok = any(fn.lower().endswith(e.lower()) for e in exts)
                else:
                    ext_ok = True
                if name_ok and ext_ok:
                    results.append(fpath)
                    if len(results) >= top_k:
                        break
        if not results:
            return "조회 결과 없음."
        return "조회 결과:\n" + "\n".join(results)

    if tool == "summarize_file":
        path = args["path"]
        if not os.path.exists(path):
            return f"요약 실패: 파일 없음 {path}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            text = "[텍스트가 아닌 파일]"
        preview = text[:200].replace("\n", " ")
        return f"요약(앞 200자): {preview}"

    return "지원하지 않는 tool"

# =========================
# UI
# =========================
root = tk.Tk()
root.title("Filetalk PoC")

tk.Label(root, text=f"관리 폴더: {ROOT_DIR}").pack(padx=10, pady=5)

entry = tk.Entry(root, width=70)
entry.pack(padx=10, pady=10)

text_box = tk.Text(root, width=80, height=15)
text_box.pack(padx=10, pady=5)

state = {"cmd": None}

def on_parse():
    user = entry.get().strip()
    if not user:
        return
    cmd = llm_parse(user)
    state["cmd"] = cmd
    text_box.delete("1.0", tk.END)
    text_box.insert(tk.END, json.dumps(cmd, ensure_ascii=False, indent=2))

def on_exec():
    cmd = state.get("cmd")
    if not cmd:
        messagebox.showinfo("알림", "먼저 LLM으로 해석하세요.")
        return
    res = run_cmd(cmd)
    messagebox.showinfo("결과", res)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=5)

tk.Button(btn_frame, text="LLM으로 해석", command=on_parse).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="명령 실행", command=on_exec).pack(side=tk.LEFT, padx=5)

root.mainloop()
