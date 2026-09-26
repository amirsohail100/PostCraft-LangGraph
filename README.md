# PostCraft-LangGraph
PostCraft is a LangGraph writer-reviewer pipeline that drafts LinkedIn posts with Mistral, optionally searching the web via Tavily for current context, then has a Groq-powered reviewer approve or reject each draft — looping up to 3 attempts. Built with FastAPI and a lightweight HTML/CSS/JS UI.
