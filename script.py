
if __name__ == "__main__":
    import os
    from src.bot.wwdc_translator_bot import translate_wwdc_videos
    from dotenv import load_dotenv
    load_dotenv()
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    translate_wwdc_videos("2024", ["10147"])