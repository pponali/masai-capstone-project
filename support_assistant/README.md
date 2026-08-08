# Module 3 - Support Assistant (RAG Pipeline)

This module builds a customer support assistant for Zepto, a quick commerce
grocery delivery service. The assistant answers policy questions such as how
long delivery takes, how refunds work, and how to cancel an order.

The important idea is that the assistant does not answer from general knowledge.
It answers from a fixed set of eight policy documents that live in this folder.
This approach is called RAG, which stands for Retrieval Augmented Generation.
The word retrieval means finding the right document first, and generation means
writing the answer afterwards using only what was found.

The pipeline has five stages and they always run in this order.

Ingest the documents, turn them into vectors and store them, classify what the
user is asking, retrieve the matching documents, and finally produce an answer
in a fixed JSON shape.

---

## Note - The Markdown Used in This File

Before the sections begin, a short note on how this document is written. Only two
pieces of markdown formatting are used, code blocks and tables.

Code blocks are written with the backtick character, which is the key above Tab
and to the left of the number 1. It is not the apostrophe or single quote.

Three backticks open the block, the language name goes right after them with no
space, and three backticks on their own line close it.

````
```python
class QueryRequest(BaseModel):
    query: str
```
````

That renders as this.

```python
class QueryRequest(BaseModel):
    query: str
```

| Rule | Detail |
| --- | --- |
| Opening line | Three backticks, then the language name, no space between them |
| Language names used in this README | python, bash, json, dockerfile |
| Closing line | Three backticks alone, nothing after them |
| If the language is left out | It still renders as code, only without colour highlighting |
| Spacing | Leave a blank line before the opening and after the closing line |

A table is made of pipe characters. The second row, the one made of dashes, is
required. It is what tells markdown these lines are a table and not plain text.

```
| Field | Type | Meaning |
| --- | --- | --- |
| answer | str | The reply text |
| confidence | float | Between 0 and 1 |
```

That renders as this.

| Field | Type | Meaning |
| --- | --- | --- |
| answer | str | The reply text |
| confidence | float | Between 0 and 1 |

| Rule | Detail |
| --- | --- |
| First row | The column headings |
| Second row | One set of three dashes per column, mandatory |
| Third row onward | The data rows |
| Column count | Every row needs the same number of pipe separators |
| Spacing | The pipes do not have to line up in the source file |

---

## Section 1 - Files in this Folder

| File or folder | What it is |
| --- | --- |
| ingest.py | The whole pipeline. Loads documents, builds the vector store, defines the LangGraph graph. |
| app.py | The FastAPI web server that exposes the pipeline as a POST /ask endpoint. |
| models.py | The Pydantic schemas that define the exact shape of the request and the response. |
| docs/ | The eight policy documents, doc_01.txt through doc_08.txt. |
| chroma_db/ | The ChromaDB vector store, created automatically when ingest.py runs. |
| Dockerfile | Builds a container image that runs the API on port 7860. |
| requirements.txt | The eight libraries the module depends on. |
| README.md | This file. |

---

## Section 2 - How to Run It

Step 1. Install the libraries.

```bash
pip install -r requirements.txt
```

The libraries and what each one is responsible for.

| Library | Its job in this pipeline |
| --- | --- |
| sentence-transformers | Turns text into a numeric vector using the all-MiniLM-L6-v2 model |
| chromadb | Stores those vectors on disk and searches them by similarity |
| langgraph | Builds the graph of nodes that decides what happens to a query |
| langchain-community | Supporting utilities for the LangChain ecosystem |
| groq | Client for the optional real LLM calls |
| fastapi | Defines the web API and the POST /ask endpoint |
| uvicorn | The web server that actually serves FastAPI |
| pydantic | Validates that every answer matches the required schema |

Step 2. Run the pipeline once on its own to check it works. This also builds the
vector store.

```bash
python ingest.py
```

Step 3. Start the API server.

```bash
uvicorn app:app --reload
```

The server then listens on http://127.0.0.1:8000 and the interactive docs page is
at http://127.0.0.1:8000/docs.

Note that ingest.py builds its paths from the location of the file itself, not
from the folder you happen to be standing in.

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
docs_dir = os.path.join(BASE_DIR, "docs")
chroma_dir = os.path.join(BASE_DIR, "chroma_db")
```

This is why the script can be started from any directory and still find its
documents. It is a deliberate difference from the data_pipeline module, which
uses relative paths and must be run from inside its own folder.

---

## Section 3 - The Document Corpus

Eight plain text files make up everything the assistant is allowed to know. Each
one covers a single policy area, and each is small, between 58 and 92 words.

| File | Topic | Words | Some facts it contains |
| --- | --- | --- | --- |
| doc_01.txt | Delivery Policy | 81 | 10 to 30 minute delivery, free over INR 149, INR 25 fee below that, INR 15 for priority |
| doc_02.txt | Returns and Refunds | 92 | 24 hours for perishables, 7 days for packaged goods, refunds in 3 to 5 business days |
| doc_03.txt | Membership Tiers | 87 | Basic free, Zepto Pass INR 49 a month, Zepto Pass+ INR 99 a month |
| doc_04.txt | Order Tracking | 67 | Live rider map, contact support after 20 minutes of no movement |
| doc_05.txt | Order Cancellation | 83 | Free cancellation before the order is packed, roughly the first 2 minutes |
| doc_06.txt | Damaged or Missing Items | 87 | Report within 24 hours, photo required above INR 1000 order value |
| doc_07.txt | Gift Cards | 86 | Denominations of 100, 250, 500, 1000, valid 1 year, not redeemable for cash |
| doc_08.txt | Customer Support Hours | 58 | In-app chat 24 by 7, under 2 minute response, no phone support |

Why the documents are this small matters. Each file is a single topic of under
100 words, which means one file fits comfortably inside a language model prompt
and does not need to be split into smaller chunks first. In a larger project with
long PDFs, a chunking step would sit between loading and embedding. Here the
natural size of the documents makes that step unnecessary, so one file equals one
stored vector.

---

## Section 4 - Stage 1, Document Ingestion

The script walks the docs folder and reads every file that ends in .txt.

```python
for root, dirs, files in os.walk(docs_dir):
    for file in files:
        if file.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                embeddings = model.encode(content)
                collection.add(
                    embeddings=[embeddings.tolist()],
                    documents=[content],
                    metadatas=[{"source": file}],
                    ids=[str(i + 1)]
                )
```

Four things are stored for every document.

| What is stored | Example value | Why it is needed |
| --- | --- | --- |
| embeddings | A list of 384 numbers | This is what similarity search actually compares |
| documents | The full original text | So the answer can quote the real wording, not the vector |
| metadatas | {"source": "doc_05.txt"} | So the answer can cite which file it came from |
| ids | "1" through "8" | A unique handle for each row in the collection |

The metadata is the piece that makes citation possible. A vector on its own is
384 numbers with no memory of where it came from. Attaching the filename means
the API response can list doc_05.txt as a source, which lets a human go and check
the claim against the real policy text.

Before ingesting, the script deletes any existing collection.

```python
try:
    client.delete_collection("support_documents")
except Exception:
    pass
```

This makes every run start from an empty store. Without it, running the script
twice would insert each document a second time and the retriever would return the
same policy repeatedly in its top three results. The try and except wrapper is
there because deleting a collection that does not exist raises an error, and on
the very first run it genuinely does not exist yet. This is the same reasoning as
the drop table statements in the data_pipeline module.

---

## Section 5 - Stage 2, Embedding and Vector Storage

An embedding is a way of turning text into numbers so that a computer can measure
whether two pieces of text mean similar things.

The model used is all-MiniLM-L6-v2.

| Property | Value |
| --- | --- |
| Model name | all-MiniLM-L6-v2 |
| Output size | 384 numbers per document |
| Runs on | The local CPU, no API call and no key needed |
| Cost | Free |
| Store | ChromaDB PersistentClient, saved in the chroma_db folder |
| Collection name | support_documents |
| Rows stored | 8, one per document |

The key property is that similar meanings produce similar vectors. The question
"How do I stop my order?" contains none of the words in the sentence "Orders can
be cancelled free of cost before the order status changes to Packed". A plain
keyword search would find nothing. Because both sentences are about stopping an
order, their vectors land close together, and the search finds the right document
anyway. That is the whole reason for using embeddings rather than text matching.

The client is a PersistentClient rather than an in-memory one, so the vectors are
written to disk in the chroma_db folder and survive after the process exits.

---

## Section 6 - Stage 3, Intent Classification and Routing

Not every question deserves a document lookup. Asking about the capital of France
has nothing to do with Zepto policies, and searching the policy corpus for it
would return three irrelevant documents. So the pipeline decides first what kind
of question it is.

There are exactly two intents.

| Intent | Meaning | Where it is routed |
| --- | --- | --- |
| policy_question | The question is about a Zepto policy | retrieve_and_answer node |
| general_question | Anything else | direct_answer node |

In the default mock mode the decision is made by a keyword list, with no model
call at all.

```python
policy_keywords = [
    "delivery", "return", "refund", "membership",
    "tracking", "cancel", "gift card", "support hours"
]
query_lower = state["query"].lower()
if any(keyword in query_lower for keyword in policy_keywords):
    intent = "policy_question"
else:
    intent = "general_question"
```

Each keyword maps onto a document topic, which is why the list has eight entries.

| Keyword | Document it points at |
| --- | --- |
| delivery | doc_01.txt |
| return, refund | doc_02.txt |
| membership | doc_03.txt |
| tracking | doc_04.txt |
| cancel | doc_05.txt |
| gift card | doc_07.txt |
| support hours | doc_08.txt |

The query is lowercased before the check, so "How do I CANCEL?" and "how do i
cancel" both classify the same way.

This heuristic is deliberately simple and it has a known limitation. A question
phrased without any of the eight keywords, for example "how long until my food
arrives", would be classified as a general question even though doc_01.txt
answers it directly. The trade off is accepted because it makes the graded
baseline fully deterministic. The same question always produces the same intent,
with no API key, no network and no cost. Real LLM mode, described in Section 9,
removes this limitation.

The routing itself is a separate function that reads the intent off the state.

```python
def route_intent(state: State) -> Literal["retrieve_and_answer", "direct_answer"]:
    current_intent = state.get("intent")
    if current_intent in ["policy_question", "policy"]:
        return "retrieve_and_answer"
    return "direct_answer"
```

Note that it accepts both "policy_question" and the shorter "policy". That is
defensive. In real LLM mode a model might reply with just the word policy, and
this stops that variation from silently falling through to the wrong branch.

---

## Section 7 - The LangGraph Structure

LangGraph models the pipeline as a graph. Nodes are steps, edges are the arrows
between them, and a shared state object travels through it.

The state is declared as a typed dictionary.

```python
class State(TypedDict):
    query: str
    intent: Literal["policy_question", "general_question"]
    retrieved_docs: list[str]
    answer: Union[dict, str]
```

| State field | Set by | Contains |
| --- | --- | --- |
| query | The caller | The user's original question, never modified |
| intent | classify_intent | policy_question or general_question |
| retrieved_docs | retrieve_and_answer | The full text of the top 3 matches, empty on the direct branch |
| answer | Either answer node | The final schema-shaped dictionary |

The graph is wired like this.

```python
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
```

Read as a path, there are exactly two routes through the graph.

| Route | Path taken | Retrieval runs? |
| --- | --- | --- |
| Policy question | START, classify_intent, retrieve_and_answer, END | Yes |
| General question | START, classify_intent, direct_answer, END | No |

The important detail is add_conditional_edges rather than add_edge. A normal edge
always goes to the same next node. A conditional edge calls a function first and
uses its return value to pick the destination, which is what makes the branch
possible. The two branches then both end at END, so whichever route is taken, the
caller gets a completed state back in the same shape.

---

## Section 8 - Stages 4 and 5, Retrieval and Answer Generation

On the policy branch the query itself is embedded with the same model that
embedded the documents, and the store is searched.

```python
embeddings = model.encode(state["query"])
retrieved_docs = collection.query(
    query_embeddings=[embeddings.tolist()],
    n_results=3,
    include=['documents', 'metadatas']
)
```

Using the same model for both sides is essential. Two different models produce
vectors in two different spaces, and comparing across them measures nothing. The
distances would still be numbers, so the search would return results, but those
results would be meaningless.

n_results=3 asks for the top three matches rather than one.

| Number retrieved | What happens |
| --- | --- |
| 1 only | If the closest match is slightly wrong, the answer has no fallback context |
| 3, the choice here | Related policies come along, which helps for questions spanning two topics |
| All 8 | Every prompt would carry the whole corpus, which wastes tokens and dilutes relevance |

Three is a reasonable middle with a corpus of only eight short documents. A
cancellation question genuinely benefits from also seeing the refund policy,
which is exactly what happens in the recorded output in Section 10.

The source filenames are then pulled out of the metadata, with the row id as a
fallback if metadata is somehow missing.

```python
source_ids = [meta.get("source", doc_id) for meta, doc_id in zip(metadatas, ids)] if metadatas else ids
```

In mock mode the answer is assembled deterministically from the top chunk.

```python
top_snippet = docs[0][:200] if docs else "No document content found."
answer_obj = FinalAnswerSchema(
    answer=f"Based on the retrieved context: {top_snippet}",
    sources=source_ids,
    confidence=1.0
)
```

The first 200 characters of the best matching document are quoted verbatim. There
is no summarising and no rewording, so the answer cannot contain anything the
documents do not say. The if docs else guard covers the case of an empty store,
which would otherwise raise an index error on docs[0].

Every answer, in both modes and on both branches, is built through
FinalAnswerSchema. That is what guarantees the response shape is always the same.

| Field | Type | Rule enforced by Pydantic |
| --- | --- | --- |
| answer | str | Required, must be a string |
| sources | List[str] | Defaults to an empty list |
| confidence | float | Defaults to 1.0, must be between 0.0 and 1.0 inclusive |

The bound on confidence is written as ge=0.0, le=1.0, meaning greater than or
equal to zero and less than or equal to one. A model that returns a confidence of
95, meaning 95 percent, is rejected rather than silently accepted as a value
nineteen times larger than the maximum.

---

## Section 9 - The MOCK_LLM Toggle

The module runs in two modes controlled by one environment variable. Mock mode is
the default and is the graded baseline.

```python
mock_llm = os.getenv("MOCK_LLM", "1")
api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
if mock_llm == "0" and api_key:
    ...real LLM path...
else:
    ...mock path...
```

Note the default value "1" in os.getenv. If the variable is never set at all, the
pipeline runs in mock mode. Note also that real mode requires both the flag and a
key. Setting MOCK_LLM=0 without a key falls back to mock rather than crashing.

Behaviour side by side.

| Stage | Mock mode, the default | Real LLM mode, MOCK_LLM=0 with a key |
| --- | --- | --- |
| classify_intent | Keyword list, no model call | Groq llama3-8b-8192 classifies the query |
| Retrieval | Runs for real against ChromaDB | Runs for real against ChromaDB, identically |
| retrieve_and_answer | Quotes the first 200 characters of the top document | Prompts the model with the retrieved context and validates the JSON it returns |
| direct_answer | Fixed sentence, "I can only answer questions about Zepto policies right now." | Prompts the model with no retrieval context |
| confidence | Always 1.0 | Whatever the model reports, still bounded to 0 to 1 |
| Needs network | No | Yes |
| Same output every time | Yes | No |

The single most important line in that table is the retrieval row. Retrieval is
real in both modes. Mock mode does not fake the vector search, it only replaces
the writing of the final sentence. So the RAG mechanism being demonstrated is
genuinely exercised even with no API key present.

The retry loop in real mode is worth describing because it is what makes schema
compliance reliable rather than hopeful.

```python
for attempt in range(3):  # Initial attempt + up to 2 retries
    try:
        response = llm.chat.completions.create(...)
        validated = FinalAnswerSchema.model_validate_json(raw_content)
        return validated.model_dump()
    except Exception as e:
        messages.append({"role": "assistant", "content": raw_content ...})
        messages.append({"role": "user", "content": f"Corrective Instruction: Output failed validation ({last_error}). ..."})
```

| Attempt | What is sent |
| --- | --- |
| 1 | The prompt template with the retrieved documents |
| 2 | The same conversation plus the bad output and the exact validation error |
| 3 | The same again, with the newest error appended |
| After 3 | Give up and return an error answer with confidence 0.0 |

Two design points here. The failed output is appended back into the conversation
along with the error text, so the model can see what it produced and precisely
why it was rejected, rather than being asked to guess again blindly. And the give
up path still returns a valid FinalAnswerSchema, with confidence set to 0.0
instead of 1.0. The caller therefore never receives a malformed response, only a
well formed one that honestly reports low confidence.

The request also passes response_format={"type": "json_object"}, which asks the
Groq API itself to constrain the output to JSON. That reduces how often the retry
loop is needed but does not replace it, because valid JSON with the wrong keys
would still fail schema validation.

---

## Section 10 - The Prompt Template

The prompt sent to the model in real mode is built from named sections rather
than being one long paragraph.

| Section | What it does |
| --- | --- |
| ROLES | States that the assistant is Zepto support and must decline rather than guess |
| CONTEXT | Injects the retrieved documents |
| TASK | Says to use only the provided documents and gives the exact refusal sentence |
| FORMAT | Says to return only the answer, no document titles or scores |
| LENGTH | Asks for 2 to 4 sentences |
| FEW-SHOT EXAMPLES | Two worked examples showing a refusal and a good answer |

The refusal sentence is fixed rather than left to the model's own wording.

"I cannot answer this question using the available documents."

Having one exact sentence means a refusal can be detected reliably by a string
comparison, instead of having to recognise a dozen different ways of phrasing a
polite no.

The two few shot examples are chosen to teach opposite behaviours. The first,
about ordering a pizza, shows a question that is out of scope and must be refused
even though the model certainly knows what a pizza is. The second, about
reporting a damaged item, shows a correct in scope answer at the right length and
level of detail. Showing the refusal case first is intentional, because refusing
is the behaviour a language model is least inclined to do on its own.

---

## Section 11 - The API Layer

The API is a single POST endpoint. The request and response shapes are declared
in models.py.

```python
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    intent: str
    retrieved_docs: List[str]
    answer: FinalAnswerSchema
```

| Response field | Why it is exposed | What it lets you check |
| --- | --- | --- |
| query | Echoes back the input | That the server received what you sent |
| intent | The classification decision | Which branch the graph took |
| retrieved_docs | Full text of the top 3 matches | Whether retrieval found sensible documents |
| answer | The schema-validated final answer | The reply, its sources and its confidence |

Returning intent and retrieved_docs alongside the answer is a deliberate choice.
It turns the pipeline from a black box into something inspectable. If an answer
looks wrong, the response itself shows whether the cause was misclassification or
poor retrieval, without needing to read the server logs.

The endpoint builds the starting state, runs the graph, and packs the result.

```python
result = graph.invoke(initial_state)

answer_raw = result.get("answer", {})
if isinstance(answer_raw, dict):
    final_answer = FinalAnswerSchema(**answer_raw)
else:
    final_answer = FinalAnswerSchema(answer=str(answer_raw), sources=[], confidence=1.0)
```

The isinstance check exists because the State type declares answer as
Union[dict, str]. Normally it is a dictionary produced by model_dump, but the
branch handles the plain string case as well so an unexpected value is wrapped
into the schema rather than raising an error at the very last step.

The initial state sets intent to "general_question" as a placeholder. That value
is always overwritten by classify_intent, which is the first node to run, so it
is a default rather than a real decision.

---

## Section 12 - Recorded API Outputs

Both examples were run against a local server at http://127.0.0.1:8000/ask with
the default MOCK_LLM=1.

Example 1, a policy question, where retrieval runs.

```bash
curl -s -X POST "http://127.0.0.1:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"query": "How to cancel my order?"}'
```

The word cancel is in the keyword list, so the intent is policy_question and the
graph takes the retrieval branch. The response is abbreviated below to keep it
readable, with the full document text shortened.

```json
{
  "query": "How to cancel my order?",
  "intent": "policy_question",
  "retrieved_docs": [
    "Order Cancellation Policy: \"Orders can be cancelled free of cost any time before the order status changes to 'Packed' ...\"",
    "Damaged or Missing Items: \"If an order arrives with damaged, spoiled, or missing items ...\"",
    "Returns & Refunds: \"Grocery and perishable items may be reported for a return within 24 hours ...\""
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

The three retrieved sources are worth reading closely, because they show the
similarity search behaving sensibly.

| Rank | Source | Topic | Why it ranked here |
| --- | --- | --- | --- |
| 1 | doc_05.txt | Order Cancellation | Exactly the question asked |
| 2 | doc_06.txt | Damaged or Missing Items | Also about an order going wrong after it is placed |
| 3 | doc_02.txt | Returns and Refunds | Cancelling raises the question of getting money back |

Nothing about delivery zones, gift cards or membership tiers appears. The top
three are the three documents a human would also reach for.

Also note that the answer text stops mid sentence at "Once an order has been".
That is the 200 character slice in mock mode cutting the snippet, not a bug. Real
LLM mode replaces this snippet with a written answer.

Example 2, a general question, where retrieval does not run.

```bash
curl -s -X POST "http://127.0.0.1:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the capital of France?"}'
```

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

Three things confirm the branch worked correctly. The intent is
general_question, retrieved_docs is an empty list which proves the vector search
was skipped entirely rather than run and discarded, and sources is empty because
nothing was cited. The assistant does not answer Paris, even though that answer
is trivially available to any language model, because answering it would be
outside the scope the corpus defines.

---

## Section 13 - Containerization

The Dockerfile packages the whole module into a single image.

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

Line by line.

| Line | What it does and why |
| --- | --- |
| FROM python:3.10-slim | Starts from a small official Python image, slim to keep the image size down |
| WORKDIR /app | Every later command runs inside /app |
| COPY requirements.txt . then RUN pip install | Copies only the requirements file first so the install layer is cached and does not rerun when only the code changes |
| COPY . . | Copies the application code and the docs corpus in afterwards |
| EXPOSE 7860 | Declares the port, which is the port Hugging Face Spaces expects |
| CMD uvicorn --host 0.0.0.0 | Binds to all interfaces, not 127.0.0.1, otherwise the container would refuse connections from outside itself |

The two details that most often go wrong are both in that table. Copying
requirements.txt before the rest of the code is what keeps rebuilds fast, since
Docker reuses the cached install layer whenever the requirements have not
changed. And binding to 0.0.0.0 rather than the default localhost is what makes
the published port actually reachable from the host machine.

Build and run.

```bash
docker build -t support-assistant .
docker run -p 7860:7860 support-assistant
```

---

## Section 14 - Deployment Notes

| Item | Setting |
| --- | --- |
| Platform | Hugging Face Spaces |
| SDK | Docker |
| Tier | Free community CPU tier |
| Port | 7860, which is the port Spaces routes to |
| API key storage | Space secret named GROQ_API_KEY under Settings and Repository Secrets |

The API key is read at runtime with os.getenv and is never written into the code
or committed to the repository. Because mock mode is the default and needs no
key, the Space still runs correctly with no secret configured at all.

---

## Section 15 - Summary of Assignment Requirements

| Requirement | Where it is done | Status |
| --- | --- | --- |
| Load a document corpus | Section 4 | 8 text files |
| Embed and store in a vector database | Section 5 | all-MiniLM-L6-v2 into ChromaDB, 384 dimensions |
| Classify the incoming query | Section 6 | Two intents, keyword based in mock mode |
| Route conditionally so retrieval is skipped when not needed | Sections 6 and 7 | LangGraph conditional edge |
| Retrieve relevant documents | Section 8 | Top 3 by similarity, with source metadata |
| Structured prompt template | Section 10 | Roles, context, task, format, length, few-shot |
| Enforce a fixed output schema | Section 8 | Pydantic FinalAnswerSchema on every path |
| Expose it as an API | Section 11 | FastAPI POST /ask |
| Record example outputs | Section 12 | One retrieval case, one non-retrieval case |
| Containerize | Section 13 | Dockerfile on port 7860 |
