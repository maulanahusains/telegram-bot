from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.lifespan import get_container
from app.modules.life.schemas import DestinationActivationInput, DestinationCandidateValue, DestinationPatch, LifeProfileInput, LifeProfileValue, NotificationDestinationValue, NutritionGoalInput, NutritionGoalValue, ReminderInput, ReminderOccurrenceValue, ReminderPatch, ReminderValue
from app.modules.life.services import LifeService
from app.platform.auth.dependencies import Authenticated

router = APIRouter(prefix="/api/v1/life", tags=["Life"])


def _service(request: Request) -> LifeService:
    container = get_container(request.app)
    return LifeService(container.database, container.settings)


@router.get("/profile", response_model=LifeProfileValue | None)
async def get_profile(request: Request, authenticated: Authenticated) -> LifeProfileValue | None:
    return await _service(request).profile(authenticated.user_id)


@router.put("/profile", response_model=LifeProfileValue)
async def put_profile(data: LifeProfileInput, request: Request, authenticated: Authenticated) -> LifeProfileValue:
    return await _service(request).put_profile(authenticated.user_id, data)


@router.get("/goals", response_model=list[NutritionGoalValue])
async def list_goals(request: Request, authenticated: Authenticated) -> list[NutritionGoalValue]:
    return await _service(request).goals(authenticated.user_id)


@router.post("/goals", response_model=NutritionGoalValue, status_code=201)
async def create_goal(data: NutritionGoalInput, request: Request, authenticated: Authenticated) -> NutritionGoalValue:
    return await _service(request).create_goal(authenticated.user_id, data)


@router.get("/notification-destination-candidates", response_model=list[DestinationCandidateValue])
async def list_destination_candidates(request: Request, authenticated: Authenticated) -> list[DestinationCandidateValue]:
    return await _service(request).candidates(authenticated.user_id)


@router.get("/notification-destinations", response_model=list[NotificationDestinationValue])
async def list_destinations(request: Request, authenticated: Authenticated) -> list[NotificationDestinationValue]:
    return await _service(request).destinations(authenticated.user_id)


@router.post("/notification-destination-candidates/{candidate_id}/activate", response_model=NotificationDestinationValue, status_code=201)
async def activate_destination(candidate_id: int, data: DestinationActivationInput, request: Request, authenticated: Authenticated) -> NotificationDestinationValue:
    return await _service(request).activate_candidate(authenticated.user_id, candidate_id, data)


@router.patch("/notification-destinations/{destination_id}", response_model=NotificationDestinationValue)
async def patch_destination(destination_id: int, data: DestinationPatch, request: Request, authenticated: Authenticated) -> NotificationDestinationValue:
    return await _service(request).patch_destination(authenticated.user_id, destination_id, data)


@router.get("/reminders", response_model=list[ReminderValue])
async def list_reminders(request: Request, authenticated: Authenticated) -> list[ReminderValue]:
    return await _service(request).reminders(authenticated.user_id)


@router.post("/reminders", response_model=ReminderValue, status_code=201)
async def create_reminder(data: ReminderInput, request: Request, authenticated: Authenticated) -> ReminderValue:
    return await _service(request).create_reminder(authenticated.user_id, data)


@router.patch("/reminders/{reminder_id}", response_model=ReminderValue)
async def patch_reminder(reminder_id: int, data: ReminderPatch, request: Request, authenticated: Authenticated) -> ReminderValue:
    return await _service(request).patch_reminder(authenticated.user_id, reminder_id, data)


@router.delete("/reminders/{reminder_id}", status_code=204)
async def delete_reminder(reminder_id: int, request: Request, authenticated: Authenticated) -> None:
    await _service(request).delete_reminder(authenticated.user_id, reminder_id)


@router.get("/reminders/{reminder_id}/occurrences", response_model=list[ReminderOccurrenceValue])
async def list_occurrences(reminder_id: int, request: Request, authenticated: Authenticated) -> list[ReminderOccurrenceValue]:
    return await _service(request).occurrences(authenticated.user_id, reminder_id)


@router.post("/occurrences/{occurrence_id}/{action}", response_model=ReminderOccurrenceValue)
async def transition_occurrence(occurrence_id: int, action: str, request: Request, authenticated: Authenticated) -> ReminderOccurrenceValue:
    return await _service(request).transition_occurrence(authenticated.user_id, occurrence_id, action)
