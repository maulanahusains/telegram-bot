import { apiRequest } from "./client";

export interface LifeProfile {
  id: number;
  timezone: string;
  display_name: string | null;
  height_cm: string | null;
  sex: "female" | "male" | "other" | "prefer_not_to_say" | null;
}

export interface NutritionGoal {
  id: number;
  calorie_target_kcal: number;
  protein_min_g: string;
  protein_max_g: string;
  effective_from: string;
}

export type GoalDirection = "lose_weight" | "maintain_weight" | "gain_weight";
export interface GoalPreference { id: number; goal_direction: GoalDirection; desired_weekly_change_kg: string | null; last_evaluated_on: string | null; created_at: string; updated_at: string; }
export interface GoalPreferenceInput { goal_direction: GoalDirection; desired_weekly_change_kg: number | null; }
export type GoalRecommendationStatus = "pending" | "applied" | "dismissed" | "expired" | "superseded";
export type GoalRecommendationDeliveryStatus = "pending" | "sent" | "failed";
export interface GoalRecommendation {
  id: number;
  status: GoalRecommendationStatus;
  delivery_status: GoalRecommendationDeliveryStatus;
  current_goal_id: number | null;
  current_calorie_target_kcal: number;
  recommended_calorie_target_kcal: number;
  goal_direction: GoalDirection;
  desired_weekly_change_kg: string | null;
  window_start: string;
  window_end: string;
  observation_count: number;
  trend_kg_per_week: string;
  rule_version: string;
  rule_snapshot: Record<string, unknown>;
  offered_at: string;
  expires_at: string;
  decided_at: string | null;
}

export interface DestinationCandidate {
  id: number;
  bot_name: string;
  kind: "private" | "group" | "supergroup";
  chat_label: string;
  last_seen_at: string;
}

export interface NotificationDestination {
  id: number;
  bot_name: string;
  kind: "private" | "group" | "supergroup";
  label: string;
  enabled: boolean;
  is_default: boolean;
  verified_at: string | null;
  disabled_reason: string | null;
}

export interface RecurrenceRule {
  frequency: "daily" | "weekly";
  time: string;
  weekdays: Array<"mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun">;
}

export interface Reminder {
  id: number;
  title: string;
  notes: string | null;
  kind: "reminder" | "routine" | "meal" | "workout";
  schedule_type: "one_time" | "recurring";
  scheduled_at: string | null;
  timezone: string;
  recurrence: RecurrenceRule | null;
  destination_id: number;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
}

export interface Food { id: number; name: string; serving_label: string; serving_grams: string | null; calories_kcal: number; protein_g: string; active: boolean; }
export interface MealTemplate { id: number; name: string; meal_slot: string | null; active: boolean; items: Array<{ id: number; food_id: number; food_name: string; quantity: string; position: number }>; }
export interface MealLog { id: number; meal_slot: string | null; status: "logged" | "planned" | "skipped"; consumed_at: string; local_date: string; note: string | null; calories_kcal: number; protein_g: string; items: Array<{ id: number; food_id: number | null; food_name: string; quantity: string; calories_kcal: number; protein_g: string }> }
export interface WeightLog { id: number; weighed_at: string; local_date: string; weight_kg: string; note: string | null; }
export interface Workout { id: number; name: string; workout_type: string | null; enabled: boolean; reminder: Reminder; }
export interface Today { date: string; timezone: string; calorie_target_kcal: number | null; protein_min_g: string | null; protein_max_g: string | null; calories_consumed: number; protein_consumed: string; meals: MealLog[]; workout: Workout | null; workout_occurrence_id: number | null; workout_completion: { id: number; status: "done" | "skipped" } | null; upcoming_reminders: Reminder[]; }
export interface GroceryItem { id: number; name: string; quantity: string; unit: string; estimated_unit_price_rupiah: number | null; estimated_total_rupiah: number | null; is_bought: boolean; }
export type GroceryCadence = "weekly" | "monthly" | "custom";
export interface GroceryList { id: number; name: string; cadence: GroceryCadence; starts_on: string; ends_on: string; status: "active" | "archived"; items: GroceryItem[]; estimated_total_rupiah: number; }
export type CreateGroceryListInput = { name: string; cadence: "weekly" | "monthly" } | { name: string; cadence: "custom"; starts_on: string; ends_on: string };
export interface RecurringGroceryItem { id: number; name: string; quantity: string; unit: string; estimated_unit_price_rupiah: number | null; enabled: boolean; }
export interface Progress { start_date: string; end_date: string; days: Array<{ date: string; calories_consumed: number; calorie_target_kcal: number | null; protein_consumed: string; protein_min_g: string | null; workout_done: number; workout_skipped: number }>; weights: WeightLog[]; }

export type ReminderInput = Omit<Reminder, "id" | "next_run_at" | "last_run_at">;

export const lifeApi = {
  profile: () => apiRequest<LifeProfile | null>("/life/profile"),
  saveProfile: (value: Omit<LifeProfile, "id">) => apiRequest<LifeProfile>("/life/profile", { method: "PUT", body: JSON.stringify(value) }),
  goals: () => apiRequest<NutritionGoal[]>("/life/goals"),
  createGoal: (value: Omit<NutritionGoal, "id">) => apiRequest<NutritionGoal>("/life/goals", { method: "POST", body: JSON.stringify(value) }),
  goalPreferences: () => apiRequest<GoalPreference | null>("/life/goal-preferences"),
  saveGoalPreference: (value: GoalPreferenceInput) => apiRequest<GoalPreference>("/life/goal-preferences", { method: "PUT", body: JSON.stringify(value) }),
  goalRecommendations: () => apiRequest<GoalRecommendation[]>("/life/goal-recommendations"),
  candidates: () => apiRequest<DestinationCandidate[]>("/life/notification-destination-candidates"),
  destinations: () => apiRequest<NotificationDestination[]>("/life/notification-destinations"),
  activateCandidate: (candidateId: number, value: { label?: string; make_default?: boolean }) => apiRequest<NotificationDestination>(`/life/notification-destination-candidates/${candidateId}/activate`, { method: "POST", body: JSON.stringify(value) }),
  patchDestination: (id: number, value: Partial<Pick<NotificationDestination, "label" | "enabled" | "is_default">>) => apiRequest<NotificationDestination>(`/life/notification-destinations/${id}`, { method: "PATCH", body: JSON.stringify(value) }),
  reminders: () => apiRequest<Reminder[]>("/life/reminders"),
  createReminder: (value: ReminderInput) => apiRequest<Reminder>("/life/reminders", { method: "POST", body: JSON.stringify(value) }),
  patchReminder: (id: number, value: Partial<ReminderInput>) => apiRequest<Reminder>(`/life/reminders/${id}`, { method: "PATCH", body: JSON.stringify(value) }),
  deleteReminder: (id: number) => apiRequest<void>(`/life/reminders/${id}`, { method: "DELETE" })
  ,foods: () => apiRequest<Food[]>("/life/foods"),
  createFood: (value: Omit<Food, "id">) => apiRequest<Food>("/life/foods", { method: "POST", body: JSON.stringify(value) }),
  patchFood: (id: number, value: Partial<Food>) => apiRequest<Food>(`/life/foods/${id}`, { method: "PATCH", body: JSON.stringify(value) }),
  templates: () => apiRequest<MealTemplate[]>("/life/meal-templates"),
  createTemplate: (value: Omit<MealTemplate, "id">) => apiRequest<MealTemplate>("/life/meal-templates", { method: "POST", body: JSON.stringify(value) }),
  createMealLog: (value: object) => apiRequest<MealLog>("/life/meal-logs", { method: "POST", body: JSON.stringify(value) }),
  mealLogs: () => apiRequest<MealLog[]>("/life/meal-logs"),
  weights: () => apiRequest<WeightLog[]>("/life/weight-logs"),
  saveWeight: (value: object) => apiRequest<WeightLog>("/life/weight-logs", { method: "PUT", body: JSON.stringify(value) }),
  workouts: () => apiRequest<Workout[]>("/life/workouts"),
  createWorkout: (value: object) => apiRequest<Workout>("/life/workouts", { method: "POST", body: JSON.stringify(value) }),
  transitionOccurrence: (id: number, action: "completed" | "skipped") => apiRequest<object>(`/life/occurrences/${id}/${action}`, { method: "POST" }),
  today: () => apiRequest<Today>("/life/today"),
  progress: () => apiRequest<Progress>("/life/progress"),
  groceryLists: () => apiRequest<GroceryList[]>("/life/grocery-lists"),
  createGroceryList: (value: CreateGroceryListInput) => apiRequest<GroceryList>("/life/grocery-lists", { method: "POST", body: JSON.stringify(value) }),
  archiveGroceryList: (listId: number) => apiRequest<GroceryList>(`/life/grocery-lists/${listId}/archive`, { method: "POST" }),
  addGroceryItem: (listId: number, value: object) => apiRequest<GroceryItem>(`/life/grocery-lists/${listId}/items`, { method: "POST", body: JSON.stringify(value) }),
  patchGroceryItem: (listId: number, itemId: number, value: object) => apiRequest<GroceryItem>(`/life/grocery-lists/${listId}/items/${itemId}`, { method: "PATCH", body: JSON.stringify(value) }),
  deleteGroceryItem: (listId: number, itemId: number) => apiRequest<void>(`/life/grocery-lists/${listId}/items/${itemId}`, { method: "DELETE" }),
  recurringGroceryItems: () => apiRequest<RecurringGroceryItem[]>("/life/recurring-grocery-items"),
  createRecurringGroceryItem: (value: object) => apiRequest<RecurringGroceryItem>("/life/recurring-grocery-items", { method: "POST", body: JSON.stringify(value) }),
  addRecurringGroceryItem: (listId: number, recurringId: number) => apiRequest<GroceryItem>(`/life/grocery-lists/${listId}/recurring-items/${recurringId}`, { method: "POST" })
};
