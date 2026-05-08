import base64
import json

from openai import OpenAI
from django.conf import settings
from .prompts import get_prompt
from ..models import Subject

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def safe_json_load(s):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        s = s.replace


class ExerciseVisionService:
    """
    Analyse un exercice (image ou PDF) et retourne
    une résolution pédagogique découpée en étapes + QCM.
    """

    @staticmethod
    def analyze_exercise(file_url: str):
        """
        file_url : URL publique ou lien S3 de l'image/PDF
        subject  : maths | physique | svt | francais | anglais
        Pour les sujets de maths, les formulaires doivent être au format Latex.
        """

        # Path to your image
        image_path = file_url

        # Getting the Base64 string
        base64_image = encode_image(image_path)

        subjects = {s.name: [i.name for i in s.chapters.all()] for s in Subject.objects.all()}

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": get_prompt(subjects)
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    ]
                }
            ],
            max_output_tokens=5096
        )

        return response.output_text
