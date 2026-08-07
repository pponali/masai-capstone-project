import os
from typing import TypedDict, Literal, Union
from sentence_transformers import SentenceTransformer
import chromadb
from groq import Groq
from langgraph.graph import StateGraph, START, END
from models import FinalAnswerSchema

# Initialize SentenceTransformer model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize ChromaDB persistent client
client = chromadb.PersistentClient(path="./chroma_db")
try:
    client.delete_collection("support_documents")
except Exception:
    pass

collection = client.get_or_create_collection("support_documents")

# Ingest documents from docs directory
i = 0
for root, dirs, files in os.walk("docs"):
    for file in files:
        if file.endswith(".txt"):
            file_path = os.path.join(root, file)
            print(f" File path : {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                embeddings = model.encode(content)
                collection.add(
                    embeddings=[embeddings.tolist()],
                    documents=[content],
                    metadatas=[{"source": file}],
                    ids=[str(i + 1)]
                )
                i += 1

for metadata, document in zip(
    collection.get(include=['metadatas'])['metadatas'],
    collection.get(include=['documents'])['documents']
):
    print(f" Metadata : {metadata}, Document : {document}")


# Task 2: Structured Prompt Template
PROMPT_TEMPLATE = """
ROLES: You are a Zepto customer support AI assistant. Your job is to answer customer questions about delivery times, refunds, membership, and other standard policies based strictly on the provided documents. When information is unavailable, you must decline to answer rather than guessing or hallucinating.
CONTEXT: Here are the retrieved documents: {retrieved_documents}  
TASK: Answer the user's question using only the information in the support documents. Do not use any outside knowledge. If the documents do not contain enough information to answer the question, respond with: "I cannot answer this question using the available documents."
FORMAT: Return only your final answer. Do not include metadata like document titles or confidence scores unless explicitly asked.
LENGTH: Keep your response concise, ideally 2–4 sentences.

FEW-SHOT EXAMPLES:
User: Can I order a pizza from Zepto?
Response: I cannot answer this question using the available documents.

User: How long do I have to report a damaged item?
Response: You must report damaged or spoiled items within 24 hours of delivery. Items returned must be unused and in resalable condition, with the exception of items with manufacturing defects. Refunds are processed within 3–5 business days or instantly to your Zepto wallet.

USER QUESTION: {query}
"""


class State(TypedDict):
    query: str
    intent: Literal["policy_question", "general_question"]
    retrieved_docs: list[str]
    answer: Union[dict, str]


def classify_intent(state: State) -> dict:
    mock_llm = os.getenv("MOCK_LLM", "1")
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")

    if mock_llm == "0" and api_key:
        # Optional MOCK_LLM=0 extension: call LLM to classify
        llm = Groq(api_key=api_key)
        prompt = (
            f"Classify the following customer query into exactly one category: 'policy_question' or 'general_question'.\n"
            f"Query: {state['query']}\n"
            f"Return only 'policy_question' or 'general_question'."
        )
        response = llm.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        res_str = response.choices[0].message.content.strip().lower()
        intent = "policy_question" if "policy" in res_str else "general_question"
    else:
        # Mock mode (MOCK_LLM unset or 1 - graded baseline): keyword heuristic
        policy_keywords = [
            "delivery", "return", "refund", "membership",
            "tracking", "cancel", "gift card", "support hours"
        ]
        query_lower = state["query"].lower()
        if any(keyword in query_lower for keyword in policy_keywords):
            intent = "policy_question"
        else:
            intent = "general_question"
    
    print(f"[classify_intent] Query: '{state['query']}' -> Classified as: '{intent}'")
    return {"intent": intent}


def route_intent(state: State) -> Literal["retrieve_and_answer", "direct_answer"]:
    current_intent = state.get("intent")
    print(f"[route_intent] Routing based on intent: '{current_intent}'")
    if current_intent in ["policy_question", "policy"]:
        return "retrieve_and_answer"
    return "direct_answer"


def retrieve_and_answer(state: State) -> dict:
    print("[retrieve_and_answer] Executing vector search and retrieval...")
    embeddings = model.encode(state["query"])
    retrieved_docs = collection.query(
        query_embeddings=[embeddings.tolist()],
        n_results=3,
        include=['documents', 'metadatas']
    )
    docs = retrieved_docs.get("documents", [[]])[0]
    ids = retrieved_docs.get("ids", [[]])[0]
    metadatas = retrieved_docs.get("metadatas", [[]])[0]
    
    source_ids = [meta.get("source", doc_id) for meta, doc_id in zip(metadatas, ids)] if metadatas else ids

    mock_llm = os.getenv("MOCK_LLM", "1")
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")

    if mock_llm == "0" and api_key:
        answer_data = invoke_llm_with_retry(state["query"], docs, source_ids)
    else:
        top_snippet = docs[0][:200] if docs else "No document content found."
        answer_obj = FinalAnswerSchema(
            answer=f"Based on the retrieved context: {top_snippet}",
            sources=source_ids,
            confidence=1.0
        )
        answer_data = answer_obj.model_dump()
    
    return {"retrieved_docs": docs, "answer": answer_data}


def direct_answer(state: State) -> dict:
    print("[direct_answer] Executing direct answer...")
    mock_llm = os.getenv("MOCK_LLM", "1")
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")

    if mock_llm == "0" and api_key:
        answer_data = invoke_llm_direct_with_retry(state["query"])
    else:
        answer_obj = FinalAnswerSchema(
            answer="I can only answer questions about Zepto policies right now.",
            sources=[],
            confidence=1.0
        )
        answer_data = answer_obj.model_dump()

    return {"answer": answer_data}


def invoke_llm_with_retry(query: str, docs: list[str], source_ids: list[str]) -> dict:
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        return FinalAnswerSchema(
            answer="I cannot answer this question using the available documents.",
            sources=[],
            confidence=0.0
        ).model_dump()
    
    llm = Groq(api_key=api_key)
    retrieved_str = "\n".join(docs)
    base_prompt = PROMPT_TEMPLATE.format(
        retrieved_documents=retrieved_str,
        query=query
    ) + "\n\nRespond strictly in valid JSON matching this schema: {\"answer\": string, \"sources\": list of strings, \"confidence\": float between 0 and 1}."

    messages = [
        {"role": "system", "content": "You are a helpful Zepto customer support AI assistant. Output valid JSON only."},
        {"role": "user", "content": base_prompt}
    ]

    last_error = ""
    for attempt in range(3):  # Initial attempt + up to 2 retries
        try:
            response = llm.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content
            validated = FinalAnswerSchema.model_validate_json(raw_content)
            return validated.model_dump()
        except Exception as e:
            last_error = str(e)
            print(f"[invoke_llm_with_retry] Attempt {attempt + 1} validation failed: {last_error}")
            messages.append({"role": "assistant", "content": raw_content if 'raw_content' in locals() else ""})
            messages.append({"role": "user", "content": f"Corrective Instruction: Output failed validation ({last_error}). Return strictly valid JSON with keys 'answer' (string), 'sources' (list of strings), and 'confidence' (float between 0 and 1)."})

    return FinalAnswerSchema(
        answer=f"Error: Failed to generate valid JSON response after retries ({last_error})",
        sources=[],
        confidence=0.0
    ).model_dump()


def invoke_llm_direct_with_retry(query: str) -> dict:
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        return FinalAnswerSchema(
            answer="I can only answer questions about Zepto policies right now.",
            sources=[],
            confidence=0.0
        ).model_dump()

    llm = Groq(api_key=api_key)
    messages = [
        {"role": "system", "content": "You are a helpful customer support AI assistant. Output valid JSON with keys 'answer' (str), 'sources' (list), 'confidence' (float)."},
        {"role": "user", "content": f"Query: {query}\nOutput strictly valid JSON with keys 'answer', 'sources' (empty list), and 'confidence' (float 0-1)."}
    ]

    last_error = ""
    for attempt in range(3):
        try:
            response = llm.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content
            validated = FinalAnswerSchema.model_validate_json(raw_content)
            return validated.model_dump()
        except Exception as e:
            last_error = str(e)
            print(f"[invoke_llm_direct_with_retry] Attempt {attempt + 1} validation failed: {last_error}")
            messages.append({"role": "assistant", "content": raw_content if 'raw_content' in locals() else ""})
            messages.append({"role": "user", "content": f"Corrective Instruction: Output failed validation ({last_error}). Return strictly valid JSON with keys 'answer' (string), 'sources' (list), and 'confidence' (float)."})

    return FinalAnswerSchema(
        answer=f"Error: Failed to generate valid JSON response after retries ({last_error})",
        sources=[],
        confidence=0.0
    ).model_dump()


# Build LangGraph StateGraph
graph_builder = StateGraph(State)
graph_builder.add_node("classify_intent", classify_intent)
graph_builder.add_node("retrieve_and_answer", retrieve_and_answer)
graph_builder.add_node("direct_answer", direct_answer)

graph_builder.add_edge(START, "classify_intent")
graph_builder.add_conditional_edges(
    "classify_intent",
    route_intent,
    {
        "retrieve_and_answer": "retrieve_and_answer",
        "direct_answer": "direct_answer"
    }
)
graph_builder.add_edge("retrieve_and_answer", END)
graph_builder.add_edge("direct_answer", END)

graph = graph_builder.compile()


if __name__ == "__main__":
    initial_state: State = {
        "query": "How to cancel my order?",
        "intent": "general_question",
        "retrieved_docs": [],
        "answer": ""
    }
    res = graph.invoke(initial_state)
    print("\nFinal Result Answer:\n", res.get("answer"))