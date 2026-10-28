"""Collects every v1 router under the /api/v1 prefix."""

from fastapi import APIRouter

from app.api.v1 import busy_times, gigs, health, members, practices, recurring_busy_times

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(members.router)
api_router.include_router(gigs.router)
api_router.include_router(busy_times.router)
api_router.include_router(practices.router)
api_router.include_router(recurring_busy_times.router)
