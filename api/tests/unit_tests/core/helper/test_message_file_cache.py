"""Unit tests for MessageFileCache."""

from unittest.mock import patch

import pytest

from core.helper.message_file_cache import MessageFileCache


@pytest.fixture
def mock_redis_client():
    """Fixture: Mock Redis client"""
    with patch("core.helper.message_file_cache.redis_client") as mock:
        yield mock


class TestMessageFileCache:
    """Test class for MessageFileCache"""

    def test_generate_cache_key(self):
        """Test cache key generation logic"""
        message_id = "msg_123456"
        expected_key = f"msg_file:{message_id}"
        assert MessageFileCache._generate_cache_key(message_id) == expected_key

    def test_set_cache(self, mock_redis_client):
        """Test setting cache for MessageFile existence"""
        message_id = "msg_123456"
        expected_key = "msg_file:msg_123456"

        MessageFileCache.set(message_id)

        mock_redis_client.setex.assert_called_once_with(
            expected_key, 3600, "1"  # TTL: 3600 seconds (1 hour)  # Value: "1" indicates existence
        )

    def test_get_cache_hit(self, mock_redis_client):
        """Test get cache - cache hit (key exists)"""
        message_id = "msg_123456"
        mock_redis_client.exists.return_value = True

        result = MessageFileCache.get(message_id)

        mock_redis_client.exists.assert_called_once_with("msg_file:msg_123456")
        assert result is True

    def test_get_cache_miss(self, mock_redis_client):
        """Test get cache - cache miss (key does not exist)"""
        message_id = "msg_123456"
        mock_redis_client.exists.return_value = False

        result = MessageFileCache.get(message_id)

        mock_redis_client.exists.assert_called_once_with("msg_file:msg_123456")
        assert result is None

    def test_invalidate_cache(self, mock_redis_client):
        """Test invalidate cache - delete cache key"""
        message_id = "msg_123456"
        expected_key = "msg_file:msg_123456"

        MessageFileCache.invalidate(message_id)

        mock_redis_client.delete.assert_called_once_with(expected_key)

    def test_cache_key_format_with_special_chars(self):
        """Test cache key generation with various message_id formats"""
        test_cases = [
            ("msg_123", "msg_file:msg_123"),
            ("uuid-v4-format-1234-5678", "msg_file:uuid-v4-format-1234-5678"),
            ("1234567890abcdef", "msg_file:1234567890abcdef"),
            ("msg_with_underscore", "msg_file:msg_with_underscore"),
        ]

        for message_id, expected_key in test_cases:
            assert MessageFileCache._generate_cache_key(message_id) == expected_key

    def test_set_then_get_workflow(self, mock_redis_client):
        """Test typical workflow: set cache then get (cache hit)"""
        message_id = "msg Workflow test"

        # Set cache
        MessageFileCache.set(message_id)
        mock_redis_client.setex.assert_called_once()

        # Clear mock to test get separately
        mock_redis_client.reset_mock()

        # Get - should return True (cache hit)
        mock_redis_client.exists.return_value = True
        result = MessageFileCache.get(message_id)
        assert result is True

    def test_cache_miss_fallback_scenario(self, mock_redis_client):
        """Test scenario where cache miss should trigger DB query"""
        message_id = "msg_new_123"

        # First check - cache miss
        mock_redis_client.exists.return_value = False
        result = MessageFileCache.get(message_id)
        assert result is None  # Should return None on cache miss

        # Developer would then query DB and set cache if found
        # This is exactly what the optimization pattern expects

    def test_multiple_message_ids(self):
        """Test that different message IDs generate different cache keys"""
        message_id_1 = "msg_111"
        message_id_2 = "msg_222"

        key_1 = MessageFileCache._generate_cache_key(message_id_1)
        key_2 = MessageFileCache._generate_cache_key(message_id_2)

        assert key_1 != key_2
        assert key_1 == "msg_file:msg_111"
        assert key_2 == "msg_file:msg_222"

    def test_cache_isolation(self, mock_redis_client):
        """Test that cache operations are isolated between different messages"""
        msg_1 = "msg_1"
        msg_2 = "msg_2"

        # Set cache for msg_1
        MessageFileCache.set(msg_1)
        key_1 = MessageFileCache._generate_cache_key(msg_1)
        mock_redis_client.setex.assert_called_with(key_1, 3600, "1")

        # Set cache for msg_2
        MessageFileCache.set(msg_2)
        key_2 = MessageFileCache._generate_cache_key(msg_2)
        mock_redis_client.setex.assert_called_with(key_2, 3600, "1")

        # Get msg_1
        mock_redis_client.exists.side_effect = [True, False]  # First call True, second False
        result_1 = MessageFileCache.get(msg_1)
        assert result_1 is True

        # Get msg_2 (not cached yet in this test flow)
        mock_redis_client.exists.return_value = False
        result_2 = MessageFileCache.get(msg_2)
        assert result_2 is None

    def test_return_type_consistency(self):
        """Test that return types are consistent"""
        # get() should always return either True or None, never False or other values
        # This is important for type safety in the consuming code

        # Test _generate_cache_key always returns string
        assert isinstance(MessageFileCache._generate_cache_key("test"), str)
