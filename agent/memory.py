"""
Memory Setup and Hook Providers for Daily Digest System

This module sets up AgentCore Memory with appropriate strategies and
provides hook providers for automatic memory management.
"""

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from strands.events import (
    AgentInitializedEvent,
    MessageAddedEvent,
    AfterInvocationEvent,
    HookProvider,
    HookRegistry,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DigestMemorySetup:
    """Handles creation and configuration of AgentCore Memory for digests"""

    def __init__(self, region: str = "us-west-2"):
        self.client = MemoryClient(region_name=region)
        self.region = region

    def create_digest_memory(self, memory_name: str = "DailyDigestMemory") -> str:
        """
        Create memory resource with appropriate strategies for digest system

        Returns:
            memory_id: The ID of the created memory resource
        """

        strategies = [
            {
                StrategyType.USER_PREFERENCE.value: {
                    "name": "DigestUserPreferences",
                    "description": "Captures user preferences, role, projects, and personalization settings",
                    "namespaces": [
                        "/strategies/{memoryStrategyId}/actors/{actorId}/preferences"
                    ],
                }
            },
            {
                StrategyType.SEMANTIC.value: {
                    "name": "DigestSemanticMemory",
                    "description": "Stores facts about projects, decisions, and key events",
                    "namespaces": [
                        "/strategies/{memoryStrategyId}/actors/{actorId}/facts"
                    ],
                }
            },
            {
                StrategyType.SUMMARY.value: {
                    "name": "DigestSessionSummary",
                    "description": "Maintains summaries of digest generation sessions and Q&A interactions",
                    "namespaces": [
                        "/strategies/{memoryStrategyId}/actors/{actorId}/sessions/{sessionId}/summary"
                    ],
                }
            },
        ]

        try:
            # Create memory resource
            memory = self.client.create_memory_and_wait(
                name=memory_name,
                strategies=strategies,
                description="Memory system for Daily Digest Agent with user preferences, facts, and summaries",
                event_expiry_days=30,  # Keep events for 90 days
            )

            memory_id = memory["id"]
            logger.info(f"✅ Created memory resource: {memory_id}")
            return memory_id

        except Exception as e:
            if "already exists" in str(e):
                # Memory exists, retrieve ID
                memories = self.client.list_memories()
                memory_id = next(
                    (m["id"] for m in memories if m.get("name") == memory_name), None
                )
                logger.info(f"Memory already exists: {memory_id}")
                return memory_id  # type: ignore
            else:
                logger.error(f"Failed to create memory: {e}")
                raise


class DigestMemoryHookProvider(HookProvider):
    """
    Hook provider for automatic memory management in digest agent

    This handles:
    - Loading user context and preferences when agent initializes
    - Storing conversation events
    - Managing short-term and long-term memory
    """

    def __init__(self, memory_id: str, region: str = "us-west-2"):
        self.memory_id = memory_id
        self.client = MemoryClient(region_name=region)

    def on_agent_initialized(self, event: AgentInitializedEvent):
        """Load user preferences and recent context when agent starts"""
        try:
            actor_id = event.agent.state.get("actor_id")
            session_id = event.agent.state.get("session_id")

            if not actor_id or not session_id:
                logger.warning("Missing actor_id or session_id in agent state")
                return

            namespace = f"/strategies/user_preferences/actors/{actor_id}"

            preferences = self.client.retrieve_memories(
                memory_id=self.memory_id,
                namespace=namespace,
                query="user role projects preferences phase priorities verbosity",
            )

            recent_events = self.client.get_last_k_turns(
                memory_id=self.memory_id, actor_id=actor_id, session_id=session_id, k=5
            )

            context_parts = []

            if preferences:
                context_parts.append("## User Profile")
                for pref in preferences[:3]:  # Top 3 most relevant
                    content = pref.get("content", {})
                    text = content.get("text", "")
                    if text:
                        context_parts.append(text)

            if recent_events:
                context_parts.append("\n## Recent Conversation")
                for turn in recent_events:
                    for msg in turn:
                        role = msg["role"]
                        text = msg["content"]["text"]
                        context_parts.append(f"{role}: {text}")

            if context_parts:
                context = "\n".join(context_parts)
                # Inject context into system prompt
                event.agent.system_prompt += f"\n\n{context}"
                logger.info(f"✅ Loaded context for {actor_id}")

        except Exception as e:
            logger.error(f"Error loading agent context: {e}", exc_info=True)

    def on_message_added(self, event: MessageAddedEvent):
        """Store new messages in short-term memory"""
        try:
            messages = event.agent.messages
            if not messages:
                return

            last_message = messages[-1]
            actor_id = event.agent.state.get("actor_id")
            session_id = event.agent.state.get("session_id")

            if not actor_id or not session_id:
                return

            role = last_message.get("role", "").upper()
            content = last_message.get("content", [{}])[0].get("text", "")

            if not content or "toolResult" in last_message.get("content", [{}])[0]:
                return  # Skip tool results

            # Store in memory
            self.client.create_event(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                messages=[(content, role)],
            )

            logger.info(f"Stored message for {actor_id}")

        except Exception as e:
            logger.error(f"Error storing message: {e}", exc_info=True)

    def register_hooks(self, registry: HookRegistry):
        """Register memory hooks with the agent"""
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        logger.info("Memory hooks registered")


class DigestStorageMemoryHook(HookProvider):
    """
    Specialized hook for storing generated digests as structured memories

    This stores completed digests as semantic memories that can be
    retrieved and queried later.
    """

    def __init__(self, memory_id: str, region: str = "us-west-2"):
        self.memory_id = memory_id
        self.client = MemoryClient(region_name=region)

    def on_after_invocation(self, event: AfterInvocationEvent):
        """Store generated digest as a structured memory"""
        try:
            # Check if this was a digest generation
            agent_state = event.agent.state
            action = agent_state.get("action")

            if action != "generate":
                return  # Only store actual digest generations

            actor_id = agent_state.get("actor_id")
            session_id = agent_state.get("session_id")
            digest_date = agent_state.get("digest_date")

            if not all([actor_id, session_id, digest_date]):
                return

            # Get the generated digest from the last message
            messages = event.agent.messages
            if messages and messages[-1]["role"] == "assistant":
                digest_content = messages[-1]["content"][0].get("text", "")

                # Store as a structured event with metadata
                self.client.create_event(
                    memory_id=self.memory_id,
                    actor_id=actor_id,
                    session_id=f"digest-{digest_date}",  # Unique session per digest
                    messages=[
                        (
                            f"Daily Digest for {digest_date}:\n{digest_content}",
                            "ASSISTANT",
                        )
                    ],
                )

                logger.info(f"✅ Stored digest for {actor_id} on {digest_date}")

        except Exception as e:
            logger.error(f"Error storing digest: {e}", exc_info=True)

    def register_hooks(self, registry: HookRegistry):
        """Register digest storage hook"""
        registry.add_callback(AfterInvocationEvent, self.on_after_invocation)


if __name__ == "__main__":
    # Initialize memory setup
    setup = DigestMemorySetup(region="us-west-2")
    # Create memory resource
    memory_id = setup.create_digest_memory("DailyDigestMemory")

    print(f"\nMemory setup complete!")
    print(f"Memory ID: {memory_id}")
    print(f"\nMemory includes:")
    print("  - User preference strategy (role, projects, phase)")
    print("  - Semantic memory (facts, decisions, events)")
    print("  - Summary strategy (session summaries)")
