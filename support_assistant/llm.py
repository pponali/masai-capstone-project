


from groq import groq
import os 
def invoke(query:str):
    if os.getenv("MOCK_LLM") == 1:
        return "Hello, how are you?"
    else:
        API_KEY = os.getenv("GROK_API_KEY")
    llm = groq(api_key=API_KEY)
    return llm.invoke(query)

print(invoke())
