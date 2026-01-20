# EverCurrent Daily Digest: System Design Document

## 1. System Architecture

The EverCurrent Daily Digest Tool is a **Multi-Agent System (MAS)** deployed on **AWS Bedrock AgentCore**. It solves the "knowledge silo" problem in hardware engineering teams by transforming high-volume, unstructured Slack data into hyper-personalized, role-specific daily briefs.

Unlike standard summary bots, this system uses **active reasoning** to determine relevance based on a user's changing role and project phase (e.g., "PVT Critical" vs. "Concept Phase").

### Core Architectural Patterns

This architecture is built on five specific advanced agentic patterns:

1. **Orchestrator-Workers:** A central "Supervisor" agent manages specialized sub-agents (Mechanical, Supply Chain, Firmware) to ensure domain expertise.
2. **Reflective Processing:** A dedicated "Critic" step reviews generated digests against the user's persona to minimize hallucination and noise before delivery.
3. **Dynamic Memory:** The system maintains a stateful "User Profile" that evolves based on feedback. It utilizes Episodic Memory to learn from past interactions (e.g., "Stop showing me minor firmware bug reports").
4. **Resource-Aware Optimization:** We use a **LiteLLM Gateway** to route "bulk" processing tasks (filtering 10k messages) to faster/cheaper models (e.g., Claude 3 Haiku) while reserving reasoning tasks for stronger models (e.g., Claude 3.5 Sonnet).
5. **Observability:** Deep tracing via **Langfuse** on AWS to debug *why* a specific piece of information was deemed "relevant" or "irrelevant."

### AWS Infrastructure Topology

The system is deployed using Terraform with the following components:

* **Runtime:** AWS Bedrock AgentCore (Serverless Containerized Agents).
* **Model Gateway:** LiteLLM (Self-hosted on AWS) balancing requests between Bedrock and other providers if needed.
* **Knowledge Store:** Amazon Bedrock Knowledge Bases (Vector Search) for retrieving project specs and historical context (RAG).
* **Safety Layer:** Amazon Bedrock Guardrails for PII redaction (sanitizing Slack messages) and toxicity filtering.
* **Frontend:** Custom Streamlit UI (Fargate/Local) for persona management and simulation.

---

## 2. Data Flow & Logic Architecture

This section maps the journey of a Slack message from "raw noise" to "critical insight."

### Phase 1: Ingestion & Routing (The Filter)

* **Pattern:** Parallelization & Routing.
* **Input:** Batch JSON export of daily Slack channels (`#mechanical`, `#electrical`, `#supply-chain`, `#general`).
* **Step 1.1 (Sanitization):** Raw text passes through **Bedrock Guardrails** to redact PII and filter unrelated "watercooler" chat.
* **Step 1.2 (Topic Extraction):** The **Ingestion Agent** scans threads to determine if they contain a Decision, a Risk, or an FYI.
* **Step 1.3 (Routing):** Based on the topic, the thread is routed to a Domain Worker.
* *Example:* "Thermal paste spec change" -> Routes to **Mechanical Expert**.
* *Example:* "Chipset lead time delay" -> Routes to **Supply Chain Expert**.



### Phase 2: Synthesis & Contextualization (The Reasoning)

* **Pattern:** Reasoning Techniques & RAG.
* **Actor:** Domain Worker Agents (Mechanical, Electrical, etc.).
* **Process:**
1. **Retrieve:** Agent queries **Bedrock Knowledge Base** for context (e.g., "What is the 'DVT Phase' requirement for thermal throttling?").
2. **Reason:** Agent evaluates the Slack thread against the retrieved context.
3. **Summarize:** Generates a structured "Knowledge Nugget" (JSON) containing topic, severity, summary, and impact.



### Phase 3: Personalization (The Lens)

* **Pattern:** Memory Management & Prioritization.
* **Trigger:** User (e.g., "Sarah, Eng Manager") requests a digest via the UI.
* **Step 3.1 (Profile Load):** System loads "Sarah's" active persona from **DynamoDB**.
* *Attributes:* `Role: Manager`, `Focus: Timeline`, `Technical_Depth: Low`.


* **Step 3.2 (Relevance Scoring):** The **Personalization Agent** scores every "Knowledge Nugget" against Sarah's profile.
* *Logic:* "Sarah cares about 'Production Delay' (Score 0.95). She does not care about 'Variable Renaming in Code' (Score 0.10)."



### Phase 4: Reflection & Refinement (The Polishing)

* **Pattern:** Reflection.
* **Actor:** The **Critic Agent**.
* **Action:** Reads the draft digest.
* *Self-Correction:* "The draft mentions 'thermal throttling' without context. Sarah is a Manager, not an Analyst. Rewrite to explain the *business impact* of the throttling."


* **Output:** Final Markdown Digest delivered to the Streamlit UI.

### Phase 5: Feedback Loop (The Learning)

* **Pattern:** Learning and Adaptation & Human-in-the-Loop.
* **Action:** Sarah clicks "Mark as Irrelevant" on a specific item.
* **Result:** System updates Sarah's vector profile in memory to down-weight similar topics in the future.

---

## 3. Component Details: Agentic Implementation

### A. The Agents (LangGraph Nodes)

1. **OrchestratorAgent (The Supervisor)**
* **Role:** The "Brain" that manages state and hands off tasks.
* **Implementation:** A LangGraph `StateGraph` root node.
* **Key Function:** Maintains the `GlobalState` (list of messages, list of nuggets, current user context).


2. **DomainExperts (Worker Agents)**
* **Variants:** `MechanicalAgent`, `ElectricalAgent`, `SupplyChainAgent`.
* **Configuration:** Specialized system prompts focused on specific engineering domains.
* **Tools:** `VectorSearchTool` (to look up specs), `Search_Tool` (to check external vendor status).


3. **PersonaManager (Memory Agent)**
* **Role:** Manages the "Digital Twin" of the user using the **Model Context Protocol (MCP)** standard.
* **Data Store:** JSON blobs in Postgres/DynamoDB (mapped to `user_id`).


4. **CriticAgent (Quality Control)**
* **Role:** The final editor ensuring safety and quality.
* **Logic:** Checks for hallucinations (verifying facts against raw threads) and tone (professionalism).



### B. The Mock User Interface (Streamlit)

**Location:** `cx-agent-frontend/src/app.py`
**Purpose:** Serves as the "Simulation Console" for the demo.

* **Left Panel (Scenario Setup):**
* **"Persona Creator":** Create a new user (Role, Focus, Seniority).
* **"Project Phase Slider":** Move project from "Concept" -> "Prototyping" -> "Production" (Changes agent prioritization weights).


* **Center Panel (Chat/Digest):**
* **"Inject Mock Data":** Button to load pre-set complex Slack threads.
* **"Generate Digest":** Triggers the Agentic Workflow.


* **Right Panel (Debug/Trace):**
* **"Thought Process":** Displays the Langfuse trace ID and a simplified view of the agent's reasoning.



---

## 4. Feature Set & User Experience (UX)

### A. The "Smart" Daily Digest

The core feature is a prioritized briefing document, not a chronological feed.

1. **Contextual Executive Summary:**
* Opens with the current **Project Phase** (e.g., "EVT - Engineering Validation Test") to set the priority context.
* **"Red Flag" Section:** Highlights strictly critical blockers (decisions/risks) tailored to the user's role.


2. **Role-Adaptive Content:**
* **Engineers:** Receives deep technical details, parametric values, and GitHub/Jira links.
* **Managers:** Receives high-level synthesis, cost implications, and schedule impacts.


3. **Progressive Disclosure:**
* Items are summarized by default. Users can click "Expand Context" to view the raw Slack thread and retrieved Knowledge Base documents.



### B. Interactive Feedback Loop

4. **Explicit Relevance Tuning:**
* Users can mark items as "Irrelevant." This updates the **Episodic Memory**, training the agent to filter similar topics in the future.


5. **Contextual Chat:**
* "Ask the Agent" bar allows users to query specific items (e.g., "Who owns this thermal risk?").


6. **Persona Simulation (Admin):**
* An interface to define "Digital Twins" (Roles, Focus Areas, Seniority) and adjust the "Project Phase" slider to test how the agent adapts.



---

## 5. API Specification

The following RESTful API model supports the frontend-to-backend interaction.

### A. Persona Management

*Handles Memory Management and Context Protocol*

#### `POST /api/v1/persona`

Creates or updates a user's digital twin configuration.

**Request Body:**

```json
{
  "user_id": "user_123",
  "role": "Mechanical Engineer",
  "seniority": "Senior",
  "focus_areas": [
    "Thermal Throttling",
    "Adhesives",
    "Waterproofing"
  ],
  "noise_filters": [
    "lunch orders",
    "happy hour",
    "general banter"
  ],
  "project_phase_override": "EVT" 
}

```

**Response:**

```json
{
  "status": "success",
  "persona_id": "p_98765",
  "message": "Persona updated. Memory weights re-balanced for 'Thermal' topics."
}

```

### B. Ingestion & Simulation

*Handles Parallelization and Routing*

#### `POST /api/v1/ingest/slack`

Simulates the ingestion of a day's worth of Slack logs for processing.

**Request Body:**

```json
{
  "timestamp": "2023-10-27T09:00:00Z",
  "channels": [
    {
      "name": "mechanical",
      "messages": [
        {
          "user": "Dave",
          "text": "The thermal paste is failing at 85C. We need a decision on the new vendor.",
          "ts": "1698393600.000100"
        }
      ]
    }
  ]
}

```

**Response:**

```json
{
  "status": "processing",
  "job_id": "job_555",
  "message": "Ingestion started. 150 messages routed to Domain Agents."
}

```

### C. Digest Generation

*Handles Reasoning, Reflection, and Prioritization*

#### `POST /api/v1/agent/digest`

Triggers the multi-agent workflow to generate a personalized digest.

**Request Body:**

```json
{
  "user_id": "user_123",
  "date_range": "24h",
  "force_refresh": true
}

```

**Response:**

```json
{
  "digest_id": "dig_001",
  "generated_at": "2023-10-27T08:30:00Z",
  "project_phase": "EVT",
  "executive_summary": "Three critical risks identified in Thermal and Supply Chain.",
  "sections": [
    {
      "title": "Critical Blockers",
      "type": "risk",
      "items": [
        {
          "item_id": "item_alpha",
          "headline": "Thermal Paste Failure at 85C",
          "summary": "Testing shows current paste fails requirements. Vendor change required.",
          "reasoning_trace": "Included because user lists 'Thermal' as focus area and sentiment is 'Urgent'.",
          "source_threads": ["thread_123"],
          "citations": ["doc_spec_v2.pdf"]
        }
      ]
    },
    {
      "title": "FYI Updates",
      "type": "update",
      "items": [...]
    }
  ]
}

```

### D. Feedback Loop (Learning)

*Handles Learning and Adaptation*

#### `POST /api/v1/feedback`

Submits user feedback to update the agent's episodic memory and weighting logic.

**Request Body:**

```json
{
  "user_id": "user_123",
  "digest_id": "dig_001",
  "item_id": "item_alpha",
  "action": "mark_irrelevant", 
  "comment": "I am not involved in adhesive procurement, only testing."
}

```

**Response:**

```json
{
  "status": "learned",
  "memory_update": {
    "down_weighted_concepts": ["procurement", "vendor_selection"],
    "up_weighted_concepts": ["testing", "validation"]
  }
}

```

### E. Contextual Chat (RAG)

*Handles Knowledge Retrieval*

#### `POST /api/v1/agent/chat`

Allows the user to ask follow-up questions about the digest content.

**Request Body:**

```json
{
  "user_id": "user_123",
  "session_id": "sess_001",
  "message": "Who is the lead engineer on the thermal paste issue?",
  "context_digest_id": "dig_001"
}

```

**Response:**

```json
{
  "response": "According to the #mechanical thread, **Dave (Senior ME)** is leading the testing. However, **Sarah (Supply Chain)** is handling the vendor negotiation.",
  "sources": [
    {
      "channel": "mechanical",
      "ts": "1698393600.000100",
      "text": "I'll handle the vendor call. - Sarah"
    }
  ]
}

```