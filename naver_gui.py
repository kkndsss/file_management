import tkinter as tk
from tkinter import scrolledtext
from llama_cpp import Llama
import threading
import sys
import os

def get_resource_path(relative_path):
    """PyInstaller로 패키징된 경우 올바른 경로 반환"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SimpleLLMChat:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("로컬 LLM 챗봇")
        self.window.geometry("800x600")
        
        self.llm = None
        self.conversation_history = []
        self.is_generating = False
        
        self.setup_ui()
        self.load_model()
        
    def setup_ui(self):
        # 시스템 기본 폰트 사용 (가장 호환성 좋음)
        default_font = ("", 11)  # 빈 문자열 = 시스템 기본 폰트
        
        # 채팅 영역
        self.chat_display = scrolledtext.ScrolledText(
            self.window,
            wrap=tk.WORD,
            width=80,
            height=30,
            font=default_font,
            state=tk.DISABLED
        )
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 입력 영역
        input_frame = tk.Frame(self.window)
        input_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        
        self.input_box = tk.Text(
            input_frame,
            height=3,
            font=default_font,
            wrap=tk.WORD
        )
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_box.focus_set()
        
        # Enter = 전송, Shift+Enter = 줄바꿈
        self.input_box.bind("<Return>", self.send_message_event)
        
        # 버튼 영역
        button_frame = tk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.send_btn = tk.Button(
            button_frame,
            text="전송",
            command=self.send_message,
            width=8,
            height=3,
            font=("", 10)
        )
        self.send_btn.pack()
        
        # 하단 버튼
        bottom_frame = tk.Frame(self.window)
        bottom_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        
        self.clear_btn = tk.Button(
            bottom_frame,
            text="대화 초기화",
            command=self.clear_conversation,
            font=("", 9)
        )
        self.clear_btn.pack(side=tk.LEFT)
        
        self.status_label = tk.Label(
            bottom_frame,
            text="모델 로딩 중...",
            fg="gray",
            font=("", 9)
        )
        self.status_label.pack(side=tk.RIGHT)
        
    def load_model(self):
        def load():
            try:
                self.update_status("모델 로딩 중...")
                
                # 여러 경로 시도
                script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
                
                possible_paths = [
                    get_resource_path("model.gguf"),  # exe에 내장된 경우
                    os.path.join(script_dir, "model.gguf"),  # 스크립트와 같은 폴더
                    os.path.join(script_dir, "HyperCLOVAX-SEED-Text-Instruct-0.5B-Q4_K_M.gguf"),  # 원본명
                    "model.gguf",  # 실행 경로
                    r"C:\local_lm\model.gguf",
                    r"C:\local_lm\HyperCLOVAX-SEED-Text-Instruct-0.5B-Q4_K_M.gguf",  # 원본
                    "/home/kknd/local_lm/model.gguf",
                    "/home/kknd/local_lm/HyperCLOVAX-SEED-Text-Instruct-0.5B-Q4_K_M.gguf",
                ]
                
                model_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        model_path = path
                        break
                
                if model_path is None:
                    raise FileNotFoundError("gguf 파일을 찾을 수 없습니다. model.gguf 파일을 스크립트와 같은 폴더에 넣어주세요.")
                
                self.llm = Llama(
                    model_path=model_path,
                    n_ctx=4096,
                    n_threads=4
                )
                self.update_status("준비 완료")
                self.add_message("system", f"모델 로드 완료: {os.path.basename(model_path)}")
            except Exception as e:
                self.update_status(f"로딩 실패: {str(e)}")
                self.add_message("system", f"오류: {str(e)}")
        
        threading.Thread(target=load, daemon=True).start()
    
    def update_status(self, message):
        self.status_label.config(text=message)
    
    def add_message(self, role, content):
        self.chat_display.config(state=tk.NORMAL)
        
        if role == "user":
            self.chat_display.insert(tk.END, f"\n[사용자]\n{content}\n", "user")
        elif role == "assistant":
            self.chat_display.insert(tk.END, f"\n[어시스턴트]\n{content}\n", "assistant")
        elif role == "system":
            self.chat_display.insert(tk.END, f"\n>>> {content}\n", "system")
        
        self.chat_display.tag_config("user", foreground="blue")
        self.chat_display.tag_config("assistant", foreground="green")
        self.chat_display.tag_config("system", foreground="orange")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def send_message_event(self, event):
        # Shift+Enter는 줄바꿈
        if event.state & 0x1:
            return None
        self.send_message()
        return "break"
    
    def send_message(self):
        if self.is_generating or self.llm is None:
            return
        
        user_input = self.input_box.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        self.input_box.delete("1.0", tk.END)
        self.add_message("user", user_input)
        self.conversation_history.append({"role": "user", "content": user_input})
        
        threading.Thread(target=self.generate_response, daemon=True).start()
    
    def generate_response(self):
        self.is_generating = True
        self.update_status("생성 중...")
        self.send_btn.config(state=tk.DISABLED)
        
        try:
            prompt = self.build_prompt()
            response = self.llm(
                prompt,
                max_tokens=4096,
                temperature=0.7,
                top_p=0.9,
                repeat_penalty=1.1,
                stop=["사용자:", "\n사용자:", "User:", "\nUser:"]
            )
            
            assistant_response = response["choices"][0]["text"].strip()
            
            # 혹시 "사용자:"가 포함되어 있으면 그 전까지만 사용
            if "사용자:" in assistant_response:
                assistant_response = assistant_response.split("사용자:")[0].strip()
            
            self.add_message("assistant", assistant_response)
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            self.update_status("준비 완료")
        except Exception as e:
            self.add_message("system", f"오류: {str(e)}")
            self.update_status("오류 발생")
        finally:
            self.is_generating = False
            self.send_btn.config(state=tk.NORMAL)
            self.input_box.focus_set()
    
    def build_prompt(self):
        """대화 히스토리를 포함한 프롬프트 구성"""
        # 시스템 프롬프트로 역할 명확히 지시
        prompt = """당신은 친절하고 정확한 AI 어시스턴트입니다. 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.

"""
        
        # 대화 히스토리
        for msg in self.conversation_history:
            if msg["role"] == "user":
                prompt += f"사용자: {msg['content']}\n"
            else:
                prompt += f"어시스턴트: {msg['content']}\n"
        
        prompt += "어시스턴트:"
        return prompt
    
    def clear_conversation(self):
        self.conversation_history = []
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.add_message("system", "대화가 초기화되었습니다.")
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = SimpleLLMChat()
    app.run()