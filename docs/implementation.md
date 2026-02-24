# Implementation Summary & Failures

## What we did

### 1. Removed planner node
- **Before:** A planner node decided “verify” vs “direct” and produced a plan + route.
- **After:** Removed planner and all references. Every question goes through full verification (no direct-answer path).
- **Files:** Deleted `src/agents/planner.py`; updated `src/graph/workflow.py`, `src/graph/state.py`, `app.py`, `src/agents/evaluation.py`, claim_extractor, verifier.

### 2. Removed human validation / human review node
- **Before:** A human_validation node set `needs_human` and wrote to `human_review_queue.jsonl`.
- **After:** Removed the node and all related state (`needs_human`, `human_feedback`).
- **Files:** Deleted `src/agents/human_validation.py`; updated workflow, state, app, evaluation.

### 3. LLM as judge during verification
- **Before:** Verification was semantic-search only; “confidence” was derived from similarity scores.
- **After:** For each claim we (1) retrieve evidence from the vector store (Chroma), (2) call an LLM with claim + evidence and get TRUE/FALSE (does the excerpt support the claim?). No confidence; binary verified/unverified.
- **Files:** `src/nodes/agents/verifier.py` – added `_retrieve_evidence`, `_llm_verify`, `VerificationOutput(verified: Literal["TRUE","FALSE"])`.

### 4. Composer node
- **Before:** No composer; guardrailed output was just a list of verified claims.
- **After:** Composer node runs after verifier. It takes the question + verified claims and uses an LLM to produce either a short answer (using only those claims) or the refusal: **“I could not find reference for this in the knowledge base.”**
- **Files:** `src/nodes/agents/composer.py`; added `composed_answer` to state; workflow: verifier → composer → evaluation; app shows Guardrailed Answer and “Full LLM response” in expander.

### 6. Only Google and Groq
- **Before:** App and config supported an “offline” provider for testing.
- **After:** Removed “offline” from the provider list and from `get_llm()`. Only `groq` and `google` remain.
- **Files:** `app.py`, `src/config.py` (LLMProvider, get_llm).

### 6. Relational DB and seed script removed
- **Before:** Relational store (SQLite IPC→BNS mapping), seed script `scripts/seed_ipcbns_mapping.py`, and relational logic in verifier.
- **After:** Verification uses only the vector store (Chroma). No SQLite, no seed script, no `IPCBNSRelationalStore` or `paths.SQLITE_DB`.
- **Files:** Removed from `src/rag/vectorstore.py`, `src/nodes/agents/verifier.py`, `src/config.py`; deleted seed script (scripts folder had no other refs).

### 7. build_vector_store in RAG folder
- **Status:** `build_vector_store.py` lives under `src/rag/build_vector_store.py`. Run: `python -m src.rag.build_vector_store` (docstring previously said `scripts.build_vector_store`; that was legacy).

### 8. Adversarial script removed
- **Before:** `src/agents/adversarial.py` ran red-team prompts and printed results.
- **After:** File and all references removed.

### 9. Folder structure (nodes: agents vs steps)
- **Current:** `src/nodes/agents/` (claim_extractor, composer, primary_llm, verifier — all LLM-calling nodes), `src/nodes/steps/` (evaluation — non-LLM pipeline steps), `src/graph/` (state, workflow), `src/rag/` (vector store, PDF processing, build_vector_store), `src/config.py`.

---

## Failures and fixes

### 1. Groq structured output: expected boolean, got string
- **Error:** `tool call validation failed: parameters for tool VerificationOutput did not match schema: errors: [/verified: expected boolean, but got string]`. The LLM returned `"verified": "FALSE"` (string).
- **Fix:** Changed Pydantic model from `verified: bool` to `verified: Literal["TRUE", "FALSE"]` so the API accepts the string. In code we use `result.verified == "TRUE"` to get a boolean.
- **File:** `src/nodes/agents/verifier.py`.

### 2. Guardrailed answer not answering the question
- **Issue:** Composer was outputting a raw list of verified claims. For questions like “Do dogs get punished?” only generic claims were verified, so the “answer” was off-topic (e.g. “BNS and IPC address human actions”).
- **Fix:** Composer was redesigned to use an LLM: input = question + verified claims; output = one short paragraph that **answers the question** using only those claims, or the refusal sentence. So the guardrailed answer is either a real answer or “I could not find reference for this in the knowledge base.”
- **File:** `src/nodes/agents/composer.py`.

### 3. Chunk quality and factual check
- **Limitation:** Factual check is “does this KB chunk support this claim?” (LLM judge). If chunks are bad (wrong, truncated, or irrelevant), the judge can only rule on that text. There is no external fact-check or live legal DB.
- **Mitigation:** Quality of the PDF and chunking (e.g. `src/rag/pdf_processor.py`, chunk size/overlap) directly affect verification quality. Improving chunks and optional human review for low-verification runs would help.

---

## Document history
- Summary covers the implementation as of the last changes: composer wording (“I could not find reference for this in the knowledge base”), only Google and Groq, and the above fixes.
