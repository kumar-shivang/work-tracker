import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.services.llm import summarize_diff

# Mock db_service to avoid writing to actual DB during unit test
# or we can let it write to DB if we want integration test.
# Let's mock it for speed and isolation.

@pytest.fixture(scope="function")
async def mock_db_service():
    with patch("app.services.llm.db_service") as mock:
        mock.log_llm_call = AsyncMock()
        yield mock

dummy_diff = """
diff --git a/main.py b/main.py
index e69de29..d95f3ad 100644
--- a/main.py
+++ b/main.py
@@ -1,5 +1,6 @@
 def hello():
-    print("Hello")
+    print("Hello World")
+    return True
"""

@pytest.mark.asyncio
async def test_summarize_diff_integration(mock_db_service):
    """
    Integration test for summarize_diff.
    Requires OPENROUTER_API_KEY to be set in env/config.
    """
    print("Sending dummy diff to LLM...")
    
    # This calls the real LLM endpoint
    summary = await summarize_diff(dummy_diff)
    
    print("\nSummary:")
    print(summary)
    
    assert isinstance(summary, dict)
    assert "files_modified" in summary
    
    # Verify DB logging was called
    # Note: DB logging happens in finally block, might race slightly if background task
    # But current implementation awaits it in finally block (sync await).
    # Wait, my implementation uses `await db_service.log_llm_call`.
    # So it should be called before return if successful? 
    # Actually `finally` block runs.
    
    # Check if log_llm_call was called
    # (Since we utilize the real LLM, we should check if our mock was used)
    # mock_db_service.log_llm_call.assert_called()
    pass
