import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useState } from "react";

import { ApiError } from "../../app/api/client";
import { lifeApi, type RecurrenceRule, type Reminder, type ReminderInput } from "../../app/api/life";

const weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

export function PlannerPage() {
  const client = useQueryClient();
  const reminders = useQuery({ queryKey: ["life", "reminders"], queryFn: lifeApi.reminders });
  const destinations = useQuery({ queryKey: ["life", "destinations"], queryFn: lifeApi.destinations });
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Reminder | null>(null);
  const save = useMutation({
    mutationFn: (value: ReminderInput) => editing ? lifeApi.patchReminder(editing.id, value) : lifeApi.createReminder(value),
    onSuccess: async () => {
      setError(null);
      setEditing(null);
      await client.invalidateQueries({ queryKey: ["life", "reminders"] });
    },
    onError: (reason) => setError(publicError(reason))
  });
  const patch = useMutation({ mutationFn: ({ id, value }: { id: number; value: object }) => lifeApi.patchReminder(id, value), onSuccess: () => client.invalidateQueries({ queryKey: ["life", "reminders"] }) });
  const remove = useMutation({ mutationFn: lifeApi.deleteReminder, onSuccess: () => client.invalidateQueries({ queryKey: ["life", "reminders"] }) });

  if (reminders.isPending || destinations.isPending) return <Section title="Planner">Loading reminders…</Section>;
  if (reminders.isError || destinations.isError) return <Section title="Planner">{publicError(reminders.error ?? destinations.error)}</Section>;

  return (
    <section className="feature-page">
      <div className="feature-heading"><div><p className="eyebrow">Life</p><h1>Planner</h1></div><p>Create structured one-time or recurring reminders.</p></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <ReminderForm key={editing?.id ?? "new"} destinations={destinations.data.filter((item) => item.enabled)} editing={editing} submitting={save.isPending} onCancel={() => setEditing(null)} onSubmit={(value) => save.mutate(value)} />
      <div className="list-card"><h2>Reminders</h2>{reminders.data.length === 0 ? <p className="muted">No reminders yet.</p> : <ul className="resource-list">{reminders.data.map((item) => <li key={item.id}><div><strong>{item.title}</strong><span>{scheduleLabel(item)} · {item.enabled ? "Enabled" : "Disabled"}</span></div><div className="row-actions"><button type="button" onClick={() => setEditing(item)}>Edit</button><button type="button" onClick={() => patch.mutate({ id: item.id, value: { enabled: !item.enabled } })}>{item.enabled ? "Disable" : "Enable"}</button><button type="button" className="danger" onClick={() => remove.mutate(item.id)}>Delete</button></div></li>)}</ul>}</div>
    </section>
  );
}

function ReminderForm({ destinations, editing, submitting, onCancel, onSubmit }: { destinations: Awaited<ReturnType<typeof lifeApi.destinations>>; editing: Reminder | null; submitting: boolean; onCancel: () => void; onSubmit: (value: ReminderInput) => void }) {
  const [scheduleType, setScheduleType] = useState<"one_time" | "recurring">(editing?.schedule_type ?? "recurring");
  const [frequency, setFrequency] = useState<"daily" | "weekly">(editing?.recurrence?.frequency ?? "weekly");
  const [selectedDays, setSelectedDays] = useState<Set<string>>(new Set(editing?.recurrence?.weekdays ?? ["mon", "wed", "fri"]));
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const timezone = String(form.get("timezone") || Intl.DateTimeFormat().resolvedOptions().timeZone);
    const base = { title: String(form.get("title")), notes: String(form.get("notes") || "") || null, kind: String(form.get("kind")) as ReminderInput["kind"], schedule_type: scheduleType, timezone, destination_id: Number(form.get("destination_id")), enabled: true };
    if (scheduleType === "one_time") {
      const local = String(form.get("scheduled_at"));
      onSubmit({ ...base, scheduled_at: new Date(local).toISOString(), recurrence: null });
      return;
    }
    const recurrence: RecurrenceRule = { frequency, time: String(form.get("time")), weekdays: frequency === "weekly" ? [...selectedDays] as RecurrenceRule["weekdays"] : [] };
    onSubmit({ ...base, scheduled_at: null, recurrence });
  };
  return <form className="form-card" onSubmit={submit}><h2>{editing ? "Edit reminder" : "Create reminder"}</h2><label>Title<input name="title" required maxLength={255} placeholder="Lunch" defaultValue={editing?.title} /></label><label>Kind<select name="kind" defaultValue={editing?.kind ?? "reminder"}><option value="reminder">Reminder</option><option value="routine">Routine</option><option value="meal">Meal</option><option value="workout">Workout</option></select></label><label>Destination<select name="destination_id" required disabled={!destinations.length} defaultValue={editing?.destination_id ?? ""}><option value="">Select an enabled destination</option>{destinations.map((item) => <option value={item.id} key={item.id}>{item.label}{item.is_default ? " (default)" : ""}</option>)}</select></label><label>Timezone<input name="timezone" defaultValue={editing?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone} required /></label><fieldset><legend>Schedule</legend><label><input type="radio" checked={scheduleType === "recurring"} onChange={() => setScheduleType("recurring")} /> Recurring</label><label><input type="radio" checked={scheduleType === "one_time"} onChange={() => setScheduleType("one_time")} /> One time</label></fieldset>{scheduleType === "one_time" ? <label>When<input name="scheduled_at" type="datetime-local" required defaultValue={toLocalInput(editing?.scheduled_at)} /></label> : <><label>Frequency<select name="frequency" value={frequency} onChange={(event) => setFrequency(event.target.value as "daily" | "weekly")}><option value="daily">Every day</option><option value="weekly">Specific weekdays</option></select></label><label>Time<input name="time" type="time" required defaultValue={editing?.recurrence?.time ?? "08:00"} /></label>{frequency === "weekly" && <div className="weekday-row">{weekdays.map((day) => <label key={day}><input type="checkbox" checked={selectedDays.has(day)} onChange={() => setSelectedDays((current) => { const next = new Set(current); next.has(day) ? next.delete(day) : next.add(day); return next; })} />{day}</label>)}</div>}</>}<label>Notes (optional)<textarea name="notes" maxLength={1000} defaultValue={editing?.notes ?? ""} /></label><div className="row-actions"><button className="button button-primary" disabled={submitting || !destinations.length}>{submitting ? "Saving…" : editing ? "Save reminder" : "Create reminder"}</button>{editing && <button type="button" onClick={onCancel}>Cancel edit</button>}</div></form>;
}

function scheduleLabel(item: Awaited<ReturnType<typeof lifeApi.reminders>>[number]) { if (item.schedule_type === "one_time") return item.scheduled_at ? new Date(item.scheduled_at).toLocaleString() : "One time"; return item.recurrence?.frequency === "daily" ? `Daily at ${item.recurrence.time}` : `${item.recurrence?.weekdays.join(", ")} at ${item.recurrence?.time}`; }
function toLocalInput(value?: string | null) { if (!value) return ""; const date = new Date(value); const offset = date.getTimezoneOffset() * 60_000; return new Date(date.getTime() - offset).toISOString().slice(0, 16); }
function publicError(error: unknown) { return error instanceof ApiError ? error.message : "The Planner request could not be completed."; }
function Section({ title, children }: { title: string; children: ReactNode }) { return <section className="feature-page"><h1>{title}</h1><p className="muted">{children}</p></section>; }
