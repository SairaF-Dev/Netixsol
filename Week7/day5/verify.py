#!/usr/bin/env python
"""Day 5 Bootstrap Verification Script"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def verify_imports():
    """Verify all core modules can be imported."""
    print("Checking imports...")
    
    try:
        from day5_langgraph import (
            AgentState,
            AgentConfig,
            ConversationStage,
            UserIntent,
            create_initial_state,
            ToolExecutor,
            TOOLS_DEFINITION,
        )
        print("✅ All core imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def verify_configuration():
    """Verify configuration system."""
    print("Checking configuration...")
    
    try:
        from day5_langgraph import AgentConfig
        config = AgentConfig.from_env()
        
        # Check key fields
        assert config.openai_model is not None
        assert config.day4_api_url is not None
        assert config.log_level is not None
        
        print(f"✅ Configuration loaded (model={config.openai_model})")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def verify_state_machine():
    """Verify state machine setup."""
    print("Checking state machine...")
    
    try:
        from day5_langgraph import (
            create_initial_state,
            ConversationStage,
            UserIntent,
        )
        
        state = create_initial_state()
        
        # Verify initial state
        assert state.conversation_stage == ConversationStage.GREETING
        assert isinstance(state.messages, list)
        assert state.current_intent is None
        
        # Verify enums have values
        assert hasattr(ConversationStage, 'GREETING')
        assert hasattr(UserIntent, 'BUYER_INQUIRY')
        
        print(f"✅ State machine verified (ConversationStage and UserIntent working)")
        return True
    except Exception as e:
        print(f"❌ State machine error: {e}")
        return False

def verify_tools():
    """Verify tools are defined."""
    print("Checking tools...")
    
    try:
        from day5_langgraph import ToolExecutor, TOOLS_DEFINITION
        
        # Verify tool executor can be instantiated
        executor = ToolExecutor(day4_api_url="http://localhost:8004")
        
        # Verify tool definitions
        assert len(TOOLS_DEFINITION) > 0
        
        print(f"✅ Tools verified ({len(TOOLS_DEFINITION)} tools defined)")
        return True
    except Exception as e:
        print(f"❌ Tools error: {e}")
        return False

def verify_nodes():
    """Verify node implementations."""
    print("Checking nodes...")
    
    try:
        from day5_langgraph.nodes import AgentNodes
        
        # Verify node methods exist
        required_methods = [
            "greeting_node",
            "intent_detection_node",
            "clarification_node",
            "rag_retrieval_node",
            "recommendation_node",
            "booking_node",
        ]
        
        for method in required_methods:
            assert hasattr(AgentNodes, method), f"Missing method: {method}"
        
        print(f"✅ Nodes verified ({len(required_methods)} core nodes)")
        return True
    except Exception as e:
        print(f"❌ Nodes error: {e}")
        return False

def verify_documentation():
    """Verify documentation exists."""
    print("Checking documentation...")
    
    try:
        docs_dir = Path(__file__).parent / "docs"
        
        required_docs = [
            "ARCHITECTURE.md",
            "SETUP.md",
            "COMPLETION_SUMMARY.md",
        ]
        
        missing = []
        for doc in required_docs:
            if not (docs_dir / doc).exists():
                missing.append(doc)
        
        if missing:
            print(f"❌ Missing documentation: {missing}")
            return False
        
        print(f"✅ Documentation verified ({len(required_docs)} guides in docs/)")
        return True
    except Exception as e:
        print(f"❌ Documentation error: {e}")
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Day 5 Bootstrap Verification")
    print("=" * 60)
    
    checks = [
        verify_imports,
        verify_configuration,
        verify_state_machine,
        verify_tools,
        verify_nodes,
        verify_documentation,
    ]
    
    results = [check() for check in checks]
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ All {total} checks passed! Bootstrap complete.")
        return 0
    else:
        print(f"❌ {passed}/{total} checks passed. See errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
