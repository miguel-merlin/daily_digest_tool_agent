# System Architecture: EverCurrent Daily Digest Agent

The EverCurrent Digest Tool is a **Multi-Agent System** deployed on **AWS Bedrock AgentCore**. It solves the "knowledge silo" problem in hardware engineering by transforming high-volume, unstructured Slack data into hyper-personalized, role-specific daily briefs.

Unlike standard summary bots, this system uses **active reasoning** to determine *relevance* based on a user's changing role and project phase (e.g., "PVT Critical" vs. "Concept Phase").

## Core Architectural Patterns
This architecture is built on five specific advanced patterns from the provided text:

1.  **Orchestrator-Workers:** A central "Supervisor" agent manages specialized sub-agents (Mechanical, Supply Chain, Firmware) to ensure domain expertise.
2.  **Reflective Processing:** A dedicated "Critic" step reviews generated digests against the user's persona to minimize hallucination and noise.
3.  **Dynamic Memory:** The system maintains a stateful "User Profile" that evolves based on feedback (e.g., "Stop showing me minor firmware bug reports").
4.  **Resource-Aware Optimization:** We use a **LiteLLM Gateway** to route "bulk" processing tasks (filtering 10k messages) to faster/cheaper models (Claude 3 Haiku) while reserving reasoning tasks for stronger models (Claude 3.5 Sonnet).
5.  **Observability:** Deep tracing via **Langfuse** on AWS to debug *why* a specific piece of information was deemed "relevant" or "irrelevant."

## AWS Infrastructure Topology
The system is deployed using cdk with the following components:

* **Runtime:** AWS Bedrock AgentCore (Containerized Agent).
* **Model Gateway:** LiteLLM (Self-hosted on AWS) balancing requests between Bedrock and other providers if needed.
* **Knowledge Store:** Amazon Bedrock Knowledge Bases (Vector Search) for retrieving project specs and historical context (RAG).
* **Safety Layer:** Amazon Bedrock Guardrails for PII redaction (sanitizing Slack messages) and toxicity filtering.
* **Frontend:** Custom Streamlit UI (Fargate/Local) for persona management and simulation.