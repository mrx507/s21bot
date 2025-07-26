import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from models import Base, Question

questions_data = [
    {
        "id": "q1",
        "text": "Кто из сотрудников Адм работает дольше всего?",
        "options": ["Ксюша", "Аня", "Катя"],
        "correct": "Ксюша",
    },
    {
        "id": "q2",
        "text": "Сколько работников Школы 21 являются участниками основного обучения или выпускниками?",
        "options": ["4", "5", "6"],
        "correct": "4",
    },
    {
        "id": "q3",
        "text": "Загрузи фотографию со дня рождения с хэштегом #WeAreSchool21x4_nsk в VK и не удаляй.",
        "options": ["Готово!"],
        "correct": "Готово!",
    },
    {
        "id": "q4",
        "text": "Кто сказал это — человек или ИИ?\n\n\"Успех — это способность идти от неудачи к неудаче, не теряя энтузиазма.\"",
        "options": ["Человек", "ИИ"],
        "correct": "Человек",
    },
    {
        "id": "q5",
        "text": "Картинка нарисована ИИ или человеком?",
        "options": ["Человек", "Искусственный интеллект"],
        "correct": "Искусственный интеллект",
        "image": "q5.png"
    },
    {
        "id": "q6",
        "text": "Выбери на изображении фотографию, сгенерированную нейросетью.",
        "options": ["Левая", "Правая"],
        "correct": "Левая",
        "image": "q6.png"
    }
]

async def insert_questions():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        for q in questions_data:
            existing = await session.get(Question, q["id"])
            if existing:
                continue  # Пропуск, если вопрос уже есть

            question = Question(
                id=q["id"],
                text=q["text"],
                options=q["options"],
                correct=q["correct"],
                image=q.get("image")
            )
            session.add(question)
        await session.commit()
        print(f"✅ Загружено {len(questions_data)} вопросов.")

if __name__ == "__main__":
    asyncio.run(insert_questions())