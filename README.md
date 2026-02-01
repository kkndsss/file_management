
# 🤖 Local LLM Chatbot (Tkinter)
# naver_gui.py

`llama-cpp-python`과 `Tkinter`를 활용하여 만든 **오프라인 로컬 LLM 챗봇**입니다. 인터넷 연결 없이 내 PC의 자원만으로 AI와 대화할 수 있습니다.

## ✨ 주요 기능

* **로컬 추론:** GGUF 포맷의 모델을 사용하여 개인정보 유출 걱정 없는 로컬 대화 가능
* **간결한 UI:** Tkinter 기반의 가볍고 직관적인 채팅 인터페이스
* **멀티 스레딩:** 모델 로딩 및 답변 생성 중에도 GUI가 멈추지 않음
* **대화 맥락 유지:** 이전 대화 내용을 기억하여 자연스러운 문답 지원
* **사용자 편의:** `Enter`로 전송, `Shift + Enter`로 줄바꿈 지원 및 대화 초기화 기능

## 🛠 준비 사항

1. **Python 3.8+** 설치
2. **필수 라이브러리 설치:**
```bash
pip install llama-cpp-python

```


3. **모델 파일:** `model.gguf` 파일이 프로젝트 루트 폴더 혹은 `C:\local_lm\` 경로에 있어야 합니다.
> 기본적으로 **HyperCLOVAX-SEED-Text-Instruct-0.5B** 등의 GGUF 모델을 탐색합니다.



## 🚀 실행 방법

```bash
python your_script_name.py

```

## 📂 파일 구조 및 모델 경로

프로그램 실행 시 아래 순서대로 모델 파일을 탐색합니다:

1. 실행 파일 내장 경로 (PyInstaller 패키징 시)
2. 스크립트와 동일한 폴더 (`model.gguf`)
3. `C:\local_lm\model.gguf` (Windows 기준)

---

### 💡 팁

* 모델 파일명을 `model.gguf`로 변경하면 별도의 코드 수정 없이 바로 인식됩니다.
* 저사양 PC라면 0.5B ~ 3B 사이의 경량화된 모델 사용을 권장합니다.

---

**이 프로젝트의 실행 파일(EXE) 빌드를 도와드릴까요? 아니면 코드의 특정 기능을 수정하고 싶으신가요?**
