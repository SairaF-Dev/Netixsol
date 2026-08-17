from app.agent import execute_tool_with_retry


class FailingTool:

    def __init__(self):
        self.calls = 0

    def invoke(self, inputs):
        self.calls += 1
        raise RuntimeError("Simulated tool failure")


def test_tool_retry_and_fallback():

    tool = FailingTool()

    result = execute_tool_with_retry(
        tool=tool,
        tool_input={},
        incident_id="TEST-RETRY-001",
        tool_name="fake_tool",
        max_retries=2,
    )

    print("\nResult:")
    print(result)

    print("\nNumber of calls:")
    print(tool.calls)

    assert tool.calls == 3
    assert "failed after 3 attempts" in result