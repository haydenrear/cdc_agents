import os
import shutil
import time
import json
import datetime
from pathlib import Path
from typing import Any, Dict, AsyncIterable, List, Optional, Union, Callable, Tuple

import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.human_delegate_config_props import HumanDelegateConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from langchain_core.tools import tool


def produce_initialize_session(config_props: HumanDelegateConfigProps):
    """Factory function that produces the bootstrap_ai_character tool with injected configuration."""
    
    @tool
    def initialize_session(session_id: str, description: str) -> Dict[str, Any]:
        """Initialize an AI character for human delegation interactions.
        
        This tool sets up the necessary directory structure and configuration for 
        a session where an AI character can interact with human delegates.
        
        Args:
            session_id: The unique session identifier (previously called character_name)
            description: A brief description of the character's purpose and capabilities
            
        Returns:
            A dictionary containing status of the initialization and session details
        """
        # Create base directory for human delegate interactions
        base_dir = Path(config_props.base_dir)
        character_dir = base_dir / session_id
        
        # Create directory structure
        os.makedirs(character_dir, exist_ok=True)
        os.makedirs(character_dir / "messages", exist_ok=True)
        os.makedirs(character_dir / "screens", exist_ok=True)
        
        # Create session config file
        character_config = {
            "session_id": session_id,
            "description": description,
            "created_at": datetime.datetime.now().isoformat(),
            "last_active": datetime.datetime.now().isoformat(),
            "status": "active"
        }
        
        with open(character_dir / "config.json", "w") as f:
            json.dump(character_config, f, indent=2)
        
        return {
            "status": "success",
            "message": f"Session '{session_id}' has been initialized",
            "session": character_config
        }
    
    return initialize_session

def produce_message_human_delegate(config_props: HumanDelegateConfigProps):
    """Factory function that produces the message_human_delegate tool with injected configuration."""
    
    @tool
    def message_human_delegate(session_id: str, message: str, message_type: str = "text") -> Dict[str, Any]:
        """Send a message to a human delegate.
        
        This tool saves a message to a file that can be read by the human delegate.
        The message is timestamped and stored in the session's messages directory.
        
        Args:
            session_id: The unique session identifier
            message: The content of the message to send
            message_type: The type of message (text, request, alert, etc.)
            
        Returns:
            A dictionary containing status of the message delivery and message details
        """
        # Ensure session exists
        base_dir = Path(config_props.base_dir)
        character_dir = base_dir / session_id
        
        if not character_dir.exists():
            return {
                "status": "error",
                "message": f"Session '{session_id}' does not exist. Please use bootstrap_ai_character first."
            }
        
        # Create message with metadata
        message_data = {
            "session_id": session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "type": message_type,
            "content": message,
            "id": f"msg_{int(time.time())}_{hash(message) % 10000}",
            "source": "ai"
        }
        
        # Save message to file
        message_file = character_dir / "messages" / f"{message_data['id']}.json"
        with open(message_file, "w") as f:
            json.dump(message_data, f, indent=2)
        
        # Update character's last active timestamp
        try:
            with open(character_dir / "config.json", "r") as f:
                config = json.load(f)
            
            config["last_active"] = datetime.datetime.now().isoformat()
            
            with open(character_dir / "config.json", "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            return {
                "status": "warning",
                "message": f"Message saved but failed to update character config: {str(e)}",
                "message_id": message_data["id"]
            }
        
        return {
            "status": "success",
            "message": "Message sent to human delegate",
            "message_id": message_data["id"],
            "timestamp": message_data["timestamp"]
        }
    
    return message_human_delegate

def produce_finalize_session(config_props: HumanDelegateConfigProps):
    """Factory function that produces the finalize_session tool with injected configuration."""
    
    @tool
    def finalize_session(session_id: str, clean_files: Optional[bool] = None) -> Dict[str, Any]:
        """Finalize a human delegate session and optionally clean up session files.
        
        This tool marks the session as complete in the config file and can optionally
        remove or archive the session files when they are no longer needed.
        
        Args:
            session_id: The unique session identifier
            clean_files: If True, will remove all session files; if False, just marks session as complete.
                        If not provided, uses the default from configuration.
            
        Returns:
            A dictionary containing status of the finalization operation
        """
        # Use config default if not explicitly provided
        if clean_files is None:
            clean_files = config_props.session_cleanup_on_finalize
            
        # Ensure session exists
        base_dir = Path(config_props.base_dir)
        character_dir = base_dir / session_id
        
        if not character_dir.exists():
            return {
                "status": "error",
                "message": f"Session '{session_id}' does not exist."
            }
        
        # Update the session config to mark it as complete
        config_file = character_dir / "config.json"
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            config["completed_at"] = datetime.datetime.now().isoformat()
            config["status"] = "completed"
            
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to update session config: {str(e)}"
            }
        
        # Optionally clean up files
        if clean_files:
            try:
                # Remove all session files and directories
                shutil.rmtree(character_dir)
                return {
                    "status": "success",
                    "message": f"Session '{session_id}' has been finalized and all files have been removed."
                }
            except Exception as e:
                return {
                    "status": "warning",
                    "message": f"Session '{session_id}' has been marked as complete, but file cleanup failed: {str(e)}"
                }
        
        return {
            "status": "success",
            "message": f"Session '{session_id}' has been finalized and marked as complete."
        }
    
    return finalize_session

def produce_wait_for_messages(config_props: HumanDelegateConfigProps):
    """Factory function that produces the wait_for_next_messages tool with injected configuration."""
    
    @tool
    def wait_for_next_messages(session_id: str, since_timestamp: Optional[str] = None,
                          timeout_seconds: Optional[int] = None, 
                          poll_interval: Optional[int] = None,
                          min_messages: Optional[int] = None) -> Dict[str, Any]:
        """Wait for new messages from a human delegate.
        
        This tool polls the messages directory for the specified session and returns
        any new messages that were created after the specified timestamp. It can optionally
        wait for a specified amount of time for messages to appear.
        
        Args:
            session_id: The unique session identifier to check messages for
            since_timestamp: Optional ISO-format timestamp to filter messages after this time
            timeout_seconds: Optional number of seconds to wait for messages to appear
                            (defaults to configuration setting)
            poll_interval: Seconds to wait between polling attempts (defaults to configuration setting)
            min_messages: Minimum number of new messages required (defaults to configuration setting)
            
        Returns:
            A dictionary containing new messages and their metadata
        """
        # Use configuration defaults if not specified
        if timeout_seconds is None:
            timeout_seconds = config_props.default_timeout_seconds
        if poll_interval is None:
            poll_interval = config_props.default_poll_interval
        if min_messages is None:
            min_messages = config_props.min_messages_required
            
        # Ensure session exists
        base_dir = Path(config_props.base_dir)
        character_dir = base_dir / session_id
        
        if not character_dir.exists():
            return {
                "status": "error",
                "message": f"Session '{session_id}' does not exist. Please use bootstrap_ai_character first."
            }
        
        # Get messages directory
        messages_dir = character_dir / "messages"
        if not messages_dir.exists():
            return {
                "status": "error",
                "message": f"Messages directory for session '{session_id}' does not exist."
            }
        
        # Parse the since_timestamp if provided
        filter_time = None
        if since_timestamp:
            try:
                filter_time = datetime.datetime.fromisoformat(since_timestamp)
            except ValueError:
                return {
                    "status": "error",
                    "message": f"Invalid timestamp format: {since_timestamp}. Expected ISO format."
                }
        
        # Check for messages with optional timeout
        start_time = time.time()
        max_attempts = config_props.max_wait_attempts
        attempts = 0
        
        while attempts < max_attempts and (time.time() - start_time < timeout_seconds):
            attempts += 1
            
            # Collect all human-originated message files
            messages = []
            message_files = list(messages_dir.glob("*.json"))
            
            for message_file in message_files:
                try:
                    with open(message_file, "r") as f:
                        message_data = json.load(f)
                    
                    # Only consider messages from human (not sent by AI)
                    if message_data.get("source", "") == "ai":
                        continue
                        
                    # Filter by timestamp if needed
                    if filter_time:
                        message_time = datetime.datetime.fromisoformat(message_data["timestamp"])
                        if message_time <= filter_time:
                            continue
                    
                    messages.append(message_data)
                except Exception:
                    # Skip invalid files
                    continue
            
            # Sort messages by timestamp
            messages.sort(key=lambda x: x["timestamp"])
            
            # If we have enough messages, return results
            if len(messages) >= min_messages:
                # Update the last activity timestamp
                try:
                    config_file = character_dir / "config.json"
                    with open(config_file, "r") as f:
                        config = json.load(f)
                    
                    config["last_active"] = datetime.datetime.now().isoformat()
                    
                    with open(config_file, "w") as f:
                        json.dump(config, f, indent=2)
                except Exception:
                    pass  # Don't fail if we can't update the timestamp
                
                return {
                    "status": "success",
                    "message": f"Found {len(messages)} new message(s).",
                    "message_count": len(messages),
                    "messages": messages,
                    "latest_timestamp": messages[-1]["timestamp"] if messages else None
                }
            
            # If still waiting for messages, sleep before checking again
            time.sleep(poll_interval)
        
        # If we get here, we timed out waiting for messages
        return {
            "status": "timeout",
            "message": f"Waited {timeout_seconds} seconds but found only {len(messages)} messages (expected at least {min_messages}).",
            "message_count": len(messages),
            "messages": messages,
            "latest_timestamp": messages[-1]["timestamp"] if messages else None
        }
    
    return wait_for_next_messages

def produce_handle_message(config_props: HumanDelegateConfigProps):
    """Factory function that produces the handle_message tool with injected configuration."""
    
    def _handle_text_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a text message from the human delegate."""
        return {
            "status": "success",
            "message_type": "text",
            "content": message_data.get("content", ""),
            "message_id": message_data.get("id", ""),
            "timestamp": message_data.get("timestamp", "")
        }
    
    def _handle_image_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an image message from the human delegate."""
        return {
            "status": "success",
            "message_type": "image",
            "image_url": message_data.get("content", {}).get("url", ""),
            "caption": message_data.get("content", {}).get("caption", ""),
            "message_id": message_data.get("id", ""),
            "timestamp": message_data.get("timestamp", "")
        }
    
    def _handle_video_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a video message from the human delegate."""
        return {
            "status": "success",
            "message_type": "video",
            "video_url": message_data.get("content", {}).get("url", ""),
            "caption": message_data.get("content", {}).get("caption", ""),
            "message_id": message_data.get("id", ""),
            "timestamp": message_data.get("timestamp", "")
        }
    
    def _handle_file_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a file message from the human delegate."""
        return {
            "status": "success",
            "message_type": "file",
            "file_url": message_data.get("content", {}).get("url", ""),
            "filename": message_data.get("content", {}).get("filename", ""),
            "message_id": message_data.get("id", ""),
            "timestamp": message_data.get("timestamp", "")
        }
    
    @tool
    def handle_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message received from a human delegate based on its type. It handles the messages retrieved from the wait_for_next_messages function.
        
        This tool analyzes the message content and delegates to specialized handlers
        based on the message type (text, image, video, file, etc.).
        
        Args:
            message_data: The message data to process, containing type, content, and metadata
            
        Returns:
            A dictionary with processed message information based on its type
        """
        message_type = message_data.get("type", "text")
        
        # Route to appropriate handler based on message type
        if message_type == "text":
            return _handle_text_message(message_data)
        elif message_type == "image":
            return _handle_image_message(message_data)
        elif message_type == "video":
            return _handle_video_message(message_data)
        elif message_type == "file":
            return _handle_file_message(message_data)
        else:
            # Default to basic handler for unknown types
            return {
                "status": "warning",
                "message": f"Received message of unknown type: {message_type}",
                "message_id": message_data.get("id", ""),
                "timestamp": message_data.get("timestamp", ""),
                "content": message_data.get("content", ""),
                "message_type": message_type
            }
    
    return handle_message

@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class HumanDelegateAgent(DeepResearchOrchestrated, A2AReactAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, 
                 model_provider: ModelProvider, config_props: HumanDelegateConfigProps):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(
            self, agent_config,
            [
                produce_initialize_session(config_props),
                produce_message_human_delegate(config_props),
                produce_wait_for_messages(config_props),
                produce_handle_message(config_props),
                produce_finalize_session(config_props)
            ],
            self_card.agent_descriptor.system_prompts, memory_saver, model_provider)
        
        self.agent_config: AgentCardItem = self_card
        self.config_props = config_props


