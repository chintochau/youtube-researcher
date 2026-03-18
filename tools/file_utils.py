import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def load_env():
    load_dotenv(PROJECT_ROOT / ".env")
    return {
        "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY", ""),
        "SUPADATA_API_KEY": os.getenv("SUPADATA_API_KEY", ""),
    }


def ensure_channel_dir(channel_name):
    slug = slugify(channel_name)
    channel_dir = DATA_DIR / slug
    (channel_dir / "transcripts").mkdir(parents=True, exist_ok=True)
    (channel_dir / "extractions").mkdir(parents=True, exist_ok=True)
    (channel_dir / "reports").mkdir(parents=True, exist_ok=True)
    return channel_dir


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
