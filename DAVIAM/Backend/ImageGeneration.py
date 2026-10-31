import asyncio
import json
import os
import sys
from random import randint
from time import sleep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import requests
from PIL import Image

from paths import data_path, env_get, files_path

API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"


def request_path():
    return files_path("ImageGeneration.data")


def normalise_prompt(prompt):
    text = (prompt or "").strip()
    lower = text.lower()
    for prefix in ("generate image of ", "generate image ", "generate an image of ", "generate "):
        if lower.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    return text or (prompt or "").strip()


def parse_image_request(data):
    data = (data or "").strip()
    if "," not in data:
        return None, None
    prompt, status = data.rsplit(",", 1)
    return prompt.strip(), status.strip()


def is_image_bytes(data):
    if not data or len(data) < 12:
        return False
    if data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8") or data.startswith(b"GIF8"):
        return True
    return data.startswith(b"RIFF") and data[8:12] == b"WEBP"


def image_from_response(response):
    if response.status_code >= 400 or not is_image_bytes(response.content):
        preview = response.content[:300]
        try:
            preview = json.dumps(response.json())[:300]
        except Exception:
            pass
        raise RuntimeError(
            f"Image service returned an error ({response.status_code}): {preview!r}"
        )
    return response.content


def _can_show_images():
    if os.environ.get("DAVIAM_HEADLESS") == "1":
        return False
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def open_images(prompt):
    folder_path = os.path.dirname(data_path("placeholder"))
    prompt = prompt.replace(" ", "_")
    files = [f"{prompt}{i}.png" for i in range(1, 5)]

    for jpg_file in files:
        image_path = os.path.join(folder_path, jpg_file)
        try:
            img = Image.open(image_path)
            print(f"Opening image: {image_path}")
            if _can_show_images():
                img.show()
                sleep(1)
            else:
                print("No display available; the image was saved but not opened.")
        except Exception as error:
            print(f"Unable to open {image_path}\n{error}")


def _headers():
    key = env_get("HuggingFaceAPIKey")
    if not key:
        raise RuntimeError(
            "HuggingFaceAPIKey is missing. Add it to DAVIAM/.env (see .env.example). "
            "The token needs permission to call Hugging Face Inference Providers."
        )
    return {"Authorization": f"Bearer {key}"}


async def query(payload):
    response = await asyncio.to_thread(
        requests.post,
        API_URL,
        headers=_headers(),
        json=payload,
        timeout=180,
    )
    if response.status_code == 503:
        sleep(3)
        response = await asyncio.to_thread(
            requests.post,
            API_URL,
            headers=_headers(),
            json=payload,
            timeout=180,
        )
    return image_from_response(response)


async def generate_images(prompt: str):
    tasks = []
    for _ in range(4):
        payload = {
            "inputs": f"{prompt}, quality=4K, sharpness=maximum, Ultra High details, high resolution",
            "parameters": {"seed": randint(0, 1000000)},
        }
        tasks.append(asyncio.create_task(query(payload)))

    image_bytes_list = await asyncio.gather(*tasks, return_exceptions=True)
    saved = 0
    for index, image_bytes in enumerate(image_bytes_list):
        if isinstance(image_bytes, Exception):
            print(f"Image {index + 1} failed: {image_bytes}")
            continue
        destination = data_path(f"{prompt.replace(' ', '_')}{index + 1}.png")
        with open(destination, "wb") as handle:
            handle.write(image_bytes)
        saved += 1
    if saved == 0:
        raise RuntimeError("All image requests failed.")


def GenerateImages(prompt: str):
    prompt = normalise_prompt(prompt)
    asyncio.run(generate_images(prompt))
    open_images(prompt)


def run_worker():
    while True:
        try:
            with open(request_path(), "r", encoding="utf-8") as handle:
                prompt, status = parse_image_request(handle.read())

            if status == "True":
                print("Generating Images... ")
                try:
                    GenerateImages(prompt=prompt)
                except Exception as error:
                    print(f"Image generation failed: {error}")
                finally:
                    with open(request_path(), "w", encoding="utf-8") as handle:
                        handle.write("False,False")
                break
            sleep(1)
        except Exception as error:
            print(f"Image generation loop error: {error}")
            sleep(1)


if __name__ == "__main__":
    run_worker()
