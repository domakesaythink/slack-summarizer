import os
from datetime import datetime, timedelta
import pytz
import openai
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Slack APIトークン
SLACK_BOT_TOKEN = str(os.environ.get('SLACK_BOT_TOKEN')).strip()
# OpenAI APIキー
OPEN_AI_TOKEN = str(os.environ.get('OPEN_AI_TOKEN')).strip()
# 投稿チャンネル
CHANNEL_ID = str(os.environ.get('SLACK_POST_CHANNEL_ID')).strip()

# Slack APIクライアントの初期化
client = WebClient(token=SLACK_BOT_TOKEN)

# 対象とするSlackチャンネルのリスト
CHANNELS = str(os.environ.get('SLACK_READ_CHANNEL_ID')).strip().split(',')

# Slack APIを使用してテキストを取得する関数
def get_channel_text(channel_id, start_time, end_time):
    try:
        # チャンネルIDを取得
        # チャンネルのメッセージを取得
        response = client.conversations_history(
            channel=channel_id,
            oldest=start_time.timestamp(),
            latest=end_time.timestamp()
        )
        messages = response['messages']
        text = ""
        for message in messages[::-1]:
            if "bot_id" in message or len(message["text"].strip()) == 0:
                continue
            if 'text' in message:
                text += message['text'] + "\n"
        return text
    except SlackApiError as e:
        print("Error: {}".format(e))
        return None

def get_time_range():
    """
    Get a time range starting from 25 hours ago and ending at the current time.

    Returns:
        tuple: A tuple containing the start and end times of the time range, as datetime objects.

    Examples:
        >>> start_time, end_time = get_time_range()
        >>> print(start_time, end_time)
        2022-05-17 09:00:00+09:00 2022-05-18 10:00:00+09:00
    """
    hours_back = 25
    timezone = pytz.timezone('Asia/Tokyo')
    now = datetime.now(timezone)
    yesterday = now - timedelta(hours=hours_back)
    start_time = datetime(yesterday.year, yesterday.month, yesterday.day,
                          yesterday.hour, yesterday.minute, yesterday.second)
    end_time = datetime(now.year, now.month, now.day, now.hour, now.minute,
                        now.second)
    return start_time, end_time

def summarize(text: str, language: str = "Japanese"):
    """
    Summarize a chat log in bullet points, in the specified language.
    Args:
        text (str): The chat log to summarize, in the format "Speaker: Message" separated by line breaks.
        language (str, optional): The language to use for the summary. Defaults to "Japanese".
    Returns:
        str: The summarized chat log in bullet point format.
    Examples:
        >>> summarize("Alice: Hi\nBob: Hello\nAlice: How are you?\nBob: I'm doing well, thanks.")
        '- Alice greeted Bob.\n- Bob responded with a greeting.\n- Alice asked how Bob was doing.\n- Bob replied that he was doing well.'
    """
    openai.api_key = OPEN_AI_TOKEN
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        temperature=0.3,
        messages=[{
            "role":
            "system",
            "content":
            "【タイトル】ここに【サマリー】に対する見出しを30文字以内で出力してください",
            "【サマリー】ここにサマリーを出力してください",
            
            
        }, {
            "role":
            "user",
            "content":
            
                "チャットログを要約して物語風の文章にしてください"
           
            
        }])

    return response["choices"][0]["message"]['content']

def postSlack(channel_id, text):
    response = client.chat_postMessage(channel=channel_id, text=text)
    if not response["ok"]:
        print(f'Failed to post message: {response["error"]}')
        raise SlackApiError('Failed to post message', response["error"])

def get_channel_name(channel_id):
    response = client.conversations_info(channel=channel_id)
    return response['channel']['name']

def main():
    start_time, end_time = get_time_range()

    # 対象のチャンネルからテキストを取得
    texts = []
    for channel_id in CHANNELS:
        text = get_channel_text(channel_id, start_time, end_time)
        if text is not None:
            channel_name = get_channel_name(channel_id)
            texts.append('<#' + channel_id + '> では今日こんなことがありました。 ')
            texts.append(summarize(text))
            texts.append("\n")

    # 取得したテキストを結合
    combined_text = "\n".join(texts)

    postSlack(CHANNEL_ID, combined_text)

if __name__ == '__main__':
    main()
