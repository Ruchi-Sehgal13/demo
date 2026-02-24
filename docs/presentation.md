# Hallucination Guardrail Meta-Agent (IPC ↔ BNS) – Presentation Outline

Use this outline to build slides (e.g. in PowerPoint or Google Slides).

---

## Slide 1: Title
- **Title:** Hallucination Guardrail Meta-Agent (IPC ↔ BNS)
- **Subtitle:** Verifying LLM answers against a trusted legal knowledge base
- **Optional:** Logo, date, team

---

## Slide 2: Problem
- LLMs can hallucinate or state unverified legal information.
- Need a system that **only shows answers supported by a trusted IPC–BNS knowledge base**.
- Goal: Guardrail that breaks the answer into claims, verifies each, and composes a safe response.

---

## Slide 3: Solution overview
- **Meta-agent pipeline:** Question → Primary LLM → Claim extraction → Verification (retrieval + LLM judge) → Composer → Response.
- **Output:** Guardrailed answer (verified claims only) or a clear “no reference in KB” message.
- **No confidence scores:** Each claim is either verified (TRUE) or not (FALSE).

---

## Slide 4: Architecture (high-level)
- **Primary LLM:** Answers the question (Groq or Google).
- **Claim extractor:** Extracts atomic factual claims.
- **Verifier:** Semantic search (Chroma) + LLM judge (claim vs chunk → TRUE/FALSE).
- **Composer:** Builds final answer from verified claims only, or “I could not find reference for this in the knowledge base.”
- **Evaluation:** Logs each run (question, status, counts).
- **Reference:** `docs/architecture.md` for diagram.

---

## Slide 5: Knowledge base & verification
- **KB:** PDF (IPC–BNS conversion guide) → chunks → Chroma vector store.
- **Embeddings:** Google or sentence-transformers (local).
- **Verification:** Retrieve top-k chunks per claim → LLM judges: “Does this excerpt support the claim?” (TRUE/FALSE).
- **Limitation:** Accuracy depends on chunk quality and judge; no external fact-check beyond the KB.

---

## Slide 6: Composer & guardrailed output
- Composer receives only **verified** claims.
- If verified claims suffice to answer the question → one short paragraph.
- If not (off-topic or insufficient) → “I could not find reference for this in the knowledge base.”

---

## Slide 7: Tech stack
- **Orchestration:** LangGraph (workflow graph).
- **LLMs:** Groq (Llama), Google (Gemini). No offline mode.
- **Vector store:** Chroma.
- **App:** Streamlit.
- **Language:** Python 3.10+.

---

## Slide 8: What we did (summary)
- Removed planner and human-review nodes; verification is always on.
- Replaced similarity-based “confidence” with **LLM judge** (TRUE/FALSE per claim).
- Added **composer** for guardrailed answer and KB-refusal message.
- Vector-only verification (no relational DB).
- Only Google and Groq as providers.

---

## Slide 9: Failures & limitations
- **Structured output:** Some providers (e.g. Groq) returned `"FALSE"` (string); schema fixed to `Literal["TRUE","FALSE"]`.
- **Chunk quality:** If PDF chunks are poor, the judge can only say whether *that* text supports the claim.
- **No external fact-check:** Only KB content is used; no live legal DB.

---

## Slide 10: Demo / next steps
- **Demo:** Ask a legal question (e.g. “What is the BNS equivalent of IPC 302?”) and show Guardrailed Answer vs Full LLM response.
- **Next steps:** Better chunking, optional human review for low-verification runs, expand KB.

---

## Slide 11: Q&A
- Contact / repo / docs.
