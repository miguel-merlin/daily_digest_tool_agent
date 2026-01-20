# System Overview: EverCurrent Daily Digest Tool

## 1. Overview
The EverCurrent Daily Digest Tool is an intelligent agentic solution designed to assist robotics hardware engineering teams (mechanical, electrical, supply chain, etc.). The system addresses knowledge silos caused by high-volume Slack communication by generating personalized digests that adapt to each user's changing priorities and project phases. The goal is to align the team on execution through targeted information surfacing.

## 2. High-Level Architecture
The system is built on **AWS** and deployed using the **AgentCore Runtime**. It operates as a **LangChain agent** that orchestrates information retrieval, user profiling, and safety checks to generate digests.

![System Architecture](./assets/diagram.png)


### Core Components
* **Runtime:** AgentCore Runtime (hosts the Daily Digest Agent).
* **Inference:** Amazon Bedrock LLMs provide the reasoning backbone.
* **Knowledge Base:** Amazon OpenSearch and Amazon Bedrock Knowledge Base serve as the retrieval engines.
* **Identity:** Amazon Cognito handles user authentication.
* **Observability:** AgentCore Observability captures agent traces.

## 3. The Daily Digest Agent
The central component is a context-aware agent capable of reasoning over user requests. It leverages **AgentCore Memory** to maintain short-term execution context and long-term history across sessions.

### Primary Tools
The agent utilizes two primary tools for information retrieval:
1.  **`get_messages()`**: Retrieves relevant Slack conversations. Messages are ingested into an S3 bucket via an AWS Lambda cron job and indexed by Amazon Bedrock Knowledge Base for OpenSearch retrieval.
2.  **`read_docs()`**: Fetches relevant company documentation. These documents follow a similar ingestion pipeline (S3 to OpenSearch) to provide technical context.

## 4. The AgentCore Gateway (Personalization Engine)
The architecture features an innovative **AgentCore Gateway** to manage dynamic user context. Instead of static profiles, the system maintains a living Markdown (`.md`) file for each employee.

### Sub-Agent Workflow
* **`write_employee_info()`**: An agent responsible for updating the `Employee.md` file. It records relevant employee information, ensuring the system's understanding of the user evolves over time.
* **`get_customer_profile()`**: An agent that reads the `Employee.md` file to extract specific context (role, current focus) to satisfy the user's digest request.

## 5. Safety & Reliability
* **Amazon Guardrails:** A post-inference safety layer ensures that hallucinations are filtered and no harmful or sensitive content reaches the user.
* **Observability:** The AgentCore Observability service traces agent interactions and tool usage for monitoring and debugging.