from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from datetime import datetime

Base = declarative_base()


class Person(Base):
    __tablename__ = 'people'


    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    bio = Column(Text)
    gender = Column(String(10))
    age = Column(Integer)
    date_of_birth = Column(String(50))
    ethnicity = Column(String(50))

    educational_background = Column(String(50))
    professional_background = Column(String(50))
    interests = Column(Text)
    financial_assets = Column(Text)
    crypto_fluency_level = Column(String(50))
    demeanor = Column(String(50))

    date_created = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    image_list = relationship("Image", back_populates="person", cascade="all, delete-orphan")


class Image(Base):
    __tablename__ = 'images'