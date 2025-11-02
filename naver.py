from llama_cpp import Llama

llm = Llama(model_path="C:\local_lm\hyperclovax-seed-text-instruct-1.5b-q4_k_m.gguf")
response = llm(input(), max_tokens=4096)
print(response["choices"][0]["text"])