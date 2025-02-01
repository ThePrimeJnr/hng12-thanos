from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import Config, logger
from utils import (
    deport_to_mexico,
    extract_slack_mentions,
    get_immigrants,
    get_mentors,
    migrate_from_mexico,
)

app = App(
    token=Config.SLACK_BOT_TOKEN, signing_secret=Config.SLACK_SIGNING_SECRET
)


@app.event("message")
def handle_message(event, client):
    """Handle message events"""


@app.command("/deport")
def handle_deport(ack, body, client):
    """Handle the /deport command."""
    try:
        ack()
        user = body["user_id"]
        channel = body["channel_id"]
        trigger_id = body["trigger_id"]
        text = body.get("text", "").strip()
        mentors = get_mentors(client)
        immigrants = get_immigrants(client)

        if user not in mentors:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=(":confused: You are not a mentor, mind your business"),
            )
            return

        if user not in immigrants:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=":thinking_face: You can't deport others when you haven't been to Mexico yourself!",
            )
            return

        users = extract_slack_mentions(text)["users"]
        if not users:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=(
                    ":confused: Please include at least one intern to deport.\n"
                    "Usage: `/deport @intern1 @intern2`"
                ),
            )
            return

        mentors_to_deport = [
            user_id for user_id in users if user_id in mentors
        ]
        if mentors_to_deport:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=(
                    ":no_entry: You cannot deport the following mentors!\n\n"
                    + "\n".join([f"• <@{m}>" for m in mentors_to_deport])
                ),
            )
            return

        client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "Confirm Deportation"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"Are you sure you want to deport the following intern(s) to <#{Config.MEXICO_CHANNEL}>?\n\n"
                                + "\n".join([f"• <@{user}>" for user in users])
                                + f"\n\nApproval will be requested from <#{Config.MENTOR_CHANNEL}>."
                            ),
                        },
                    },
                ],
                "close": {"type": "plain_text", "text": "Cancel"},
                "submit": {"type": "plain_text", "text": "Deport"},
                "callback_id": "approve_deportation",
            },
        )

    except Exception as e:
        logger.error(f"Error handling deport command: {str(e)}")
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=body["user_id"],
            text="🔧 Oops! Something went wrong. Please try again.",
        )


@app.view("approve_deportation")
def approve_deportation(ack, body, client):
    """Approve deportation"""
    try:
        ack()
        users = extract_slack_mentions(
            body["view"]["blocks"][0]["text"]["text"]
        )["users"]
        client.chat_postMessage(
            channel=Config.MENTOR_CHANNEL,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<@{body['user']['id']}> has requested to deport the following intern(s) to <#{Config.MEXICO_CHANNEL}>:\n\n"
                        + "\n".join([f"• <@{user}>" for user in users]),
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve"},
                            "style": "primary",
                            "action_id": "approve_deportation",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Decline"},
                            "style": "danger",
                            "action_id": "decline_deportation",
                        },
                    ],
                },
            ],
        )
    except Exception as e:
        logger.error(f"Error handling submission: {str(e)}")
        client.chat_postMessage(
            channel=body["user"]["id"],
            text="🔧 Oops! Something went wrong. Please try again.",
        )


@app.action("decline_deportation")
def decline_deportation(ack, body, client):
    """Decline deportation request"""
    try:
        ack()
        user = body["user"]["id"]
        message = body["message"]
        blocks = message["blocks"]
        blocks[0]["text"]["text"] += f"\n\n:abidoshaker: Declined by <@{user}>"
        blocks.pop()

        client.chat_update(
            channel=body["channel"]["id"],
            ts=message["ts"],
            blocks=blocks,
            text="Deportation request declined",
        )
    except Exception as e:
        logger.error(f"Error declining deportation: {str(e)}")
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=user,
            text="🔧 Oops! Something went wrong. Please try again.",
        )


@app.action("approve_deportation")
def accept_deportation(ack, body, client):
    """Accept deportation request"""
    try:
        ack()
        user = body["user"]["id"]
        mentor = body["message"]["text"].split()[0].strip("<@>")
        message = body["message"]
        blocks = message["blocks"]

        if mentor == user:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user,
                text=":no_entry: You cannot approve your own deportation request",
            )
            return

        blocks[0]["text"]["text"] += f"\n\n:sat: Approved by <@{user}>"
        blocks.pop()
        client.chat_update(
            channel=body["channel"]["id"],
            ts=message["ts"],
            blocks=blocks,
            text="Deportation request approval",
        )
        users = extract_slack_mentions(blocks[0]["text"]["text"])["users"]
        print(users)
        users = [u for u in users if u not in [mentor, user]]
        print("after")
        print(users)

        for deported_user in users:
            deport_to_mexico(client, deported_user)
            client.chat_postMessage(
                channel=deported_user,
                text=f"👮 You have been deported to <#{Config.MEXICO_CHANNEL}> by <@{mentor}>.\nPlease review the workspace rules and follow proper conduct guidelines to be reinstated.",
            )

    except Exception as e:
        logger.error(f"Error accepting deportation: {str(e)}")
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=user,
            text="🔧 Oops! Something went wrong. Please try again.",
        )


@app.command("/reinstate")
def handle_reinstate(ack, body, client):
    """Handle the /reinstate command."""
    try:
        ack()
        user = body["user_id"]
        channel = body["channel_id"]
        text = body.get("text", "").strip()
        mentors = get_mentors(client)
        immigrants = get_immigrants(client)

        if user not in mentors:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=":confused: You are not a mentor, mind your business",
            )
            return

        if channel != Config.MEXICO_CHANNEL:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=f":no_entry: You can only reinstate <#{channel}> immigrants from <#{Config.MEXICO_CHANNEL}>",
            )
            return

        users = extract_slack_mentions(text)["users"]
        if not users:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text="Please mention the user to reinstate",
            )
            return

        mentors_to_reinstate = [
            user_id for user_id in users if user_id in mentors
        ]
        if mentors_to_reinstate:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=(
                    ":no_entry: You cannot reinstate the following mentors!\n\n"
                    + "\n".join([f"• <@{m}>" for m in mentors_to_reinstate])
                ),
            )
            return

        non_immigrants = [user for user in users if user not in immigrants]
        if non_immigrants:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=(
                    ":no_entry: Cannot reinstate the following user(s) as they are not immigrants:\n"
                    + "\n".join([f"• <@{u}>" for u in non_immigrants])
                ),
            )
            return

        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "Confirm Reinstate"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Are you sure you want to reinstate <@{users[0]}>?",
                        },
                    },
                ],
                "close": {"type": "plain_text", "text": "Cancel"},
                "submit": {"type": "plain_text", "text": "Reinstate"},
                "callback_id": "confirm_reinstate",
            },
        )
    except Exception as e:
        logger.error(f"Error handling reinstate: {str(e)}")
        client.chat_postEphemeral(
            channel=channel, user=user, text="🔧 Something went wrong"
        )


@app.view("confirm_reinstate")
def confirm_reinstate(ack, body, client):
    """Handle reinstate confirmation"""
    try:
        ack()
        user = extract_slack_mentions(
            body["view"]["blocks"][0]["text"]["text"]
        )["users"][0]
        channels = migrate_from_mexico(client, user)
        client.chat_postMessage(
            channel=user,
            text=f"You have been reinstated to the following channels:\n{"\n".join([f"• <#{channel}>" for channel in channels])}",
        )
        client.chat_postEphemeral(
            channel=Config.MEXICO_CHANNEL,
            user=body["user"]["id"],
            text=f"✅ Successfully reinstated <@{user}>",
        )
    except Exception as e:
        logger.error(f"Error confirming reinstate: {str(e)}")


def main():
    """Main entry point"""
    try:
        handler = SocketModeHandler(app, Config.SLACK_APP_TOKEN)
        handler.start()
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}")
        raise


if __name__ == "__main__":
    main()
