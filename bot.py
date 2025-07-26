import asyncio
import datetime
import os
import random
import subprocess
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.types import FSInputFile

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func

from config import BOT_TOKEN, DATABASE_URL, ADMIN_IDS, NOVOSIB_TZ, QUEST_END_TIME
from models import Base, User, Answer, Question, Draw


class QuizStates(StatesGroup):
    WAIT_LOGIN = State()
    WAIT_ANSWER = State()
    WAIT_RESTART_CONFIRM = State()


async def send_user_results(user: User, sess: AsyncSession, bot: Bot):
    total_questions = await sess.execute(select(Question.id))
    total = len(total_questions.scalars().all())

    answers_res = await sess.execute(
        select(Answer).where(Answer.user_id == user.id).order_by(Answer.answered_at)
    )
    answers = answers_res.scalars().all()

    lines = [f"Ваш результат квеста ({user.login}):"]
    for a in answers:
        q = await sess.get(Question, a.question_id)
        correctness = "✅" if a.is_correct else "❌"
        lines.append(f"{q.id}: {correctness}")
    lines.append(f"Правильных ответов: {user.total_correct} из {total}")

    try:
        await bot.send_message(user.telegram_id, "\n".join(lines))
    except Exception:
        pass


async def send_results_to_all(async_session, bot: Bot):
    async with async_session() as sess:
        result = await sess.execute(select(User))
        users = result.scalars().all()
        for user in users:
            await send_user_results(user, sess, bot)


async def check_quest_end(async_session, bot: Bot):
    """Периодическая проверка времени окончания квеста"""
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        if now >= QUEST_END_TIME:
            await send_results_to_all(async_session, bot)
            break
        await asyncio.sleep(60)


async def is_quest_active():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now < QUEST_END_TIME


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        if not await is_quest_active():
            await message.answer("Квест завершён. Спасибо за участие!")
            return

        text = message.text.strip()
        parts = text.split(maxsplit=1)
        qr_id = parts[1] if len(parts) > 1 else None

        if not qr_id:
            await message.answer("Привет! Нашел QR код? Сканируй")
            return

        async with async_session() as sess:
            result = await sess.execute(select(User).where(User.telegram_id == message.from_user.id))
            user = result.scalar_one_or_none()

            if user and user.finished_rank is not None:
                await message.answer("Вы уже прошли квест и не можете проходить его повторно.")
                return

            if user:
                existing_answer = await sess.execute(
                    select(Answer).where(
                        Answer.user_id == user.id,
                        Answer.question_id == qr_id
                    )
                )
                if existing_answer.scalar_one_or_none():
                    await message.answer("Вы уже сканировали этот QR код.")
                    return

                await send_question(message.chat.id, qr_id, async_session, dp, bot)
            else:
                await message.answer("Привет! Введите ваш логин:")
                await state.set_state(QuizStates.WAIT_LOGIN)
                await state.update_data(qr_id=qr_id)

    @dp.message(QuizStates.WAIT_LOGIN)
    async def process_login(message: types.Message, state: FSMContext):
        data = await state.get_data()
        qr_id = data.get("qr_id")
        login = message.text.strip()
        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)

        async with async_session() as sess:
            existing = await sess.execute(select(User).where(User.telegram_id == message.from_user.id))
            if existing.scalar_one_or_none():
                await message.answer("Вы уже зарегистрированы!")
                return

            user = User(
                telegram_id=message.from_user.id,
                nickname=message.from_user.username,
                login=login,
                first_scan=now_utc,
                last_answer=now_utc,
                total_correct=0,
                finished_rank=None
            )
            sess.add(user)
            await sess.commit()

            count_users = await sess.execute(select(User.telegram_id))
            unique_count = len(set(row[0] for row in count_users))
            for admin_id in ADMIN_IDS:
                await bot.send_message(admin_id, f"Новая регистрация: {login} (@{message.from_user.username})\nВсего участников: {unique_count}")

        await message.answer(f"Спасибо, {login}! Начинаем викторину.")
        await state.clear()
        await send_question(message.chat.id, qr_id, async_session, dp, bot)

    async def send_question(chat_id, qid, session_factory, dp, bot):
        async with session_factory() as sess:
            q = await sess.get(Question, qid)
            if not q:
                await bot.send_message(chat_id, "Вопрос не найден.")
                return

            kb = types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text=option)] for option in q.options],
                resize_keyboard=True
            )

            if q.image:
                if q.image.startswith("http"):
                    await bot.send_photo(chat_id, q.image, caption=q.text, reply_markup=kb)
                else:
                    path = os.path.join("images", q.image)
                    if os.path.exists(path):
                        photo = FSInputFile(path)
                        await bot.send_photo(chat_id, photo, caption=q.text, reply_markup=kb)
                    else:
                        await bot.send_message(chat_id, f"{q.text}\n(⚠️ Картинка не найдена)", reply_markup=kb)
            else:
                await bot.send_message(chat_id, q.text, reply_markup=kb)

            state = dp.fsm.get_context(bot=bot, chat_id=chat_id, user_id=chat_id)
            await state.set_state(QuizStates.WAIT_ANSWER)
            await state.update_data(qid=qid)

    @dp.message(QuizStates.WAIT_ANSWER)
    async def handle_answer(message: types.Message, state: FSMContext):
        if not await is_quest_active():
            await message.answer("Квест завершён. Ответы не принимаются.")
            await state.clear()
            return

        data = await state.get_data()
        qid = data.get("qid")

        async with async_session() as sess:
            result = await sess.execute(select(User).where(User.telegram_id == message.from_user.id))
            user = result.scalar_one_or_none()
            question = await sess.get(Question, qid)

            if not user or not question:
                await message.answer("Ошибка. Попробуйте ещё раз.")
                return

            if message.text not in question.options:
                await message.answer("Ошибка! Выберите вариант из меню.")
                return

            existing_answer = await sess.execute(
                select(Answer).where(
                    Answer.user_id == user.id,
                    Answer.question_id == qid
                )
            )
            if existing_answer.scalar_one_or_none():
                await message.answer("Вы уже ответили на этот вопрос.")
                await state.clear()
                return

            is_correct = (message.text == question.correct)
            now_utc = datetime.datetime.now(datetime.timezone.utc)

            ans = Answer(
                user_id=user.id,
                question_id=qid,
                answer=message.text,
                is_correct=is_correct,
                answered_at=now_utc
            )
            sess.add(ans)

            if is_correct:
                user.total_correct += 1

            total_questions = await sess.execute(select(Question.id))
            total = len(total_questions.scalars().all())

            answered_count_res = await sess.execute(
                select(func.count(Answer.id)).where(Answer.user_id == user.id)
            )
            answered_count = answered_count_res.scalar_one()

            if answered_count == total:
                if user.finished_rank is None:
                    finished_users = await sess.execute(
                        select(User).where(User.finished_rank != None).order_by(User.finished_rank)
                    )
                    rank = len(finished_users.scalars().all()) + 1
                    user.finished_rank = rank

                answers = await sess.execute(
                    select(Answer).where(Answer.user_id == user.id).order_by(Answer.answered_at)
                )
                answers = answers.scalars().all()
                if user.total_correct == total:
                    report_lines = [f"{user.login} (@{user.nickname}) завершил квест!"]
                    for a in answers:
                        q = await sess.get(Question, a.question_id)
                        correctness = "✅" if a.is_correct else "❌"
                        report_lines.append(f"{q.id}: {correctness}")
                    report_lines.append(f"Правильных ответов: {user.total_correct} из {total}")
                    for admin_id in ADMIN_IDS:
                        await bot.send_message(admin_id, "\n".join(report_lines))

                await message.answer("🎉 Вы завершили квест!", reply_markup=types.ReplyKeyboardRemove())
            else:
                await message.answer("✅ Ответ принят!", reply_markup=types.ReplyKeyboardRemove())

            user.last_answer = now_utc
            await sess.commit()
            await state.clear()

    @dp.message(Command("winner"))
    async def choose_winner(message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("У вас нет доступа к этой команде.")
            return

        async with async_session() as sess:
            total_questions = await sess.execute(select(Question.id))
            total = len(total_questions.scalars().all())

            result = await sess.execute(
                select(User)
                .join(Answer, Answer.user_id == User.id)
                .group_by(User.id)
                .having(func.count(Answer.id) == total)
            )
            eligible_users = result.scalars().all()
            if not eligible_users:
                await message.answer("Нет участников, завершивших квест полностью.")
                return

            winner = random.choice(eligible_users)
            await message.answer(f"🎁 Победитель: {winner.login} (@{winner.nickname})")
            try:
                await bot.send_message(winner.telegram_id, "Поздравляем! Вы выиграли приз 🎉")
            except Exception:
                pass

    @dp.message(Command("restart"))
    async def restart_handler(message: types.Message, state: FSMContext):
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("⛔ У вас нет прав для перезапуска.")
            return
        await message.answer("⚠️ Вы точно хотите перезапустить бота? Ответьте `да` или `нет`.")
        await state.set_state(QuizStates.WAIT_RESTART_CONFIRM)

    @dp.message(QuizStates.WAIT_RESTART_CONFIRM)
    async def restart_confirm(message: types.Message, state: FSMContext):
        text = message.text.strip().lower()
        if text == "да":
            await message.answer("♻️ Перезапуск бота...")
            await bot.session.close()
            await dp.storage.close()
            subprocess.Popen(["bash", "restart.sh"])
            sys.exit(0)
        elif text == "нет":
            await message.answer("Перезапуск отменён.")
            await state.clear()
        else:
            await message.answer("Пожалуйста, ответьте либо `да`, либо `нет`.")

    asyncio.create_task(check_quest_end(async_session, bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
