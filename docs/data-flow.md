# Data Flow Architecture: EverCurrent Daily Digest

This document outlines the end-to-end data flow within the EverCurrent ecosystem, covering ingestion, authentication, personalization, inference, and observability.

## 1. Asynchronous Data Ingestion (Knowledge Pipeline)
Before user interaction occurs, the system continuously aggregates knowledge from corporate sources to ensure the agent has access to the latest data.

* **Source:** Slack Workspaces and Company Documentation (e.g., Wikis, Drive).
* **Transport:** An AWS Lambda function triggers via a Cron Job to fetch relevant messages and documents.
* **Storage:** Raw data is stored in specific **Amazon S3** buckets ("Slack Messages" and "Company Docs").
* **Indexing:** **Amazon Bedrock Knowledge Base** ingests the data from S3, chunking and embedding it into **Amazon OpenSearch** to enable semantic retrieval.

## 2. User Authentication & Session Initialization
When a user initiates a session to request a digest:

1.  **Identity Verification:** The user authenticates via **Amazon Cognito**, which integrates with **AgentCore Identity** to validate access rights.
2.  **Context Loading:** Upon successful auth, the **AgentCore Runtime** initializes the **Daily Digest Agent**. It retrieves the session history and previous interaction context from **AgentCore Memory** to maintain conversation continuity.

## 3. Personalization & Context Retrieval (AgentCore Gateway)
To generate a *personalized* digest, the agent must first understand the specific employee's role and current focus.

1.  **Tool Invocation:** The Daily Digest Agent calls the **AgentCore Gateway**.
2.  **Profile Retrieval:** The Gateway triggers the `get_customer_profile()` tool (a sub-agent specialized in retrieval).
3.  **Data Access:** This tool accesses the persistent `Employee.md` file stored in **Amazon S3** via an AWS Lambda function.
4.  **Context Return:** The tool returns the employee's specific profile (e.g., "Mechanical Engineer," "Focus: Actuators") to the main agent.

## 4. Query Execution & Inference
With the user's profile context established, the agent generates the digest.

1.  **Knowledge Retrieval:** The agent invokes `get_messages()` and `read_docs()`.
    * These tools query the **Amazon Bedrock Knowledge Base**.
    * **Amazon OpenSearch** performs a vector search to find Slack messages and docs relevant to the user's specific profile context.
2.  **LLM Inference:** The retrieved context and user query are sent to **Amazon Bedrock LLMs** for processing and answer generation.
3.  **Safety Layer:** The raw model output is passed through **Amazon Guardrails** to filter hallucinations, toxicity, or PII before being returned to the runtime.

## 5. Profile Evolution (Learning Loop)
The system dynamically updates its understanding of the user based on the interaction.

1.  **Analysis:** If the user interaction reveals new priorities or role changes, the agent invokes the **AgentCore Gateway**.
2.  **Profile Update:** The Gateway triggers the `write_employee_info()` tool (a sub-agent).
3.  **Persistence:** An AWS Lambda function updates the specific `Employee.md` file in **Amazon S3**, ensuring the next session is even more personalized.

## 6. Observability
Throughout the entire lifecycle, the **AgentCore Runtime** emits telemetry data.

* **Tracing:** Agent traces (inputs, outputs, latency, tool usage) are sent to **AgentCore Observability** for monitoring system health and debugging.