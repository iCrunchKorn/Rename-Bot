import telebot
import requests
import re
import time
from pymongo import MongoClient

# Telegram Bot Token
TOKEN = "8134928059:AAHJBYKEqT-J4IER3Nfzyb1IN4BP1wK0Jhw"
bot = telebot.TeleBot(TOKEN)

# MongoDB Connection
MONGO_URI = "mongodb+srv://ligermohit:usermongodb23@cluster0.w2vky.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['telegram_bot_db']
collection = db['channel_config']

# Global Configuration
channel_config = {
    "source_channel": None,
    "target_channel": None
}

# Load channel configuration from MongoDB
def load_channel_config():
    config = collection.find_one()
    if config:
        channel_config["source_channel"] = config.get("source_channel")
        channel_config["target_channel"] = config.get("target_channel")

# Save channel configuration to MongoDB
def save_channel_config(source_channel=None, target_channel=None):
    update = {}
    if source_channel:
        channel_config["source_channel"] = source_channel
        update["source_channel"] = source_channel
    if target_channel:
        channel_config["target_channel"] = target_channel
        update["target_channel"] = target_channel
    collection.update_one({}, {"$set": update}, upsert=True)

# OMDB API Configuration
OMDB_API_URL = "http://www.omdbapi.com/"
OMDB_API_KEY = "22ada4cd"

# Extract details from file name
def extract_quality(file_name):
    qualities = ['1080p', '720p', 'HD', '4K', 'SD', '480p', '360p']
    for quality in qualities:
        if re.search(quality, file_name, re.IGNORECASE):
            return quality
    return "Unknown Quality"

def extract_season_episode(file_name):
    season_match = re.search(r'(S\d+|Season\s?\d+)', file_name, re.IGNORECASE)
    episode_match = re.search(r'(E\d+|Episode\s?\d+)', file_name, re.IGNORECASE)
    season = season_match.group(0) if season_match else None
    episode = episode_match.group(0) if episode_match else None
    return season, episode

# Fetch details from OMDB
def get_omdb_details(movie_name, release_year):
    params = {
        't': movie_name,
        'y': release_year,
        'apikey': OMDB_API_KEY
    }
    response = requests.get(OMDB_API_URL, params=params)
    data = response.json()
    if data.get('Response') == 'True':
        language = data.get('Language', 'Unknown Language')
        genre = data.get('Genre', 'Unknown Genre')
        return language, genre
    else:
        return 'Unknown Language', 'Unknown Genre'

# Rename file
def rename_file_with_omdb(file_name, quality, season=None, episode=None):
    movie_name_parts = file_name.split(' ')
    movie_name = ' '.join(movie_name_parts[:-2])
    release_year = movie_name_parts[-2] if movie_name_parts[-2].isdigit() else "Unknown Year"
    omdb_language, omdb_genre = get_omdb_details(movie_name, release_year)
    industry = "Hollywood" if "Action" in omdb_genre or "Drama" in omdb_genre else "Bollywood"
    new_name = f"{movie_name}"
    if season and episode:
        new_name += f" {season}{episode}"
    new_name += f" ({release_year}) [{quality}] [{omdb_language}] [{industry}] @iCrunchKornBots"
    return new_name

# Set source channel
@bot.message_handler(commands=['setsource'])
def set_source_channel(message):
    if len(message.text.split()) > 1:
        source_channel = message.text.split()[1]
        save_channel_config(source_channel=source_channel)
        bot.reply_to(message, f"Source channel set to: {source_channel}")
    else:
        bot.reply_to(message, "Usage: /setsource @source_channel_username or channel_id")

# Set target channel
@bot.message_handler(commands=['settarget'])
def set_target_channel(message):
    if len(message.text.split()) > 1:
        target_channel = message.text.split()[1]
        save_channel_config(target_channel=target_channel)
        bot.reply_to(message, f"Target channel set to: {target_channel}")
    else:
        bot.reply_to(message, "Usage: /settarget @target_channel_username or channel_id")

# Forward messages
def forward_messages():
    load_channel_config()
    source_channel = channel_config.get("source_channel")
    target_channel = channel_config.get("target_channel")
    if not source_channel or not target_channel:
        print("Source or Target channel is not set!")
        return
    offset = 0
    while True:
        messages = bot.get_chat_history(source_channel, limit=100, offset_id=offset)
        if not messages:
            break
        for message in messages:
            if message.content_type == 'document':
                file = message.document
                file_name = file.file_name if file.file_name else "Unknown Filename"
                quality = extract_quality(file_name)
                season, episode = extract_season_episode(file_name)
                new_file_name = rename_file_with_omdb(file_name, quality, season, episode)
                print(f"Renamed File: {new_file_name}")
                bot.forward_message(target_channel, source_channel, message.message_id)
        offset += 100
        time.sleep(2)

# Start Bot
if __name__ == "__main__":
    print("Bot is running...")
    bot.polling()
        
