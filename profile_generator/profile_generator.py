import os
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from vertexai.generative_models import GenerativeModel
from datetime import datetime


"""import io
from PIL import Image
import requests

HF_API_KEY = os.environ("VIVEK_HF_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/ZB-Tech/Text-to-Image"
headers = {"Authorization": f"Bearer {HF_API_KEY}"}


def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.content
image_bytes = query({
    "inputs": "Astronaut riding a horse",
})

# You can access the image with PIL.Image for example

image = Image.open(io.BytesIO(image_bytes))"""

#makes the folder if it doesn't exist
images_folder = "generated_images"
os.makedirs(images_folder, exist_ok=True)


class ProfileGenerator:

    def __init__(self):
        self.PROJECT_ID = "pigbutchering-capstone"
        vertexai.init(project=self.PROJECT_ID, location="us-west1")

    def generate_name(self):
        model = GenerativeModel("gemini-1.5-flash-002")
        name = model.generate_content(f"Generate me a full name, including middle name, for an individual")
        print(name.text)
        return(name.text)

    def generate_bio(self, name):
        model = GenerativeModel("gemini-1.5-flash-002")

        bio = model.generate_content(f"Generate me a 1-2 paragraph long bio for an individual with the name {name}. \
                                      This individual should be vulnerable, being older in age and/or lonely, \
                                      and desiring a connection. \
                                      This individual should be single, divorced, or widowed. \
                                      This individual may be a man or woman, and may come from any background. \
                                      This individual should come from a profession that would allow them to be middle-class to upper-class. \
                                      The bio should feel authentic. \
                                      The bio must be written in the third person and only cover facts about this person's life. \
                                      The bio should include some approachable hobbies. \
                                      The bio should include why the individual doesnt have a large social media presense. \
                                      The tone must be as if it is were in a biography.")

        print(bio.text)
        return bio.text

    def generate_picture(self, bio, name):
        
        date = datetime.now().strftime("%Y-%m-%d")
        name_str = name.lower().replace(" ", "_").strip()
        output_file_name = f"{name_str}_{date}.png"

        prompt = f"Generate an image for someone with the name {name} and the bio {bio}. \
                Make this picture an unclear selfie"
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")

        images = model.generate_images(
            prompt=prompt,
            #parameters
            number_of_images=1,
            language="en",
            # You can't use a seed value and watermark at the same time.
            # add_watermark=False,
            # seed=100,
            aspect_ratio="1:1",
            person_generation="allow_adult",
            
            #currently person_generation is disabled, I asked for permission to create this from google.
            #person_generation="allow_adult",
        )
        if not images:
            print("No images were generated")
            return
        else:
            print("Images were generated")
        
        try:
            images[0].save(location=f'{images_folder}/{output_file_name}', include_generation_parameters=False)
            print(f"Created output image using {len(images[0]._image_bytes)} bytes")
        except IndexError:
            raise Exception("Image generation failed - no images were returned")
        except Exception as e:
            raise Exception(f"Error saving generated image: {str(e)}")


        def generate_full(self):
            pass


if __name__ == "__main__":
    generator = ProfileGenerator()
    name = generator.generate_name()
    bio = generator.generate_bio(name)
    generator.generate_picture(bio, name)
