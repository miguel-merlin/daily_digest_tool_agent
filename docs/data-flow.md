# Data Flow & Logic Architecture

This document details the movement of information from raw Slack dumps to personalized insights, utilizing Parallelization and Routing patterns.

## Phase 1: Ingestion & Routing (The Filter)
* **Pattern:** **Parallelization** & **Routing**.
* **Input:** Batch JSON export of daily Slack channels (`#mechanical`, `#electrical`, `#supply-chain`, `#general`).
* **Step 1.1 (Sanitization):** Raw text passes through **Bedrock Guardrails** to redact PII and filter unrelated "watercooler" chat.
* **Step 1.2 (Topic Extraction):** The **Ingestion Agent** scans threads.
    * *Logic:* "Does this thread contain a Decision, a Risk, or an FYI?"
* **Step 1.3 (Routing):** Based on the topic, the thread is routed to a Domain Worker.
    * *Example:* "Thermal paste spec change" -> Routes to **Mechanical Expert**.
    * *Example:* "Chipset lead time delay" -> Routes to **Supply Chain Expert**.

## Phase 2: Synthesis & Contextualization (The Reasoning)
* **Pattern:** **Reasoning Techniques** & **RAG**.
* **Actor:** Domain Worker Agents (Mechanical, Electrical, etc.).
* **Process:**
    1.  **Retrieve:** Agent queries **Bedrock Knowledge Base** for context. (e.g., "What is the 'DVT Phase' requirement for thermal throttling?").
    2.  **Reason:** Agent evaluates the Slack thread against the retrieved context.
    3.  **Summarize:** Generates a structured "Knowledge Nugget" (JSON) containing: ` { "topic": "Thermal", "severity": "High", "summary": "...", "impact": "Production Delay" }`.

## Phase 3: Personalization (The Lens)
* **Pattern:** **Memory Management** & **Prioritization**.
* **Trigger:** User (e.g., "Sarah, Eng Manager") requests a digest via the UI.
* **Step 3.1 (Profile Load):** System loads "Sarah's" active persona from **DynamoDB**.
    * *Attributes:* `Role: Manager`, `Focus: Timeline`, `Technical_Depth: Low`.
* **Step 3.2 (Relevance Scoring):** The **Personalization Agent** scores every "Knowledge Nugget" against Sarah's profile.
    * *Logic:* "Sarah cares about 'Production Delay' (Score 0.95). She does not care about 'Variable Renaming in Code' (Score 0.10)."

## Phase 4: Reflection & Refinement (The Polishing)
* **Pattern:** **Reflection**.
* **Actor:** The **Critic Agent**.
* **Action:** Reads the draft digest.
    * *Self-Correction:* "The draft mentions 'thermal throttling' without context. Sarah is a Manager, not an Analyst. Rewrite to explain the *business impact* of the throttling."
* **Output:** Final Markdown Digest delivered to the Streamlit UI.

## Phase 5: Feedback Loop (The Learning)
* **Pattern:** **Learning and Adaptation** & **Human-in-the-Loop**.
* **Action:** Sarah clicks "Mark as Irrelevant" on a specific item.
* **Result:** System updates Sarah's vector profile in memory to down-weight similar topics in the future.