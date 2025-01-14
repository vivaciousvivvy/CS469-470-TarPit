import os
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from vertexai.generative_models import GenerativeModel


class Profile:

    def __init__(self):
        self.name = ""
        self.bio = ""
        self.picture_path = ""
        self.PROJECT_ID = "cs470-rag-llm"
        vertexai.init(project=self.PROJECT_ID, location="us-west1")

    def generate_name(self):
        model = GenerativeModel("gemini-1.5-flash-002")
        name = model.generate_content(f"Generate me a full name, including middle name, for an individual")
        print(name.text)
        self.name = name

    def generate_bio(self, name):
        model = GenerativeModel("gemini-1.5-flash-002")

        bio = model.generate_content(f"Generate me a 1-2 paragraph long bio for an individual with the name {name}. \
                                      This individual should be vulnerable, being older in age and/or lonely, \
                                      and desiring a connection. \
                                      This individual may be a man or woman, and may come from any background or profession. \
                                      The bio should feel authentic. \
                                      The bio must be written in the third person and only cover facts about this person's life. \
                                      The tone must be as if it is were in a biography.")

        print(bio.text)
        self.bio = bio

    def generate_picture(self, output_file_name):
        output_file = output_file_name
        prompt = f"Generate an image for someone with the name {self.name} and the bio {self.bio}."
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

if __name__ == "__main__":
    run_main()