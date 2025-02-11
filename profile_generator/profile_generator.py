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


class ProfileGenerator:

    def __init__(self):
        self.PROJECT_ID = "cs470-rag-llm"
        vertexai.init(project=self.PROJECT_ID, location="us-west1")

    def generate_name(self):
        model = GenerativeModel("gemini-1.5-flash-002")
        name = model.generate_content(f"Generate me a full name, including middle name, for an individual")
        print(name.text)

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
            safety_filter_level="block_some",
            
            #currently person_generation is disabled, I asked for permission to create this from google.
            #person_generation="allow_adult",
        )
        images[0].save(location=output_file, include_generation_parameters=False)
        print(f"Created output image using {len(images[0]._image_bytes)} bytes")
        # Example response:
        # Created output image using 1234567 bytes



def run_main():
    profile = Profile()
    profile.generate_name()
    profile.generate_bio(profile.name)
    profile.generate_picture("output.png")

if __name__ == "__main__":
    run_main()