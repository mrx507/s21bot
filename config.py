import os
import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
NOVOSIB_TZ = "Asia/Novosibirsk"

if not BOT_TOKEN:
    raise EnvironmentError("❌ Переменная BOT_TOKEN не задана в .env")

if not DATABASE_URL:
    raise EnvironmentError("❌ Переменная DATABASE_URL не задана в .env")

quest_end_str = os.getenv("QUEST_END_TIME")
QUEST_END_TIME = None
if quest_end_str:
    try:
        QUEST_END_TIME = datetime.datetime.strptime(quest_end_str, "%Y-%m-%d %H:%M:%S").astimezone(datetime.timezone.utc)
    except ValueError:
        raise ValueError("❌ Неверный формат переменной QUEST_END_TIME в .env. Используй: YYYY-MM-DD HH:MM:SS")