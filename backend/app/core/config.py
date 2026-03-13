from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
LANCEDB_DIR = DATA_DIR / "lancedb"
DB_PATH = DATA_DIR / "riverai.sqlite"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

# 模型提供商选择：dashscope 或 deepseek
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "dashscope")

# 根据选择的提供商设置API配置
if MODEL_PROVIDER == "dashscope":
    API_KEY = DASHSCOPE_API_KEY
    API_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL_ID = DASHSCOPE_MODEL
else:  # deepseek
    API_KEY = DEEPSEEK_API_KEY
    API_BASE_URL = DEEPSEEK_BASE_URL
    MODEL_ID = DEEPSEEK_MODEL

# API 超时和重试配置
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "120"))  # 默认120秒
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))  # 默认重试3次
API_RETRY_DELAY = int(os.getenv("API_RETRY_DELAY", "3"))  # 重试延迟3秒

