import os
from openai import OpenAI
from supabase import create_client
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a performance intelligence assistant. You have access to two sources:
1. The user's personal biometric data from their wearable device
2. Peer-reviewed research papers on health, recovery, and athletic performance

Rules:
- Always reference BOTH the user's actual data AND specific research findings
- Cite papers like this: [Study: Title, Year]
- Clearly distinguish "Your data shows..." from "Research indicates..."
- Give specific actionable advice based on their numbers, not generic tips
- Never diagnose medical conditions
- If data is limited or unclear, say so honestly"""

def search_papers(question: str, top_k: int = 5) -> list:
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    )
    query_embedding = response.data[0].embedding

    result = supabase_client.rpc('match_papers', {
        'query_embedding': query_embedding,
        'match_threshold': 0.5,
        'match_count': top_k
    }).execute()

    return result.data

def format_papers(papers: list) -> str:
    if not papers:
        return "No relevant research found."
    formatted = []
    for p in papers:
        formatted.append(f"[Study: {p['title']}, similarity: {p['similarity']:.2f}]\n{p['abstract'][:500]}...")
    return "\n\n".join(formatted)

def ask(question: str, user_vitals: str = None, history: list = None) -> str:
    if history is None:
        history = []

    papers = search_papers(question)
    papers_text = format_papers(papers)

    if user_vitals:
        context = f"""User biometric data:
{user_vitals}

Relevant research papers:
{papers_text}

Question: {question}"""
    else:
        context = f"""Relevant research papers:
{papers_text}

Question: {question}"""

    messages = history + [{"role": "user", "content": context}]

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    return response.content[0].text

# Test it right now with fake vitals
if __name__ == "__main__":
    test_vitals = """
- HRV: 38ms (personal avg: 58ms, down 35% over 10 days)
- Recovery score: 41/100
- Resting heart rate: 62 bpm (personal avg: 54 bpm)
- Sleep score: 71/100
- Sleep duration: 7.2 hours
- Device: Oura Ring
"""

    test_questions = [
        "My HRV has dropped significantly this week — what does the research say about this pattern?",
        "Should I train hard today based on my data?",
        "What does the research say about the relationship between HRV and overtraining?"
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        print("-" * 60)
        answer = ask(q, user_vitals=test_vitals)
        print(answer)
        print("=" * 60)
