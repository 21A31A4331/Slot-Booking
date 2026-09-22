import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    """Base configuration for Flask application."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-secret-key-replace-in-prod')
    
    # MySQL Database Settings
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'slot_booking_db')

    # Construct MySQL URI (using pure-Python PyMySQL)
    MYSQL_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    
    # Optional direct DATABASE_URL override
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # SQLite Fallback configuration
    USE_SQLITE_FALLBACK = os.environ.get('USE_SQLITE_FALLBACK', 'True').lower() in ('true', '1', 'yes')
    _instance_dir = BASE_DIR / 'instance'
    _instance_dir.mkdir(exist_ok=True, parents=True)
    SQLITE_DATABASE_URI = f"sqlite:///{(_instance_dir / 'slot_booking.db').as_posix()}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    _cached_uri = None
    
    @classmethod
    def get_database_uri(cls):
        """
        Determines the database URI.
        Attempts to connect to MySQL first; if unavailable and fallback is enabled, uses SQLite.
        Caches the result to avoid redundant network timeouts during app initialization.
        """
        if cls._cached_uri:
            return cls._cached_uri

        if cls.DATABASE_URL:
            uri = cls.DATABASE_URL
            if uri.startswith("postgres://"):
                uri = uri.replace("postgres://", "postgresql://", 1)
            elif uri.startswith("mysql://") and "+pymysql" not in uri:
                uri = uri.replace("mysql://", "mysql+pymysql://", 1)
            cls._cached_uri = uri
            return cls._cached_uri

        # Check if MySQL can be reached
        try:
            import pymysql
            conn = pymysql.connect(
                host=cls.DB_HOST,
                port=int(cls.DB_PORT),
                user=cls.DB_USER,
                password=cls.DB_PASSWORD,
                connect_timeout=2
            )
            conn.close()
            cls._cached_uri = cls.MYSQL_DATABASE_URI
            return cls._cached_uri
        except Exception as e:
            if cls.USE_SQLITE_FALLBACK:
                # Ensure instance folder exists
                (BASE_DIR / 'instance').mkdir(exist_ok=True)
                print(f"[INFO] MySQL at {cls.DB_HOST}:{cls.DB_PORT} not reachable ({e}).")
                print(f"[INFO] Using SQLite fallback: {cls.SQLITE_DATABASE_URI}")
                cls._cached_uri = cls.SQLITE_DATABASE_URI
                return cls._cached_uri
            else:
                # Strictly use MySQL as configured
                cls._cached_uri = cls.MYSQL_DATABASE_URI
                return cls._cached_uri

class TestConfig(Config):
    """Configuration for testing."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
