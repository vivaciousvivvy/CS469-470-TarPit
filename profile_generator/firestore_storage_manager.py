import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud import storage

import os
from datetime import datetime
from typing import List, Dict, Union

"""
People info is stored as so:
people {
    person_id: {
        name: asdf
        pictures: [pic_id1, ..]
        sex: asdf
        bio: asdf
        ethnicity: asdf
        city: dsaf
        conversation_history: {
            conversation_id_1: [
               {
                    "speaker": "victim" or "butcher"
                    "text": "asdfdsaf",
                    "timestamp": "2025-01-27 10:00:00"
                },
                {
                    "speaker": "victim" or "butcher",
                    "text": "Hfjjrm",
                    "timestamp": "2025-01-27 10:00:05"
                }
            ],
            conversation_id_2: [ ... ]
    }
        }
}

"""


class PeopleDatabase:
    def __init__(self, images_folder='generated_images'):
        """Initialize Firestore client and image storage"""
        # Initialize the Firebase app
        self.cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(self.cred)
        self.db = firestore.client()
        self.storage_client = storage.Client()
        self.bucket_name = "pigbutchering-profile-pictures"
        self.bucket = self.storage_client.bucket(self.bucket_name)

        # Create the local images folder if it doesn't exist
        self.images_folder = images_folder
        os.makedirs(self.images_folder, exist_ok=True)

    def _save_image(self, image_path):
        """Helper method to save an image file and return the stored path"""
        file_extension = os.path.splitext(image_path)[1]
        
        # old filename = (lower_case_name_yyyy-mm-dd.png), ex = elanor_grace_davies_2024-01-05.png
        new_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
        blob = self.bucket.blob(f"images/{new_filename}")

        # Upload the image to Google Cloud Storage
        blob.upload_from_filename(image_path)

        # Return the public URL of the image
        return blob.public_url



    def add_person(self, name, bio, ethnicity, demeanor, image_paths=None):
        """Add a new person with optional multiple images"""
        try:
            # Create person document
            person_ref = self.db.collection('people').document()
            person_data = {
                'name': name,
                'bio': bio,
                'ethnicity': ethnicity,
                'demeanor': demeanor,
                'date_created': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'conversation_history': {} #init empty convo history
            }
            
            # Add images if provided
            if image_paths:
                images = []
                for image_path in image_paths:
                    stored_path = self._save_image(image_path)
                    images.append({'image_url': stored_path})
                person_data['images'] = images

            person_ref.set(person_data)
            return person_ref.id

        except Exception as e:
            raise Exception(f"Error adding person: {str(e)}")

    def add_images_to_person(self, person_id, image_paths, captions=None):
        """Add multiple images to an existing person"""
        try:
            person_ref = self.db.collection('people').document(person_id)
            person = person_ref.get()
            
            if not person.exists:
                raise Exception("Person not found")

            captions = captions or [None] * len(image_paths)
            new_images = []
            
            # Get existing images or initialize empty list
            person_data = person.to_dict()
            existing_images = person_data.get('images', [])
            
            for image_path, caption in zip(image_paths, captions):
                stored_path = self._save_image(image_path)
                new_images.append({ 
                    'image_url': stored_path,
                    'caption': caption 
                }) 
            
            # Update the document with new images
            person_ref.update({
                'images': existing_images + new_images
            })
            
            return True

        except Exception as e:
            raise Exception(f"Error adding images: {str(e)}")

    def remove_image(self, person_id, image_url):
        """Remove a specific image"""
        try:
            person_ref = self.db.collection('people').document(person_id)
            person = person_ref.get()
            
            if not person.exists:
                raise Exception("Person not found")

            person_data = person.to_dict()
            images = person_data.get('images', [])
            
            # Remove image from list and delete file
            images = [img for img in images if img['image_url'] != image_url]

            # Delete the image from Google Cloud Storage
            blob_name = image_url.split(f"https://storage.googleapis.com/{self.bucket_name}/")[1]
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                blob.delete()

            # Update document
            person_ref.update({'images': images})
            return True

        except Exception as e:
            raise Exception(f"Error removing image: {str(e)}")

    def get_person(self, person_id):
        """Retrieve a person by ID"""
        person_ref = self.db.collection('people').document(person_id)
        person = person_ref.get()
        return person.to_dict() if person.exists else None

    def get_person_images(self, person_id):
        """Get all images for a person"""
        person = self.get_person(person_id)
        return person.get('images', []) if person else []

    def update_person(self, person_id, name=None, bio=None, ethnicity=None, demeanor=None):
        """Update a person's basic information"""
        try:
            person_ref = self.db.collection('people').document(person_id)
            if not person_ref.get().exists:
                raise Exception("Person not found")

            update_data = {} 
            if name:
                update_data['name'] = name
            if bio:
                update_data['bio'] = bio
            if ethnicity:
                update_data['ethnicity'] = ethnicity
            if demeanor:
                update_data['bio'] = bio

            if update_data:
                person_ref.update(update_data)
            return True

        except Exception as e:
            raise Exception(f"Error updating person: {str(e)}")

    def delete_person(self, person_id):
        """Delete a person and all their associated images"""
        try:
            person_ref = self.db.collection('people').document(person_id)
            person = person_ref.get()
            
            if not person.exists:
                raise Exception("Person not found")

            # Delete all associated image files
            person_data = person.to_dict()
            for image in person_data.get('images', []): 
                image_url = image['image_url']
                blob_name = image_url.split(f"https://storage.googleapis.com/{self.bucket_name}/")[1]
                blob = self.bucket.blob(blob_name)
                if blob.exists():
                    blob.delete()
                    
            # Delete the document
            person_ref.delete()
            return True

        except Exception as e:
            raise Exception(f"Error deleting person: {str(e)}")

    def list_people(self):
        """List all people with their images"""
        people = []
        for doc in self.db.collection('people').stream():
            person = doc.to_dict()
            person['id'] = doc.id
            people.append(person)
        return people
                                                                                        #    
    def add_message_to_conversation(self, person_id: str, conversation_id: str, message: Dict[str, Union[str, datetime]]):
        """
        Adds a message to a victim on firestore.

        Args:
            person_id: The ID of the person.
            conversation_id: The ID of the conversation (not sure what this should be, perhaps just consecutive ints)
            message: A dictionary containing the message details.
                    {"speaker": "victim" or "butcher", "text": "asdf", "timestamp": "2025-10-27 10:00:00"}
        """
        try:
            person_ref = self.db.collection('people').document(person_id)
            person = person_ref.get()

            if not person.exists:
                raise Exception("Person not found")

            person_data = person.to_dict()
            conversation_history = person_data.get('conversation_history', {})

            if conversation_id not in conversation_history:
                conversation_history[conversation_id] = []

            # Add the message to the conversation
            conversation_history[conversation_id].append(message)

            # Update the document in Firestore
            person_ref.update({'conversation_history': conversation_history})
            return True

        except Exception as e:
            raise Exception(f"Error adding message to conversation: {str(e)}")

    def get_conversation_history(self, person_id: str, conversation_id: str) -> List[Dict[str, Union[str, datetime]]]:
        """
        Retrieves the conversation history for a specific person and conversation.

        Args:
            person_id: The ID of the person.
            conversation_id: The ID of the conversation.

        Returns:
            A list of messages in the conversation, or an empty list if no conversation is found.
        """
        try:
            person_ref = self.db.collection('people').document(person_id)
            person = person_ref.get()

            if not person.exists:
                raise Exception("Person not found")

            person_data = person.to_dict()
            conversation_history = person_data.get('conversation_history', {})

            return conversation_history.get(conversation_id, [])

        except Exception as e:
             raise Exception(f"Error getting conversation history: {str(e)}")
             

# Example usage
if __name__ == "__main__":
    db = PeopleDatabase()
    try:
        print("do the things here")
    except Exception as e:
        print(f"Error: {str(e)}")
