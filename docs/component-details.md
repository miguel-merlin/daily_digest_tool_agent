# Component Details: Agentic Implementation

## A. The Agents (LangGraph Nodes)

### 1. `OrchestratorAgent` (The Supervisor)
* **Role:** The "Brain" that manages state and hands off tasks.
* **Implementation:** A LangGraph `StateGraph` root node.
* **Key Function:** Maintains the `GlobalState` (list of messages, list of nuggets, current user context).

### 2. `DomainExperts` (Worker Agents)
* **Variants:** `MechanicalAgent`, `ElectricalAgent`, `SupplyChainAgent`.
* **Configuration:**
    * **Prompt:** Specialized system prompts (e.g., "You are a Senior ME. Focus on tolerances, materials, and thermal issues.").
    * **Tools:** `VectorSearchTool` (to look up specs), `TavilySearch` (Optional - to check external vendor status).
    * **Model:** Claude 3.5 Sonnet (via LiteLLM) for high-reasoning capability.

### 3. `PersonaManager` (Memory Agent)
* **Role:** Manages the "Digital Twin" of the user.
* **Pattern:** **Model Context Protocol** for standardizing how user context is injected into prompts.
* **Data Store:** JSON blobs in Postgres/DynamoDB (mapped to `user_id`).
    * *Structure:* `{ "user_id": "123", "current_phase": "EVT", "high_priority_keywords": ["risk", "delay", "budget"], "low_priority_keywords": ["lunch", "typo"] }`

### 4. `CriticAgent` (Quality Control)
* **Role:** The final editor.
* **Pattern:** **Guardrails** + **Reflection**.
* **Logic:**
    1.  Check for hallucinations (Verify facts against the raw Slack thread).
    2.  Tone check (Ensure professional, concise language).
    3.  Safety check (Double-check PII redaction).

## B. The Mock User Interface (Streamlit)

**Location:** `cx-agent-frontend/src/app.py`
**Purpose:** Since we cannot integrate with live Slack for the demo, this UI serves as the "Simulation Console."

* **Left Panel (Scenario Setup):**
    * **"Persona Creator":** Create a new user (Role, Focus, Seniority).
    * **"Project Phase Slider":** Move project from "Concept" -> "Prototyping" -> "Production" (Changes agent prioritization weights).
* **Center Panel (Chat/Digest):**
    * **"Inject Mock Data":** Button to load pre-set complex Slack threads (e.g., "The 'Missing Screw' Crisis").
    * **"Generate Digest":** Triggers the Agentic Workflow.
* **Right Panel (Debug/Trace):**
    * **"Thought Process":** Displays the Langfuse trace ID and a simplified view of the agent's reasoning (e.g., "Filtered out 'Lunch order' thread because relevance < 0.2").

## C. Infrastructure Integration

**1. LiteLLM Gateway**
* **Purpose:** Centralized governance for model access.
* **Configuration:**
    * `master_key`: Uses the key provided config.
    * `model_routing`: Configured to route `model="fast"` to Haiku and `model="reasoning"` to Sonnet.

**2. Observability (Langfuse)**
* **Integration:** The `OrchestratorAgent` is wrapped with the Langfuse Python SDK.
* **Metric:** We track "Hallucination Rate" (via user feedback) and "Processing Latency" per digest.

**3. Knowledge Base (Bedrock)**
* **Ingestion:** We use the `aws bedrock-agent start-ingestion-job` (from Step 4a in docs) to index the PDF specifications of the robot.
* **Usage:** When a Slack message mentions a part number, the agent queries this KB to find the part name and importance.