import json
import os
import aiofiles
import asyncio
from typing import Any, Dict

class Storage:
    @staticmethod
    async def load_json(file_path: str) -> Dict[str, Any]:
        """Loads a JSON file asynchronously."""
        if not os.path.exists(file_path):
            return {}
        try:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}

    @staticmethod
    async def save_json(file_path: str, data: Dict[str, Any]):
        """Saves a dictionary to a JSON file asynchronously."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=4, ensure_ascii=False))
        except Exception as e:
            print(f"Error saving {file_path}: {e}")

    @staticmethod
    async def update_json(file_path: str, key: str, value: Any):
        """Updates a specific key in a JSON file."""
        data = await Storage.load_json(file_path)
        data[key] = value
        await Storage.save_json(file_path, data)
