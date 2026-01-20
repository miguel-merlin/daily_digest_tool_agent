import logging
from strands.hooks.registry import HookProvider, HookRegistry
from strands.hooks.events import AgentInitializedEvent, MessageAddedEvent
from bedrock_agentcore.memory import MemoryClient

logger = logging.getLogger(__name__)
K_DEFAULT_TURNS = 5


class MemoryHookProvider(HookProvider):

    def __init__(self, memory_client: MemoryClient, memory_id: str) -> None:
        super().__init__()
        self.memory_client = memory_client
        self.memory_id = memory_id

    def on_agent_initialized(self, event: AgentInitializedEvent) -> None:
        """Load recent conversation history when agent starts"""
        try:
            # Get session info from agent state
            actor_id = event.agent.state.get("actor_id")
            session_id = event.agent.state.get("session_id")
            if not actor_id or not session_id:
                logger.warning("Actor ID or Session ID not found in agent state.")
                return
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                k=K_DEFAULT_TURNS,
            )
            if recent_turns:
                context_messages = []
                for turn in recent_turns:
                    for message in turn:
                        role = message.get("role")
                        content = (message.get("content") or {}).get("text", "")
                        context_messages.append(f"{role}: {content}")
                context_str = "\n".join(context_messages)
                if not event.agent.system_prompt:
                    event.agent.system_prompt = ""
                event.agent.system_prompt += (
                    f"\n\nRecent conversation history:\n{context_str}"
                )
                logger.info("Loaded recent conversation history into system prompt.")
        except Exception as e:
            logger.error(f"Failed to load recent conversation history: {e}")

    def on_message_added(self, event: MessageAddedEvent):
        """Store messages in memory"""
        messages = event.agent.messages
        try:
            actor_id = event.agent.state.get("actor_id")
            session_id = event.agent.state.get("session_id")
            if messages[-1]["content"][0].get("text"):
                message = messages[-1]["content"][0]
                message_text = message.get("text", "")
                self.memory_client.store_message(
                    memory_id=self.memory_id,
                    actor_id=actor_id,
                    session_id=session_id,
                    message=[(message_text, messages[-1]["role"])],
                )
                logger.info("Stored new message in memory.")
        except Exception as e:
            logger.error(f"Failed to store message in memory: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
