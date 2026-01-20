from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
REGION = "us-west-2"

model = BedrockModel(
    model_id=MODEL_ID,
)


class DigestAgent:
    """Main digest generation agent with memory and personalization"""

    def __init__(self, memory_id: str, memory_client: MemoryClient):
        self.memory_id = memory_id
        self.memory_client = memory_client
        self.system_prompt = """You are a Daily Digest Agent for hardware engineering teams.
        
Your job is to create personalized, role-aware daily digests that help team members stay informed
about the most relevant updates in their projects and responsibilities.

When generating a digest, you should:
1. Prioritize information based on the user's role, active projects, and current phase
2. Highlight critical blockers and risks
3. Surface important decisions made
4. Identify actionable items requiring attention
5. Note significant changes from the previous day
6. Filter out noise and focus on signal

Be concise but comprehensive. Use clear sections and prioritize the most critical information first.
"""
        self.agent = Agent(
            model=model,
            tools=[
                self.get_user_preferences,
                self.get_slack_messages,
                self.search_company_docs,
                self.generate_digest_section,
            ],
            system_prompt=self.system_prompt,
        )

    @tool
    def get_user_preferences(self, user_id: str) -> dict:
        """Retrieve user preferences from long-term memory

        Args:
            user_id: The user identifier

        Returns:
            Dict containing user role, projects, preferences, and phase info
        """
        try:
            # Query long-term memory for user preferences
            namespace = f"/strategies/user_preferences/actors/{user_id}"

            memories = self.memory_client.retrieve_memories(
                memory_id=self.memory_id,
                namespace=namespace,
                query="user role projects preferences phase priorities",
            )

            # Parse and structure preferences
            preferences = {
                "role": "Unknown",
                "active_projects": [],
                "current_phase": "DVT",
                "muted_topics": [],
                "priority_keywords": [],
                "verbosity": "medium",
            }

            for memory in memories:
                content = memory.get("content", {})
                text = content.get("text", "")
                if "role:" in text.lower():
                    preferences["role"] = text.split("role:")[1].split("\n")[0].strip()
                if "projects:" in text.lower():
                    projects = text.split("projects:")[1].split("\n")[0].strip()
                    preferences["active_projects"] = [
                        p.strip() for p in projects.split(",")
                    ]
                if "phase:" in text.lower():
                    preferences["current_phase"] = (
                        text.split("phase:")[1].split("\n")[0].strip()
                    )

            logger.info(f"Retrieved preferences for {user_id}: {preferences}")
            return preferences

        except Exception as e:
            logger.error(f"Error retrieving preferences: {e}")
            return {"role": "Unknown", "active_projects": [], "current_phase": "DVT"}

    @tool
    def get_slack_messages(self, user_id: str, date: str, filters: dict) -> list:
        """Retrieve relevant Slack messages for the user

        Args:
            user_id: User identifier
            date: Date for messages (YYYY-MM-DD)
            filters: Dict with role, projects, phase for filtering

        Returns:
            List of relevant Slack messages
        """
        # This would integrate with your Slack data storage (S3/DDB/Vector)
        # For now, returning mock structure

        logger.info(
            f"Fetching Slack messages for {user_id} on {date} with filters: {filters}"
        )

        # Mock data - in production, this would query your Slack data plane
        messages = [
            {
                "channel": "#hardware-team",
                "author": "john.doe",
                "timestamp": f"{date}T10:30:00Z",
                "text": "EVT build showing 15% failure rate on power tests. Need ME review.",
                "reactions": ["⚠️", "👀"],
                "thread_replies": 5,
                "mentions": [user_id] if filters.get("role") == "ME" else [],
                "relevance_score": 0.95,
            },
            {
                "channel": "#project-apollo",
                "author": "jane.smith",
                "timestamp": f"{date}T14:15:00Z",
                "text": "Decision: Moving forward with supplier B for battery components",
                "reactions": ["✅"],
                "thread_replies": 2,
                "tags": ["decision", "supply-chain"],
                "relevance_score": 0.88,
            },
        ]

        # Filter by relevance to user's role and projects
        filtered = [
            msg
            for msg in messages
            if any(
                proj in msg.get("channel", "")
                for proj in filters.get("active_projects", [])
            )
            or user_id in msg.get("mentions", [])
            or msg.get("relevance_score", 0) > 0.85
        ]

        return filtered

    @tool
    def search_company_docs(self, query: str, filters: dict = None) -> list:  # type: ignore
        """Search company documents for relevant context

        Args:
            query: Search query
            filters: Optional filters for document type, project, etc.

        Returns:
            List of relevant document excerpts
        """
        logger.info(f"Searching company docs: {query}")

        # This would integrate with Bedrock Knowledge Base or OpenSearch
        # Mock response for now
        return [
            {
                "title": "DVT Phase Guidelines",
                "excerpt": "During DVT, focus on design validation and supplier qualification...",
                "source": "s3://company-docs/processes/dvt-guidelines.pdf",
                "relevance": 0.92,
            }
        ]

    @tool
    def generate_digest_section(
        self, section_type: str, content: list, user_prefs: dict
    ) -> str:
        """Generate a specific section of the digest

        Args:
            section_type: Type of section (highlights, blockers, decisions, actions)
            content: Raw content to process
            user_prefs: User preferences for personalization

        Returns:
            Formatted section text
        """
        logger.info(f"Generating {section_type} section")

        # Use the agent to intelligently format the section
        section_prompt = f"""
        Create a {section_type} section for the daily digest.
        User role: {user_prefs.get('role')}
        Current phase: {user_prefs.get('current_phase')}
        
        Raw content:
        {json.dumps(content, indent=2)}
        
        Format this into a clear, actionable {section_type} section.
        Be concise but informative. Prioritize by importance.
        """

        response = self.agent(section_prompt)
        return response.message["content"][0]["text"]  # type: ignore


@app.entrypoint
def generate_daily_digest(payload: dict) -> dict:
    """
    Main entry point for digest generation

    Payload structure:
    {
        "user_id": "emp_12345",
        "date": "2026-01-20",
        "action": "generate" | "query"
        "query": "optional question about digest" (for Q&A mode)
    }
    """
    try:
        user_id = payload.get("user_id")
        date = payload.get("date", datetime.now().strftime("%Y-%m-%d"))
        action = payload.get("action", "generate")

        # Initialize memory client (would be configured during deployment)
        memory_client = MemoryClient(region_name=REGION)

        # Get or create memory resource for digests
        # In production, this would be pre-created
        memory_id = "daily-digest-memory"  # This should be from environment/config

        # Initialize digest agent
        digest_agent = DigestAgent(memory_id, memory_client)

        if action == "generate":
            # Generate digest workflow
            logger.info(f"Generating digest for {user_id} on {date}")
            user_prefs = digest_agent.get_user_preferences(user_id=user_id)  # type: ignore
            slack_messages = digest_agent.get_slack_messages(  # type: ignore
                user_id=user_id, date=date, filters=user_prefs
            )
            digest = {
                "user_id": user_id,
                "date": date,
                "role": user_prefs["role"],
                "phase": user_prefs["current_phase"],
                "generated_at": datetime.now().isoformat(),
                "sections": {},
            }
            sections_to_generate = [
                ("highlights", "Key highlights and updates"),
                ("blockers", "Blockers and risks requiring attention"),
                ("decisions", "Important decisions made"),
                ("actions", "Action items for you"),
            ]

            for section_name, section_desc in sections_to_generate:
                section_content = digest_agent.generate_digest_section(  # type: ignore
                    section_type=section_name,
                    content=slack_messages,
                    user_prefs=user_prefs,
                )
                digest["sections"][section_name] = section_content

            # TODO: Store digest for future retrieval
            # This would go to S3 + DynamoDB + Vector index

            logger.info(f"Successfully generated digest for {user_id}")

            return {"status": "success", "digest": digest}

        elif action == "query":
            # Q&A mode - answer questions about digests
            query = payload.get("query", "")
            logger.info(f"Answering query for {user_id}: {query}")

            # This would:
            # 1. Retrieve relevant digests from vector store
            # 2. Load context from long-term memory
            # 3. Use agent to answer question with citations

            response = digest_agent.agent(
                f"User {user_id} asks: {query}\n\n"
                f"Provide an answer based on their recent digests and Slack activity."
            )

            return {
                "status": "success",
                "answer": response.message["content"][0]["text"],  # type: ignore
            }

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Error in digest generation: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    app.run()
