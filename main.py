import os
import json
import asyncio
from dotenv import load_dotenv
from core.bot import DiscordGameBot

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Load config
def load_config():
    if not os.path.exists("config.json"):
        config = {
            "prefix": "!",
            "theme_color": "0x00FFFF"
        }
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        return config
    
    with open("config.json", "r") as f:
        return json.load(f)

async def main():
    config = load_config()
    bot = DiscordGameBot(config)
    
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error starting bot: {e}")
