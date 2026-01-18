"""End-to-end test for ConvoAgent and full chat workflow."""

import os
from unittest.mock import patch, MagicMock

# Import agents package to ensure registration
import src.agents  # noqa: F401
from src.core import AgentFactory


def main():
    """Run end-to-end test of the conversation workflow."""
    print("=" * 60)
    print("ConvoAgent End-to-End Test - Full Chat Workflow")
    print("=" * 60)

    # Mock environment variables and AI client
    with patch.dict(
        os.environ,
        {
            "ANTHROPIC_API_KEY": "test-key",
            "GEMINI_API_KEY": "test-key",
            "OPENAI_API_KEY": "test-key",
        },
    ):
        with patch("src.core.agent.AIClientWrapper") as mock_client:
            # Setup mock client
            mock_client_instance = MagicMock()
            mock_client_instance.current_provider = "claude"
            mock_client_instance.get_default_model.return_value = (
                "claude-3-5-sonnet-20241022"
            )

            # Mock LLM responses
            def create_mock_response(content):
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = content
                return mock_response

            # Setup different responses for different inputs
            mock_client_instance.chat_completion.side_effect = [
                create_mock_response("I'm Claude, an AI assistant."),
                create_mock_response("Python is a versatile programming language."),
            ]

            mock_client.return_value = mock_client_instance

            # Test 1: Create ConvoAgent with router
            print("\n1. Creating ConvoAgent with router enabled...")
            convo = AgentFactory.create("convo", provider="claude", use_router=True)
            print(f"   ✓ ConvoAgent created: {convo}")

            # Test 2: Check routing to specialized agent
            print("\n2. Testing routing to specialized agent (hello_agent)...")
            response1 = convo.run("hello world")
            print(f"   Input: 'hello world'")
            print(f"   Output: '{response1}'")
            assert response1 == "hello", f"Expected 'hello', got '{response1}'"

            # Check routing stats
            context = convo.get_conversation_context()
            print(f"   Routed to: {context['last_route']['agent']}")
            print(f"   Confidence: {context['last_route']['confidence']:.2f}")
            assert context["last_route"]["agent"] == "hello_agent"
            print("   ✓ Successfully routed to specialized agent")

            # Test 3: Fallback to LLM for non-specialized input
            print("\n3. Testing LLM fallback for general conversation...")
            response2 = convo.run("who are you?")
            print(f"   Input: 'who are you?'")
            print(f"   Output: '{response2}'")
            assert (
                "Claude" in response2
            ), f"Expected LLM response with 'Claude', got '{response2}'"
            print("   ✓ Successfully fell back to LLM conversation")

            # Test 4: Create ConvoAgent without router
            print("\n4. Creating ConvoAgent without router...")
            convo_no_router = AgentFactory.create(
                "convo", provider="claude", use_router=False
            )
            response3 = convo_no_router.run("tell me about Python")
            print(f"   Input: 'tell me about Python'")
            print(f"   Output: '{response3}'")
            assert (
                "Python" in response3
            ), f"Expected response about Python, got '{response3}'"
            print("   ✓ Direct LLM conversation works without router")

            # Test 5: Conversation history
            print("\n5. Testing conversation history...")
            print(f"   ConvoAgent history length: {len(convo.history)}")
            assert len(convo.history) >= 1, "History should have at least one entry"
            print("   ✓ Conversation history is maintained")

            # Test 6: Conversation context
            print("\n6. Checking conversation context...")
            context = convo.get_conversation_context()
            print(f"   Provider: {context['provider']}")
            print(f"   Model: {context['model']}")
            print(f"   Router enabled: {context['router_enabled']}")
            print(f"   History length: {context['history_length']}")
            assert context["router_enabled"] is True
            assert context["provider"] == "claude"
            print("   ✓ Conversation context correctly tracked")

            # Test 7: Reset conversation
            print("\n7. Testing conversation reset...")
            initial_history_len = len(convo.history)
            convo.reset_conversation()
            print(f"   History length before reset: {initial_history_len}")
            print(f"   History length after reset: {len(convo.history)}")
            assert len(convo.history) == 0, "History should be empty after reset"
            print("   ✓ Conversation reset successful")

            # Test 8: Verify agent registration
            print("\n8. Verifying agent registrations...")
            agents = AgentFactory.list_agents()
            print(f"   Registered agents: {agents}")
            assert "convo" in agents
            assert "router" in agents
            assert "hello_agent" in agents
            print("   ✓ All agents properly registered")

            # Test 9: Check routable agents
            print("\n9. Checking routable agents...")
            routable = AgentFactory.get_routable_agents()
            print(f"   Routable agents: {list(routable.keys())}")
            assert "hello_agent" in routable, "hello_agent should be routable"
            assert "convo" not in routable, "convo should not be routable"
            assert "router" not in routable, "router should not be routable"
            print("   ✓ Routing configuration correct")

            # Test 10: Workflow summary
            print("\n10. Workflow Summary:")
            print("   ┌─────────────────────────────────────────┐")
            print("   │           ConvoAgent Workflow           │")
            print("   └─────────────────────────────────────────┘")
            print("   ")
            print("   User Input")
            print("      ↓")
            print("   ConvoAgent (Entry Point)")
            print("      ↓")
            print("   Router checks for specialized agents")
            print("      ↓")
            print("   ┌────────────┬────────────────────┐")
            print("   │ High Conf. │ Low Conf./No Match │")
            print("   ↓            ↓                    │")
            print("   Specialized  Direct LLM ←────────┘")
            print("   Agent        Conversation")
            print("      ↓            ↓")
            print("   Response    Response")
            print("   ")

    print("\n" + "=" * 60)
    print("✓ All tests passed! Full chat workflow is working correctly")
    print("=" * 60)


if __name__ == "__main__":
    main()
