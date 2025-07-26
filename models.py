from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, Integer, BigInteger, Text, Boolean,
    TIMESTAMP, ForeignKey, JSON, UniqueConstraint
)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    nickname = Column(Text)
    login = Column(Text, nullable=False)
    first_scan = Column(TIMESTAMP(timezone=True), nullable=False)
    last_answer = Column(TIMESTAMP(timezone=True), nullable=False)
    total_correct = Column(Integer, default=0)
    finished_rank = Column(Integer)

class Answer(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_id = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint('user_id', 'question_id', name='uq_user_question'),)

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Text, primary_key=True)
    text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    correct = Column(Text, nullable=False)
    image = Column(Text, nullable=True)

class Draw(Base):
    __tablename__ = 'draws'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    drawn_at = Column(TIMESTAMP(timezone=True), nullable=False)