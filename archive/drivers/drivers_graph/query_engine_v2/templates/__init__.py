import json
import pathlib

TEMPLATE_PATH = pathlib.Path(__file__).with_name("template_library.json")
TEMPLATES = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))