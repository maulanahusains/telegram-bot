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

export type ReminderInput = Omit<Reminder, "id" | "next_run_at" | "last_run_at">;

export const lifeApi = {
  profile: () => apiRequest<LifeProfile | null>("/life/profile"),
  saveProfile: (value: Omit<LifeProfile, "id">) => apiRequest<LifeProfile>("/life/profile", { method: "PUT", body: JSON.stringify(value) }),
  goals: () => apiRequest<NutritionGoal[]>("/life/goals"),
  createGoal: (value: Omit<NutritionGoal, "id">) => apiRequest<NutritionGoal>("/life/goals", { method: "POST", body: JSON.stringify(value) }),
  candidates: () => apiRequest<DestinationCandidate[]>("/life/notification-destination-candidates"),
  destinations: () => apiRequest<NotificationDestination[]>("/life/notification-destinations"),
  activateCandidate: (candidateId: number, value: { label?: string; make_default?: boolean }) => apiRequest<NotificationDestination>(`/life/notification-destination-candidates/${candidateId}/activate`, { method: "POST", body: JSON.stringify(value) }),
  patchDestination: (id: number, value: Partial<Pick<NotificationDestination, "label" | "enabled" | "is_default">>) => apiRequest<NotificationDestination>(`/life/notification-destinations/${id}`, { method: "PATCH", body: JSON.stringify(value) }),
  reminders: () => apiRequest<Reminder[]>("/life/reminders"),
  createReminder: (value: ReminderInput) => apiRequest<Reminder>("/life/reminders", { method: "POST", body: JSON.stringify(value) }),
  patchReminder: (id: number, value: Partial<ReminderInput>) => apiRequest<Reminder>(`/life/reminders/${id}`, { method: "PATCH", body: JSON.stringify(value) }),
  deleteReminder: (id: number) => apiRequest<void>(`/life/reminders/${id}`, { method: "DELETE" })
};
