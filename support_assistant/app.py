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
