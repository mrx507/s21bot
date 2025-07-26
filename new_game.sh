#!/bin/bash

echo "🔄 Начинаю перезапуск..."

# Удаляем БД, если есть
if [ -f quiz.db ]; then
    echo "🗑 Удаляю quiz.db..."
    rm quiz.db
else
    echo "✅ quiz.db не найден — пропускаем удаление."
fi

# Добавляем вопросы
echo "📥 Запускаю insert_questions.py..."
python3 insert_questions.py

# Запускаем бота
echo "🚀 Запускаю bot.py..."
python3 bot.py
