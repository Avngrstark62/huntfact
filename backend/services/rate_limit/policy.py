from dataclasses import dataclass

from config import settings


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    limit: int
    window_seconds: int


def global_ip_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        name="global_ip",
        limit=max(1, settings.rate_limit.global_ip_limit),
        window_seconds=max(1, settings.rate_limit.global_ip_window_seconds),
    )


def health_ip_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        name="health_ip",
        limit=max(1, settings.rate_limit.health_ip_limit),
        window_seconds=max(1, settings.rate_limit.health_ip_window_seconds),
    )


def start_hunt_user_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        name="start_hunt_user",
        limit=max(1, settings.rate_limit.start_hunt_user_limit),
        window_seconds=max(1, settings.rate_limit.start_hunt_user_window_seconds),
    )


def start_hunt_duplicate_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        name="start_hunt_duplicate",
        limit=1,
        window_seconds=max(1, settings.rate_limit.start_hunt_duplicate_cooldown_seconds),
    )


def hunt_read_user_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        name="hunt_read_user",
        limit=max(1, settings.rate_limit.hunt_read_user_limit),
        window_seconds=max(1, settings.rate_limit.hunt_read_user_window_seconds),
    )


def hunt_list_user_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        name="hunt_list_user",
        limit=max(1, settings.rate_limit.hunt_list_user_limit),
        window_seconds=max(1, settings.rate_limit.hunt_list_user_window_seconds),
    )
