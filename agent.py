from langgraph.graph import StateGraph, START, END

from state.WriterState import WriterState
from tools.nodes import (
    writer_node,
    tool_node,
    extract_draft_node,
    reviewer_node,
    should_use_tool,
    should_stop_looping,
)

graph = StateGraph(WriterState)

graph.add_node("writer", writer_node)
graph.add_node("tools", tool_node)
graph.add_node("extract_draft", extract_draft_node)
graph.add_node("reviewer", reviewer_node)

graph.add_edge(START, "writer")
graph.add_conditional_edges("writer", should_use_tool)

# Tool results loop back to the writer so it can actually USE them to finish the
# post. (The original version sent tool output straight to the reviewer, which
# skipped post generation entirely and left `draft` unset.)
graph.add_edge("tools", "writer")
graph.add_edge("extract_draft", "reviewer")

graph.add_conditional_edges("reviewer", should_stop_looping)

compiled_graph = graph.compile()


def run_writer(topic: str) -> dict:
    """Runs the full writer/reviewer loop (up to 3 attempts) and returns the final result."""
    result = compiled_graph.invoke({
        "topic": topic,
        "messages": [],
        "draft": "",
        "reviewer_feedback": "",
        "is_approved": False,
        "attempt": 0,
    })

    return {
        "draft": result["draft"],
        "is_approved": result["is_approved"],
        "attempt": result["attempt"],
        "reviewer_feedback": result["reviewer_feedback"],
    }
