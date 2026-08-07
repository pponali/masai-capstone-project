# Assignment Submission: Zepto Support Assistant Module

Name: Support Assistant RAG Pipeline Implementation  
Module: Masai Capstone Project  

---

## 1. RAG Pipeline Architecture & Execution Flow

### Stage 1: Document Ingestion
- **File & Function**: Handled in `ingest.py` during the initial file loading loop (`os.walk("docs")`).
- **Description**: The script reads raw `.txt` files (`doc_01.txt` through `doc_08.txt`) from the `docs/` corpus directory and attaches metadata containing the source filename (`{"source": file}`).

### Stage 2: Vector Embedding & Storage
- **Components**: `SentenceTransformer("all-MiniLM-L6-v2")` and `chromadb.PersistentClient`.
- **Description**: Document texts are converted into 384-dimensional dense vector embeddings using `model.encode()`. The vectors, original document texts, metadata, and string IDs (`1` to `N`) are saved in a persistent ChromaDB collection named `support_documents` at `./chroma_db`.

### Stage 3: Intent Classification & Routing
- **Components**: LangGraph node `classify_intent` and router edge function `route_intent`.
- **Description**: The incoming query is classified as either a `policy_question` or a `general_question`. The `route_intent` conditional edge inspects `state["intent"]` and routes `policy_question` queries to the `retrieve_and_answer` node and `general_question` queries to the `direct_answer` node.

### Stage 4: Document Retrieval
- **Component**: LangGraph node `retrieve_and_answer` in `ingest.py`.
- **Description**: The user query is embedded using `model.encode()` and queried against ChromaDB (`collection.query(..., n_results=3)`). Cosine similarity search retrieves the top 3 relevant document chunks along with source metadata (`doc_05.txt`, etc.). Retrieval always runs for real in both Mock Mode and Real-LLM Mode.

### Stage 5: Answer Generation & Schema Output
- **Components**: `retrieve_and_answer` and `direct_answer` nodes using `PROMPT_TEMPLATE`.
- **Description**: The node constructs the final output and enforces the `FinalAnswerSchema` format (`answer`, `sources`, `confidence`).

---

## MOCK_LLM Toggle & Branching Behavior

- **Mock Mode (`MOCK_LLM` unset or `1` — Required Graded Baseline)**:
  - `classify_intent`: Uses a keyword heuristic (`"delivery"`, `"return"`, `"refund"`, `"membership"`, `"tracking"`, `"cancel"`, `"gift card"`, `"support hours"`). No LLM call is made.
  - `retrieve_and_answer`: Returns a deterministic answer of the form `f"Based on the retrieved context: {top_chunk_snippet}"` using the first ~200 characters of the top chunk. `sources` is populated with the retrieved file names (`["doc_05.txt", ...]`) and `confidence` is `1.0`.
  - `direct_answer`: Returns a fixed canned response `"I can only answer questions about Zepto policies right now."` with `sources = []` and `confidence = 1.0`.

- **Real-LLM Mode (`MOCK_LLM=0` — Extension)**:
  - `classify_intent`: Calls Groq LLM (`llama3-8b-8192`) to dynamically classify the question.
  - `retrieve_and_answer`: Prompts Groq LLM using `PROMPT_TEMPLATE` with context. Parses JSON and validates against `FinalAnswerSchema`. If validation fails, retries up to 2 additional times with corrective instructions before returning an error response.
  - `direct_answer`: Prompts Groq LLM directly without retrieval context and validates schema output with retries.

---

## 2. Python Code Implementation

### `models.py`
```python
from pydantic import BaseModel, Field
from typing import List

class FinalAnswerSchema(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    intent: str
    retrieved_docs: List[str]
    answer: FinalAnswerSchema
```

### `app.py`
```python
from fastapi import FastAPI
from models import QueryRequest, QueryResponse, FinalAnswerSchema
from ingest import graph, State

app = FastAPI(title="Zepto Customer Support AI Assistant API")

@app.post("/ask", response_model=QueryResponse)
def ask_question(request: QueryRequest) -> QueryResponse:
    initial_state: State = {
        "query": request.query,
        "intent": "general_question",
        "retrieved_docs": [],
        "answer": {}
    }
    result = graph.invoke(initial_state)
    
    answer_raw = result.get("answer", {})
    if isinstance(answer_raw, dict):
        final_answer = FinalAnswerSchema(**answer_raw)
    else:
        final_answer = FinalAnswerSchema(answer=str(answer_raw), sources=[], confidence=1.0)

    return QueryResponse(
        query=result["query"],
        intent=result["intent"],
        retrieved_docs=result.get("retrieved_docs", []),
        answer=final_answer
    )
```

---

## 3. Recorded API Endpoint Outputs

Tested on locally running server (`http://127.0.0.1:8000/ask`) with default `MOCK_LLM=1`.

### Example 1: Retrieval Triggered (`policy_question`)

**Request**:
```bash
curl -s -X POST "http://127.0.0.1:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"query": "How to cancel my order?"}'
```

**Raw JSON Output**:
```json
{
  "query": "How to cancel my order?",
  "intent": "policy_question",
  "retrieved_docs": [
    "Order Cancellation Policy: \"Orders can be cancelled free of cost any time before the order status changes to 'Packed', typically within the first 2 minutes of placing the order. Once an order has been packed, it can no longer be cancelled through the app, since the rider is dispatched immediately after packing given Zepto's quick-delivery model. If a packed order cannot be delivered due to a Zepto-side issue (for example, rider unavailability), the order is auto-cancelled and fully refunded without any cancellation fee.\"",
    "Damaged or Missing Items: \"If an order arrives with damaged, spoiled, or missing items, customers must report it within 24 hours of delivery through the 'Report an Issue' button on the order page. Zepto ships a free replacement or issues a full refund for damaged, spoiled, or missing items without requiring the customer to return the original item, unless the order value exceeds INR 1000, in which case a photo of the issue must be submitted through the report form before a replacement or refund is processed.\"",
    "Returns & Refunds: \"Grocery and perishable items may be reported for a return within 24 hours of delivery if damaged, spoiled, or incorrect; non-perishable packaged items may be returned within 7 days of delivery in unopened, resalable condition. Approved refunds are credited to the original payment method within 3–5 business days, or instantly to the Zepto wallet if the customer opts for wallet credit. Personal care items that have been opened are non-returnable except in the case of a manufacturing defect. Return pickup, where required, is arranged free of cost by Zepto.\""
  ],
  "answer": {
    "answer": "Based on the retrieved context: Order Cancellation Policy: \"Orders can be cancelled free of cost any time before the order status changes to 'Packed', typically within the first 2 minutes of placing the order. Once an order has been",
    "sources": [
      "doc_05.txt",
      "doc_06.txt",
      "doc_02.txt"
    ],
    "confidence": 1.0
  }
}
```

---

### Example 2: Retrieval NOT Triggered (`general_question`)

**Request**:
```bash
curl -s -X POST "http://127.0.0.1:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the capital of France?"}'
```

**Raw JSON Output**:
```json
{
  "query": "What is the capital of France?",
  "intent": "general_question",
  "retrieved_docs": [],
  "answer": {
    "answer": "I can only answer questions about Zepto policies right now.",
    "sources": [],
    "confidence": 1.0
  }
}
```

---

## 4. Containerization (Dockerfile)

### `Dockerfile`
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

### Build & Run Commands
```bash
docker build -t support-assistant .
docker run -p 7860:7860 support-assistant
```

---

## 5. Hugging Face Spaces Deployment Notes (Optional Extension)
- **Deployment SDK**: Docker
- **Tier**: Free Community CPU Tier (no payment required)
- **Port**: `7860`
- **Secrets Management**: The LLM API key (`GROQ_API_KEY`) is stored as a Space secret under Settings -> Repository Secrets and is never hardcoded.
