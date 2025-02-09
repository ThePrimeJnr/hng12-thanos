import logging
import os

from dotenv import load_dotenv
from spreadsheet import Sheet

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Config:
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_USER_TOKEN = os.getenv("SLACK_USER_TOKEN")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

    MEXICO_CHANNEL = "C089GMMHKLL"
    MENTOR_CHANNEL = "C08977V9SRJ"

    SHEET = Sheet(
        "1-noQONm8x7GKQLrFYP24QjhijZOmHfJulCmKWUfw-lo",
        {"A": "intern", "B": "channels"},
    )
