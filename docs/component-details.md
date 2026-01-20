# Component Deep Dive: EverCurrent Daily Digest Architecture

## 1. AgentCore Runtime & Daily Digest Agent
The **AgentCore Runtime** acts as the central orchestration engine for the system, hosting the **Daily Digest Agent** (a LangChain-based entity). It is responsible for session management, tool routing, and maintaining the cognitive loop of the application.

* **Low-Level Functionality:**
    * **Session Initialization:** Upon a user request, the runtime initializes a new agent instance. It pulls strictly scoped session data from **AgentCore Memory** to hydrate the agent's context window with previous interaction history.
    * **ReAct Loop:** The agent operates on a ReAct (Reasoning + Acting) loop. It analyzes the user's request (e.g., "What happened in the Actuator project today?"), determines which tools to call (`get_messages`, `read_docs`, or `get_customer_profile`), and iterates until a sufficient answer is constructed.
    * **State Management:** The runtime manages the transient state of the conversation, ensuring that tool outputs are correctly fed back into the LLM's context window for subsequent reasoning steps.

* **Bottlenecks & Trade-offs:**
    * **Latency:** The sequential nature of the ReAct loop (Think $\rightarrow$ Act $\rightarrow$ Observe $\rightarrow$ Think) introduces latency. Each tool call requires a round-trip to an external service and a subsequent LLM inference step.
    * **Context Window Limits:** While LLMs have large context windows, hydrating the agent with extensive long-term memory and retrieved documents can lead to context exhaustion or "lost in the middle" phenomena.
    * **Trade-off:** We prioritize **accuracy** over **speed** here. By allowing the agent to reason iteratively, we reduce hallucinations, even though it results in a slower time-to-first-token compared to a simple RAG (Retrieval-Augmented Generation) chain.

## 2. AgentCore Gateway (Dynamic Profiling Engine)
This is the system's core innovation. Unlike static SQL databases for user profiles, the **AgentCore Gateway** manages two specialized sub-agents that interface with unstructured Markdown (`.md`) files stored in S3.

### A. `write_employee_info()` Agent
* **Function:** This sub-agent parses user interactions to extract implicit signals about changing priorities (e.g., a user shifting focus from "battery thermal management" to "supply chain logistics").
* **Mechanism:** It invokes a Lambda function to append or rewrite sections of the `Employee.md` file.
* **Concurrency Handling:** The Lambda must handle potential write conflicts if a user generates multiple signals rapidly, likely using S3 versioning or optimistic locking strategies.

### B. `get_customer_profile()` Agent
* **Function:** Before the main digest generation, this agent reads the `Employee.md` file to construct a "system prompt injection" containing the user's persona.
* **Mechanism:** It uses a Lambda to fetch the file from S3.

* **Bottlenecks & Trade-offs:**
    * **Cold Starts:** The Lambda functions triggering these tools may experience cold starts, adding ~100-500ms latency to the initial tool call.
    * **Trade-off (Unstructured vs. Structured Data):** Storing profiles in Markdown (`.md`) rather than a database allows the LLM to store flexible, nuanced natural language notes about the user (e.g., "User prefers concise bullet points"). The trade-off is higher query latency and lack of strict schema validation compared to a DynamoDB or PostgreSQL lookup.

## 3. Data Ingestion Pipeline (The Knowledge Backbone)
The system relies on an asynchronous "Extract, Load, Index" (ELI) pipeline to keep the knowledge base fresh without blocking user requests.

* **Components:**
    * **Cron Job (Lambda):** A scheduled Lambda function polls Slack APIs and Company Documentation repositories.
    * **Raw Storage (S3):** Raw JSON/Text data is dumped into S3 buckets ("Slack Messages" & "Company Docs").
    * **Indexing (Bedrock Knowledge Base):** Amazon Bedrock manages the ingestion from S3, chunking the text (e.g., recursive character split), creating vector embeddings, and updating the OpenSearch index.

* **Bottlenecks & Trade-offs:**
    * **Data Freshness (Eventual Consistency):** Since this is a cron-based system (not real-time streaming), there is a lag between a Slack message being posted and it appearing in the digest.
    * **Trade-off:** We sacrifice **real-time** availability for **architectural simplicity** and **cost efficiency**. A real-time stream would require managing WebSocket connections or Kinesis streams, significantly increasing complexity for a "Daily Digest" use case where sub-second freshness is rarely critical.

## 4. Retrieval & Inference Layer
* **Amazon OpenSearch (Vector Database):** Acts as the retrieval engine. It performs semantic search (KNN/ANN) to find messages relevant to the query.
* **Amazon Bedrock LLMs:** The core inference engine. It takes the retrieved context + user profile + user query to generate the final response.

* **Bottlenecks & Trade-offs:**
    * **Retrieval Precision:** "Garbage in, garbage out." If the OpenSearch index returns irrelevant Slack threads, the LLM will fail to generate a useful digest.
    * **Trade-off:** Using a managed service (Bedrock Knowledge Base) reduces operational overhead but limits control over low-level indexing parameters (like specific HNSW graph settings) compared to managing a raw OpenSearch cluster.

## 5. Safety & Governance (Amazon Guardrails)
* **Post-Inference Guardrails:** Situated strictly *after* the LLM inference but *before* the response reaches the user.
* **Function:** It scans the generated text for PII (Personally Identifiable Information), toxicity, and hallucination patterns (checking if the output is grounded in the retrieved context).

* **Bottlenecks & Trade-offs:**
    * **Latency Penalty:** This adds a final processing step, increasing end-to-end latency.
    * **False Positives:** Aggressive guardrails might filter out legitimate technical discussions (e.g., discussing "killing a process" in a Linux context might be flagged as violence by a poorly tuned model).