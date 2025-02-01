import logging
import re

from config import Config

logger = logging.getLogger(__name__)


def extract_slack_mentions(text: str) -> dict:
    users = set()
    channels = set()
    mention_pattern = r"<(@U[A-Z0-9]+|#C[A-Z0-9]+)(?:\|[^>]+)?>"
    matches = re.finditer(mention_pattern, text)
    for match in matches:
        identifier = match.group(1)
        if identifier.startswith("@U"):
            users.add(identifier[1:])
        elif identifier.startswith("#C"):
            channels.add(identifier[1:])
    return {"users": list(users), "channels": list(channels)}


def get_mentors(client):
    """Gets a list of all mentors"""
    mentors = client.conversations_members(
        channel=Config.MENTOR_CHANNEL, limit=200
    )
    return mentors["members"]


def deport_to_mexico(client, user):
    """Deport a user from all private channels to mexico"""
    # response = client.users_conversations(user=user, types="private_channel")
    # channels = [channel["id"] for channel in response["channels"]]
    # for channel in channels:
    #     try:
    #         client.conversations_kick(
    #             channel=channel, user=user, token=Config.SLACK_USER_TOKEN
    #         )
    #     except Exception as e:
    #         logger.error(f"Failed to kick {user} from {channel}: {e}")

    try:
        client.conversations_invite(channel=Config.MEXICO_CHANNEL, users=user)
    except Exception as e:
        logger.error(f"Failed to invite {user} to Mexico channel: {e}")
