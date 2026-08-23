from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.lifespan import get_container
from datetime import date, timedelta

from app.modules.life.schemas import DestinationActivationInput, DestinationCandidateValue, DestinationPatch, FoodInput, FoodPatch, FoodValue, GoalPreferenceInput, GoalPreferenceValue, GoalRecommendationValue, GroceryItemInput, GroceryItemPatch, GroceryItemValue, GroceryListInput, GroceryListPatch, GroceryListValue, LifeProfileInput, LifeProfileValue, MealLogInput, MealLogValue, MealTemplateInput, MealTemplatePatch, MealTemplateValue, NotificationDestinationValue, NutritionGoalInput, NutritionGoalValue, ProgressValue, RecurringGroceryItemInput, RecurringGroceryItemPatch, RecurringGroceryItemValue, ReminderInput, ReminderOccurrenceValue, ReminderPatch, ReminderValue, TodayValue, WeightLogInput, WeightLogValue, WorkoutCompletionInput, WorkoutCompletionValue, WorkoutScheduleInput, WorkoutSchedulePatch, WorkoutScheduleValue
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


@router.get("/goal-preferences", response_model=GoalPreferenceValue | None)
async def get_goal_preference(request: Request, authenticated: Authenticated) -> GoalPreferenceValue | None:
    return await _service(request).goal_preference(authenticated.user_id)


@router.put("/goal-preferences", response_model=GoalPreferenceValue)
async def put_goal_preference(data: GoalPreferenceInput, request: Request, authenticated: Authenticated) -> GoalPreferenceValue:
    return await _service(request).put_goal_preference(authenticated.user_id, data)


@router.get("/goal-recommendations", response_model=list[GoalRecommendationValue])
async def list_goal_recommendations(request: Request, authenticated: Authenticated) -> list[GoalRecommendationValue]:
    return await _service(request).goal_recommendations(authenticated.user_id)


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


@router.get("/foods", response_model=list[FoodValue])
async def list_foods(request: Request, authenticated: Authenticated) -> list[FoodValue]:
    return await _service(request).foods(authenticated.user_id)


@router.post("/foods", response_model=FoodValue, status_code=201)
async def create_food(data: FoodInput, request: Request, authenticated: Authenticated) -> FoodValue:
    return await _service(request).create_food(authenticated.user_id, data)


@router.patch("/foods/{food_id}", response_model=FoodValue)
async def patch_food(food_id: int, data: FoodPatch, request: Request, authenticated: Authenticated) -> FoodValue:
    return await _service(request).patch_food(authenticated.user_id, food_id, data)


@router.post("/foods/{food_id}/deactivate", response_model=FoodValue)
async def deactivate_food(food_id: int, request: Request, authenticated: Authenticated) -> FoodValue:
    return await _service(request).patch_food(authenticated.user_id, food_id, FoodPatch(active=False))


@router.get("/meal-templates", response_model=list[MealTemplateValue])
async def list_templates(request: Request, authenticated: Authenticated) -> list[MealTemplateValue]:
    return await _service(request).templates(authenticated.user_id)


@router.post("/meal-templates", response_model=MealTemplateValue, status_code=201)
async def create_template(data: MealTemplateInput, request: Request, authenticated: Authenticated) -> MealTemplateValue:
    return await _service(request).create_template(authenticated.user_id, data)


@router.patch("/meal-templates/{template_id}", response_model=MealTemplateValue)
async def patch_template(template_id: int, data: MealTemplatePatch, request: Request, authenticated: Authenticated) -> MealTemplateValue:
    return await _service(request).patch_template(authenticated.user_id, template_id, data)


@router.delete("/meal-templates/{template_id}", status_code=204)
async def deactivate_template(template_id: int, request: Request, authenticated: Authenticated) -> None:
    await _service(request).deactivate_template(authenticated.user_id, template_id)


@router.get("/meal-logs", response_model=list[MealLogValue])
async def list_meal_logs(request: Request, authenticated: Authenticated, start_date: date | None = None, end_date: date | None = None) -> list[MealLogValue]:
    end = end_date or date.today()
    return await _service(request).meal_logs(authenticated.user_id, start_date or end - timedelta(days=6), end)


@router.post("/meal-logs", response_model=MealLogValue, status_code=201)
async def create_meal_log(data: MealLogInput, request: Request, authenticated: Authenticated) -> MealLogValue:
    return await _service(request).create_meal_log(authenticated.user_id, data)


@router.delete("/meal-logs/{log_id}", status_code=204)
async def delete_meal_log(log_id: int, request: Request, authenticated: Authenticated) -> None:
    await _service(request).delete_meal_log(authenticated.user_id, log_id)


@router.get("/weight-logs", response_model=list[WeightLogValue])
async def list_weight_logs(request: Request, authenticated: Authenticated, start_date: date | None = None, end_date: date | None = None) -> list[WeightLogValue]:
    end = end_date or date.today()
    return await _service(request).weights(authenticated.user_id, start_date or end - timedelta(days=29), end)


@router.put("/weight-logs", response_model=WeightLogValue)
async def put_weight_log(data: WeightLogInput, request: Request, authenticated: Authenticated) -> WeightLogValue:
    return await _service(request).put_weight(authenticated.user_id, data)


@router.delete("/weight-logs/{log_id}", status_code=204)
async def delete_weight_log(log_id: int, request: Request, authenticated: Authenticated) -> None:
    await _service(request).delete_weight(authenticated.user_id, log_id)


@router.get("/workouts", response_model=list[WorkoutScheduleValue])
async def list_workouts(request: Request, authenticated: Authenticated) -> list[WorkoutScheduleValue]:
    return await _service(request).workouts(authenticated.user_id)


@router.post("/workouts", response_model=WorkoutScheduleValue, status_code=201)
async def create_workout(data: WorkoutScheduleInput, request: Request, authenticated: Authenticated) -> WorkoutScheduleValue:
    return await _service(request).create_workout(authenticated.user_id, data)


@router.patch("/workouts/{schedule_id}", response_model=WorkoutScheduleValue)
async def patch_workout(schedule_id: int, data: WorkoutSchedulePatch, request: Request, authenticated: Authenticated) -> WorkoutScheduleValue:
    return await _service(request).patch_workout(authenticated.user_id, schedule_id, data)


@router.post("/workouts/{schedule_id}/occurrences/{occurrence_id}", response_model=WorkoutCompletionValue)
async def complete_workout(schedule_id: int, occurrence_id: int, data: WorkoutCompletionInput, request: Request, authenticated: Authenticated) -> WorkoutCompletionValue:
    return await _service(request).complete_workout(authenticated.user_id, schedule_id, occurrence_id, data)


@router.get("/today", response_model=TodayValue)
async def get_today(request: Request, authenticated: Authenticated) -> TodayValue:
    return await _service(request).today(authenticated.user_id)


@router.get("/progress", response_model=ProgressValue)
async def get_progress(request: Request, authenticated: Authenticated, start_date: date | None = None, end_date: date | None = None) -> ProgressValue:
    end = end_date or date.today()
    return await _service(request).progress(authenticated.user_id, start_date or end - timedelta(days=29), end)


@router.get("/grocery-lists", response_model=list[GroceryListValue])
async def list_grocery_lists(request: Request, authenticated: Authenticated) -> list[GroceryListValue]:
    return await _service(request).grocery_lists(authenticated.user_id)


@router.post("/grocery-lists", response_model=GroceryListValue, status_code=201)
async def create_grocery_list(data: GroceryListInput, request: Request, authenticated: Authenticated) -> GroceryListValue:
    return await _service(request).create_grocery_list(authenticated.user_id, data)


@router.patch("/grocery-lists/{list_id}", response_model=GroceryListValue)
async def patch_grocery_list(list_id: int, data: GroceryListPatch, request: Request, authenticated: Authenticated) -> GroceryListValue:
    return await _service(request).patch_grocery_list(authenticated.user_id, list_id, data)


@router.post("/grocery-lists/{list_id}/archive", response_model=GroceryListValue)
async def archive_grocery_list(list_id: int, request: Request, authenticated: Authenticated) -> GroceryListValue:
    return await _service(request).archive_grocery_list(authenticated.user_id, list_id)


@router.delete("/grocery-lists/{list_id}", status_code=204)
async def delete_grocery_list(list_id: int, request: Request, authenticated: Authenticated) -> None:
    await _service(request).delete_grocery_list(authenticated.user_id, list_id)


@router.post("/grocery-lists/{list_id}/items", response_model=GroceryItemValue, status_code=201)
async def add_grocery_item(list_id: int, data: GroceryItemInput, request: Request, authenticated: Authenticated) -> GroceryItemValue:
    return await _service(request).add_grocery_item(authenticated.user_id, list_id, data)


@router.patch("/grocery-lists/{list_id}/items/{item_id}", response_model=GroceryItemValue)
async def patch_grocery_item(list_id: int, item_id: int, data: GroceryItemPatch, request: Request, authenticated: Authenticated) -> GroceryItemValue:
    return await _service(request).patch_grocery_item(authenticated.user_id, list_id, item_id, data)


@router.delete("/grocery-lists/{list_id}/items/{item_id}", status_code=204)
async def delete_grocery_item(list_id: int, item_id: int, request: Request, authenticated: Authenticated) -> None:
    await _service(request).delete_grocery_item(authenticated.user_id, list_id, item_id)


@router.get("/recurring-grocery-items", response_model=list[RecurringGroceryItemValue])
async def list_recurring_grocery_items(request: Request, authenticated: Authenticated) -> list[RecurringGroceryItemValue]:
    return await _service(request).recurring_grocery_items(authenticated.user_id)


@router.post("/recurring-grocery-items", response_model=RecurringGroceryItemValue, status_code=201)
async def create_recurring_grocery_item(data: RecurringGroceryItemInput, request: Request, authenticated: Authenticated) -> RecurringGroceryItemValue:
    return await _service(request).create_recurring_grocery_item(authenticated.user_id, data)


@router.patch("/recurring-grocery-items/{item_id}", response_model=RecurringGroceryItemValue)
async def patch_recurring_grocery_item(item_id: int, data: RecurringGroceryItemPatch, request: Request, authenticated: Authenticated) -> RecurringGroceryItemValue:
    return await _service(request).patch_recurring_grocery_item(authenticated.user_id, item_id, data)


@router.post("/grocery-lists/{list_id}/recurring-items/{recurring_id}", response_model=GroceryItemValue, status_code=201)
async def add_recurring_grocery_item(list_id: int, recurring_id: int, request: Request, authenticated: Authenticated) -> GroceryItemValue:
    return await _service(request).add_recurring_grocery_item(authenticated.user_id, list_id, recurring_id)
