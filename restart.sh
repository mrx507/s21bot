#!/bin/bash

echo "🛑 Завершаю старый процесс бота..."

PIDS=$(pgrep -f "python3 bot.py")

if [ -n "$PIDS" ]; then
    echo "✅ Найдены PID: $PIDS"
    for pid in $PIDS; do
        kill -9 "$pid"
        echo "🔪 Убит процесс $pid"
    done
else
    echo "⚠️ Процесс bot.py не найден"
fi

sleep 1

echo "🗑 Удаляю базу данных..."
rm -f quiz.db

echo "📥 Добавляю вопросы..."
python3 insert_questions.py

echo "🚀 Запускаю нового бота..."
nohup python3 bot.py > bot.log 2>&1 &
echo "✅ Бот запущен"
