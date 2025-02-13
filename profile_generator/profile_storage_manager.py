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

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('people.id'))
    image_path = Column(String(255), nullable=False)

    person = relationship("Person", back_populates="image_list")



class PeopleDatabase():

    def __init__(self, db_path='sqlite:///people.db', images_folder='generated_images'):
        """Initialize database and image storage"""
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self.images_folder = images_folder
        os.makedirs(self.images_folder, exist_ok=True)

    def _save_image(self, image_path):
        """Helper method to save an image file and return the stored path"""
        file_extension = os.path.splitext(image_path)[1]
        new_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
        new_path = os.path.join(self.images_folder, new_filename)
        
        with open(image_path, 'rb') as source, open(new_path, 'wb') as dest:
            dest.write(source.read())
        
        return new_path

    def add_person(self, name, bio, image_paths=None):
        """Add a new person with optional multiple images"""
        try:
            new_person = Person(name=name, bio=bio)
            
            # Add images if provided
            if image_paths:
                for image_path in image_paths:
                    stored_path = self._save_image(image_path)
                    new_image = Image(image_path=stored_path)
                    new_person.images.append(new_image)

            self.session.add(new_person)
            self.session.commit()
            return new_person.id
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error adding person: {str(e)}")

    def add_images_to_person(self, person_id, image_paths, captions=None):
        """Add multiple images to an existing person"""
        try:
            person = self.get_person(person_id)
            if not person:
                raise Exception("Person not found")

            captions = captions or [None] * len(image_paths)
            
            for image_path, caption in zip(image_paths, captions):
                stored_path = self._save_image(image_path)
                new_image = Image(image_path=stored_path, caption=caption)
                person.images.append(new_image)

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error adding images: {str(e)}")

    def remove_image(self, image_id):
        """Remove a specific image"""
        try:
            image = self.session.query(Image).filter(Image.id == image_id).first()
            if not image:
                raise Exception("Image not found")

            # Delete the actual file
            if os.path.exists(image.image_path):
                os.remove(image.image_path)

            self.session.delete(image)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error removing image: {str(e)}")

    def get_person(self, person_id):
        """Retrieve a person by ID"""
        return self.session.query(Person).filter(Person.id == person_id).first()

    def get_person_images(self, person_id):
        """Get all images for a person"""
        person = self.get_person(person_id)
        return person.images if person else []

    def update_person(self, person_id, name=None, bio=None):
        """Update a person's basic information"""
        try:
            person = self.get_person(person_id)
            if not person:
                raise Exception("Person not found")

            if name:
                person.name = name
            if bio:
                person.bio = bio

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error updating person: {str(e)}")

    def delete_person(self, person_id):
        """Delete a person and all their associated images"""
        try:
            person = self.get_person(person_id)
            if not person:
                raise Exception("Person not found")

            # Delete all associated image files
            for image in person.images:
                if os.path.exists(image.image_path):
                    os.remove(image.image_path)

            self.session.delete(person)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Error deleting person: {str(e)}")

    def list_people(self):
        """List all people with their images"""
        return self.session.query(Person).all()

    def close(self):
        """Close the database session"""
        self.session.close()

# Example usage
if __name__ == "__main__":
    db = PeopleDatabase()

    try:
        print("put commands here")

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        db.close()