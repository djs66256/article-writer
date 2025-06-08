
if __name__ == "__main__":
    from src.bot.wwdc_translator_bot import translate_wwdc_videos
    from dotenv import load_dotenv
    load_dotenv()
    translate_wwdc_videos("2024", ["10118"])