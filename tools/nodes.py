import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_tavily import TavilySearch
from langgraph.prebuilt import ToolNode

load_dotenv()

search_tool = TavilySearch(max_results=3)
tools = [search_tool]

writer_llm = ChatMistralAI(model="mistral-small-2506", temperature=0.7)
writer_llm_with_tools = writer_llm.bind_tools(tools)

reviewer_llm = ChatGroq(model="openai/gpt-oss-20b", api_key=os.getenv("GROQ_API_KEY"), temperature=0.2)

tool_node = ToolNode(tools)

# Safety cap on total search round-trips across the whole run, so a model that
# keeps deciding to search can't loop forever and burn API cost.
MAX_TOOL_ROUNDS = 2

WRITER_SYSTEM_PROMPT = (
    "You are an expert LinkedIn content writer. Your job is to write "
    "engaging, professional LinkedIn posts about the given topic. "
    "If the topic requires up-to-date information, statistics, or "
    "current trends, use the web search tool to gather fresh context "
    "before writing. If you have already received feedback on a "
    "previous draft, carefully address every point in the new draft. "
    "Rules for good LinkedIn posts: strong hook in the first line, "
    "1 clear takeaway, easy to skim (short paragraphs), around "
    "150-200 words, ends with a question or call-to-action to invite "
    "engagement. Do not use hashtags."
)

REVIEWER_SYSTEM_PROMPT = (
    "You are a strict LinkedIn content reviewer. You judge whether a "
    "post is publish-ready. Evaluate against these criteria:\n"
    "1. Strong hook in the first line\n"
    "2. One clear, valuable takeaway\n"
    "3. Easy to skim - uses short paragraphs\n"
    "4. Roughly 150-200 words\n"
    "5. Ends with an engaging question or CTA\n"
    "6. Professional but human tone (not corporate-robotic)\n"
    "7. No hashtags\n\n"
    "Respond in exactly this format:\n"
    "VERDICT: APPROVED or REJECTED\n"
    "FEEDBACK: <one short paragraph explaining why>\n\n"
    "Be strict but fair. Approve only if the post genuinely meets all "
    "criteria. Reject if even one criterion is clearly missing."
)


def writer_node(state: dict) -> dict:
    """Writes (or rewrites) the LinkedIn post. Can call Tavily to search first."""
    existing_messages = state.get("messages", [])

    # If the last message is a tool result, we're continuing the SAME attempt
    # after a web search - just let the model finish the post using that context.
    if existing_messages and getattr(existing_messages[-1], "type", None) == "tool":
        response = writer_llm_with_tools.invoke(existing_messages)
        return {"messages": [response]}

    # Otherwise this is a fresh attempt: either the first draft, or a rewrite
    # after the reviewer rejected the previous one.
    attempt = state.get("attempt", 0) + 1
    topic = state["topic"]
    previous_feedback = state.get("reviewer_feedback", "")

    if attempt == 1:
        user_message = (
            f"Write a LinkedIn post on this topic: {topic}. "
            f"If you need current info, search the web first."
        )
    else:
        user_message = (
            f"Your previous draft on '{topic}' was rejected. "
            f"Here is the reviewer's feedback:\n\n{previous_feedback}\n\n"
            f"Write a new, improved draft that fixes every issue mentioned. "
            f"Do not repeat the same mistakes."
        )

    new_messages = [("system", WRITER_SYSTEM_PROMPT), ("human", user_message)]
    response = writer_llm_with_tools.invoke(new_messages)

    return {
        "messages": new_messages + [response],
        "attempt": attempt,
    }


def extract_draft_node(state: dict) -> dict:
    """After the writer finishes any tool calls, pulls the final text out as the draft."""
    last_message = state["messages"][-1]
    print(f"\n\n[generated post - attempt {state.get('attempt')}]\n{last_message.content}\n")
    return {"draft": last_message.content}


def reviewer_node(state: dict) -> dict:
    """Reviews the draft and decides: approve or reject with feedback."""
    draft = state["draft"]
    prompt = f"Review this LinkedIn post draft:\n\n{draft}\n\nGive your review."

    response = reviewer_llm.invoke(
        [("system", REVIEWER_SYSTEM_PROMPT), ("human", prompt)]
    )

    review_text = response.content.strip()
    is_approved = "APPROVED" in review_text.upper().split("FEEDBACK")[0]

    if "FEEDBACK:" in review_text:
        feedback = review_text.split("FEEDBACK:", 1)[1].strip()
    else:
        feedback = review_text

    verdict = "APPROVED" if is_approved else "REJECTED"
    print(f"[Verdict: {verdict}]\n[Feedback: {feedback}]")

    return {
        "reviewer_feedback": feedback,
        "is_approved": is_approved,
    }


def should_use_tool(state: dict) -> str:
    last_message = state["messages"][-1]
    tool_rounds_so_far = sum(1 for m in state["messages"] if getattr(m, "type", None) == "tool")

    if getattr(last_message, "tool_calls", None) and tool_rounds_so_far < MAX_TOOL_ROUNDS:
        return "tools"
    return "extract_draft"


def should_stop_looping(state: dict):
    from langgraph.graph import END

    if state["is_approved"]:
        print("Post has been approved.\n")
        return END
    elif state["attempt"] >= 3:
        print("Reached max attempts.\n")
        return END
    else:
        return "writer"
