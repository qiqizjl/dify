"""
Message file cache helper.

Provides Redis caching for message file existence checks to reduce database queries.
"""

from extensions.ext_redis import redis_client

# Cache configuration
MESSAGE_FILE_CACHE_TTL = 3600  # 1 hour
MESSAGE_FILE_CACHE_PREFIX = "msg_file:"


class MessageFileCache:
    """
    Cache helper for MessageFile existence checks using Redis.

    Cache strategy:
    - Key: msg_file:{message_id}
    - Key exists in Redis = MessageFile exists
    - Key does not exist = Uncached (need to query DB)
    - TTL: 1 hour

    Usage:
        # Set cache after creating MessageFile
        MessageFileCache.set(message_id)

        # Query cache (returns None if not cached)
        exists = MessageFileCache.get(message_id)
        if exists is not None:
            # Cache hit
            return exists  # True or the key shouldn't exist
        else:
            # Cache miss - query database
            exists = check_database()
            if exists:
                MessageFileCache.set(message_id)
    """

    @staticmethod
    def _generate_cache_key(message_id: str) -> str:
        """Generate Redis cache key for message_id."""
        return f"{MESSAGE_FILE_CACHE_PREFIX}{message_id}"

    @staticmethod
    def set(message_id: str):
        """
        Set cache for MessageFile existence.
        Should be called after creating a MessageFile.

        Args:
            message_id: Message ID
        """
        cache_key = MessageFileCache._generate_cache_key(message_id)
        redis_client.setex(cache_key, MESSAGE_FILE_CACHE_TTL, "1")

    @staticmethod
    def get(message_id: str) -> bool | None:
        """
        Check if MessageFile exists in cache.

        Returns:
            True if cached (key exists)
            None if not cached (cache miss)
        """
        cache_key = MessageFileCache._generate_cache_key(message_id)
        exists = redis_client.exists(cache_key)
        if exists:
            return True
        return None

    @staticmethod
    def invalidate(message_id: str):
        """
        Invalidate cache for a specific message_id.
        Useful when MessageFile is updated or deleted.
        """
        cache_key = MessageFileCache._generate_cache_key(message_id)
        redis_client.delete(cache_key)
