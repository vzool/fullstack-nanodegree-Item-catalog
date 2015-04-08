import os, sys, datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()

# Person Model
class Person(Base):
    
    # Table name in .db file
    __tablename__ = 'person'
   
    # Fields
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    password = Column(String(250), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

# Catalog Model
class Catalog(Base):
    
    # Table name in .db file
    __tablename__ = 'catalog'
   
    # Fields
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

    person_id = Column(Integer, ForeignKey('person.id'))
    person = relationship(Person)
    created_at = Column(DateTime, default=datetime.datetime.now)

    # Data interface for JSON or anything else
    @property
    def serialize(self):
      """Return object data in easily serializeable format"""
      return {
        'name'  : self.name,
        'id'    : self.id,
    }

# CatalogItem Model
class CatalogItem(Base):
    
    # Table name in .db file
    __tablename__ = 'catalog_item'

    # Fields
    id = Column(Integer, primary_key = True)
    name =Column(String(80), nullable = False)
    description = Column(String(250))
    catalog_id = Column(Integer,ForeignKey('catalog.id'))
    catalog = relationship(Catalog)

    person_id = Column(Integer,ForeignKey('person.id'))
    person = relationship(Person)
    created_at = Column(DateTime, default=datetime.datetime.now)

    # Data interface for JSON or anything else
    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'           : self.id,
           'name'         : self.name,
           'description'  : self.description,
       }
 
# Database file on HHD
engine = create_engine('sqlite:///catalog_item.db')

Base.metadata.create_all(engine)
