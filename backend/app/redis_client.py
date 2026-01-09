import redis
import os
from dotenv import load_dotenv
import json
from typing import Optional, Any

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            if expire:
                return self.client.setex(key, expire, value)
            return self.client.set(key, value)
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis"""
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        try:
            return self.client.delete(key) > 0
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists"""
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False

    def publish(self, channel: str, message: Any) -> bool:
        """Publish a message to a channel"""
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            self.client.publish(channel, message)
            return True
        except Exception as e:
            print(f"Redis PUBLISH error: {e}")
            return False

    def subscribe(self, channel: str):
        """Subscribe to a channel"""
        pubsub = self.client.pubsub()
        pubsub.subscribe(channel)
        return pubsub

# Global Redis client instance
redis_client = RedisClient()
