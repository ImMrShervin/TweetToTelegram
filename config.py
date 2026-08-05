import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMINS = [int(x) for x in os.getenv("ADMINS", "").replace(" ", "").split(",") if x]

TWEET_API = os.getenv("TWEET_API", "https://api.fxtwitter.com")
TWEET_API_FALLBACK = os.getenv("TWEET_API_FALLBACK", "https://api.vxtwitter.com")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "data", "bot.db"))
LOGO_DIR = os.getenv("LOGO_DIR", os.path.join(BASE_DIR, "data", "logos"))
TMP_DIR = os.getenv("TMP_DIR", os.path.join(BASE_DIR, "data", "tmp"))

for _d in (os.path.dirname(DB_PATH), LOGO_DIR, TMP_DIR):
    os.makedirs(_d, exist_ok=True)

DEFAULTS = {

    "title_emoji": "📌",
    "paragraph_emoji": "🔹",
    "font_size": 20,         
    "font_color": "#0f1419",  
    "card_bg": "#ffffff",    
    "page_bg": "#f5f8fa",    
    "bg_image": "",          

    "show_stats": 1,         
    "show_verified": 1,  
    "show_quote": 1,        
    "show_date": 1,     
    "show_media": 1,   
    "shadow": 1,        

    "padding": 40,           
    "width": 720,       

    "watermark_opacity": 85,  
    "watermark_scale": 14,   
    "watermark_pos": "bottom-right",
}

BOOL_KEYS = {"show_stats", "show_verified", "show_quote", "show_date", "show_media", "shadow"}
INT_KEYS = {"font_size", "padding", "width", "watermark_opacity", "watermark_scale"}
