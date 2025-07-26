import qrcode

# Подставляем ваш юзернейм бота (без @)
BOT_USERNAME = "s21happybirthday_bot"

# Список ID вопросов — они же будут аргументом start
QUESTIONS = ["q1", "q2", "q3", "q4", "q5", "q6"]

for q in QUESTIONS:
    url = f"https://t.me/{BOT_USERNAME}?start={q}"
    img = qrcode.make(url)
    img.save(f"{q}.png")
    print(f"Сохранён {q}.png → {url}")
