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
