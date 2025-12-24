import openai
import os
from dotenv import load_dotenv
from sqlmodel import Session, select, create_engine
from models.chat_cache import ChatCache

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sqlite_url = "sqlite:///database.db"
engine = create_engine(sqlite_url)

SYSTEM_PROMPT = """Du bist ein KI-Reiseberater für FlyAI.
Du hilfst NUR bei folgenden Themen:
- Flugsuche und Flugbuchungen
- Reiseziele und Empfehlungen
- Visa und Einreisebestimmungen
- Gepäckregeln und Airline-Infos
- Reiseplanung und Tipps

Wenn jemand nach anderen Themen fragt (z.B. Kochen, Programmieren, Politik), 
antworte freundlich: "Ich bin dein Reiseberater und kann dir nur bei Reisethemen helfen. 
Frag mich gerne nach Flügen, Reisezielen, Visa oder Gepäck!"

Antworte immer auf Deutsch, kurz und hilfreich."""

def ask_chatgpt(prompt: str):
    normalized_question = prompt.strip().lower()
    
    with Session(engine) as session:
        statement = select(ChatCache).where(ChatCache.question == normalized_question)
        cached = session.exec(statement).first()
        
        if cached:
            return cached.answer
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7,
    )
    answer = response.choices[0].message.content
    
    with Session(engine) as session:
        cache_entry = ChatCache(question=normalized_question, answer=answer)
        session.add(cache_entry)
        session.commit()
    
    return answer
