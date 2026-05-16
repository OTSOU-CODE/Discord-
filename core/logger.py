import logging
import os
from datetime import datetime

class Logger:
    @staticmethod
    def setup_logger():
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        log_filename = f"logs/bot_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger('DiscordGameBot')
