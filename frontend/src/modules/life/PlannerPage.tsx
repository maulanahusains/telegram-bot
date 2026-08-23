import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { ApiError } from "../../app/api/client";
import { lifeApi, type RecurrenceRule, type Reminder, type ReminderInput } from "../../app/api/life";
import { IconButton, LifeSelect, PageHeader, SectionHeading, StatusChip, Toggle } from "./LifeUI";
import { Icon, type IconName } from "./icons";

const weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

export function PlannerPage() {
  const client = useQueryClient();
  const reminders = useQuery({ queryKey: ["life", "reminders"], queryFn: lifeApi.reminders });
  const destinations = useQuery({ queryKey: ["life", "destinations"], queryFn: lifeApi.destinations });
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Reminder | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const save = useMutation({ mutationFn: (value: ReminderInput) => editing ? lifeApi.patchReminder(editing.id, value) : lifeApi.createReminder(value), onSuccess: async () => { setError(null); setEditing(null); setFormOpen(false); await client.invalidateQueries({ queryKey: ["life", "reminders"] }); }, onError: (reason) => setError(publicError(reason)) });
  const patch = useMutation({ mutationFn: ({ id, value }: { id: number; value: object }) => lifeApi.patchReminder(id, value), onSuccess: () => client.invalidateQueries({ queryKey: ["life", "reminders"] }) });
  const remove = useMutation({ mutationFn: lifeApi.deleteReminder, onSuccess: () => client.invalidateQueries({ queryKey: ["life", "reminders"] }) });

  if (reminders.isPending || destinations.isPending) return <PlannerState text="Loading reminders…" />;
  if (reminders.isError || destinations.isError) return <PlannerState text={publicError(reminders.error ?? destinations.error)} error />;

  const activeCount = reminders.data.filter((item) => item.enabled).length;
  const enabledDestinations = destinations.data.filter((item) => item.enabled);
  return <section className="life-page">
    <PageHeader eyebrow="Keep your rhythm visible" title="Planner" description="A clear view of the commitments coming next." action={<details className="new-reminder" open={formOpen || Boolean(editing)} onToggle={(event) => setFormOpen((event.currentTarget as HTMLDetailsElement).open)}><summary className="button button-primary"><Icon name="plus" size={17} />New reminder</summary><ReminderForm key={editing?.id ?? "new"} destinations={enabledDestinations} editing={editing} submitting={save.isPending} onCancel={() => { setEditing(null); setFormOpen(false); }} onSubmit={(value) => save.mutate(value)} /></details>} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="summary-strip"><div className="summary-stat"><span className="summary-icon"><Icon name="calendar" size={17} /></span><strong>{activeCount}</strong><small>active plans</small></div><div className="summary-stat"><span className="summary-icon"><Icon name="clock" size={17} /></span><strong>{reminders.data.length}</strong><small>all reminders</small></div><div className="summary-stat"><span className="summary-icon summary-icon-warm"><Icon name="plus" size={17} /></span><strong>{enabledDestinations.length}</strong><small>destinations</small></div></div>
    <section className="content-section"><SectionHeading eyebrow="Your commitments" title="Upcoming" count={`${reminders.data.length} items`} /><div className="list-card planner-list">{reminders.data.length ? reminders.data.map((item) => <ReminderRow item={item} key={item.id} onEdit={() => { setEditing(item); setFormOpen(true); }} onToggle={() => patch.mutate({ id: item.id, value: { enabled: !item.enabled } })} onDelete={() => remove.mutate(item.id)} />) : <div className="empty-state"><Icon name="calendar" size={22} /><strong>No reminders yet</strong><p>Create one small plan to get started.</p></div>}</div></section>
  </section>;
}

function ReminderRow({ item, onEdit, onToggle, onDelete }: { item: Reminder; onEdit: () => void; onToggle: () => void; onDelete: () => void }) {
  const icon: IconName = item.kind === "workout" ? "workout" : item.kind === "meal" ? "flame" : item.kind === "routine" ? "calendar" : "bell";
  return <div className="planner-row"><span className={`planner-icon ${item.enabled ? "planner-icon-green" : ""}`}><Icon name={icon} size={19} /></span><div className="planner-row-main"><div className="row-title"><strong>{item.title}</strong><StatusChip tone={item.enabled ? "green" : "muted"}>{item.enabled ? "Active" : "Paused"}</StatusChip></div><p>{scheduleLabel(item)} <span aria-hidden="true">·</span> {item.timezone} <span aria-hidden="true">·</span> {item.kind}</p></div><div className="planner-row-actions"><Toggle checked={item.enabled} label={`${item.enabled ? "Disable" : "Enable"} ${item.title}`} onChange={onToggle} /><IconButton label={`Edit ${item.title}`} icon="edit" onClick={onEdit} /><IconButton label={`Delete ${item.title}`} icon="close" onClick={onDelete} /></div></div>;
}

function ReminderForm({ destinations, editing, submitting, onCancel, onSubmit }: { destinations: Awaited<ReturnType<typeof lifeApi.destinations>>; editing: Reminder | null; submitting: boolean; onCancel: () => void; onSubmit: (value: ReminderInput) => void }) {
  const [scheduleType, setScheduleType] = useState<"one_time" | "recurring">(editing?.schedule_type ?? "recurring");
  const [frequency, setFrequency] = useState<"daily" | "weekly">(editing?.recurrence?.frequency ?? "weekly");
  const [kind, setKind] = useState<ReminderInput["kind"]>(editing?.kind ?? "reminder");
  const [destinationId, setDestinationId] = useState(String(editing?.destination_id ?? ""));
  const [selectedDays, setSelectedDays] = useState<Set<string>>(new Set(editing?.recurrence?.weekdays ?? ["mon", "wed", "fri"]));
  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const form = new FormData(event.currentTarget); const timezone = String(form.get("timezone") || Intl.DateTimeFormat().resolvedOptions().timeZone); const base = { title: String(form.get("title")), notes: String(form.get("notes") || "") || null, kind, schedule_type: scheduleType, timezone, destination_id: Number(destinationId), enabled: true }; if (scheduleType === "one_time") { const scheduledDate = String(form.get("scheduled_date")); const scheduledTime = String(form.get("scheduled_time")); onSubmit({ ...base, scheduled_at: new Date(`${scheduledDate}T${scheduledTime}`).toISOString(), recurrence: null }); return; } const recurrence: RecurrenceRule = { frequency, time: String(form.get("time")), weekdays: frequency === "weekly" ? [...selectedDays] as RecurrenceRule["weekdays"] : [] }; onSubmit({ ...base, scheduled_at: null, recurrence }); };
  return <form className="sheet-form" onSubmit={submit}><div className="sheet-heading"><div><p className="eyebrow">Quick setup</p><h2>{editing ? "Edit reminder" : "New reminder"}</h2></div><IconButton label="Close reminder form" icon="close" onClick={onCancel} /></div><label className="field"><span>What do you want to remember?</span><input name="title" required maxLength={255} placeholder="Evening walk" defaultValue={editing?.title} /></label><div className="field-grid"><label className="field"><span>Kind</span><LifeSelect name="kind" value={kind} onChange={(value) => setKind(value as ReminderInput["kind"])} options={[{ value: "reminder", label: "Reminder" }, { value: "routine", label: "Routine" }, { value: "meal", label: "Meal" }, { value: "workout", label: "Workout" }]} /></label><label className="field"><span>Destination</span><LifeSelect name="destination_id" value={destinationId} onChange={setDestinationId} options={destinations.map((item) => ({ value: String(item.id), label: `${item.label}${item.is_default ? " (default)" : ""}` }))} placeholder="Select destination" required disabled={!destinations.length} /></label></div><label className="field"><span>Timezone</span><input name="timezone" defaultValue={editing?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone} required /></label><div className="choice-row"><label className="choice"><input type="radio" checked={scheduleType === "recurring"} onChange={() => setScheduleType("recurring")} />Recurring</label><label className="choice"><input type="radio" checked={scheduleType === "one_time"} onChange={() => setScheduleType("one_time")} />One time</label></div>{scheduleType === "one_time" ? <div className="field-grid reminder-when-grid"><label className="field"><span>Date</span><input name="scheduled_date" type="date" required defaultValue={toLocalDateInput(editing?.scheduled_at)} /></label><label className="field"><span>Time</span><input name="scheduled_time" type="time" required defaultValue={toLocalTimeInput(editing?.scheduled_at)} /></label></div> : <><div className="field-grid"><label className="field"><span>Frequency</span><LifeSelect name="frequency" value={frequency} onChange={(value) => setFrequency(value as "daily" | "weekly")} options={[{ value: "daily", label: "Every day" }, { value: "weekly", label: "Specific weekdays" }]} /></label><label className="field"><span>Time</span><input name="time" type="time" required defaultValue={editing?.recurrence?.time ?? "08:00"} /></label></div>{frequency === "weekly" && <div className="weekday-row">{weekdays.map((day) => <label key={day}><input type="checkbox" checked={selectedDays.has(day)} onChange={() => setSelectedDays((current) => { const next = new Set(current); next.has(day) ? next.delete(day) : next.add(day); return next; })} />{day}</label>)}</div>}</>}<label className="field"><span>Notes (optional)</span><textarea name="notes" maxLength={1000} defaultValue={editing?.notes ?? ""} /></label><div className="row-actions"><button className="button button-primary" disabled={submitting || !destinations.length}>{submitting ? "Saving…" : editing ? "Save reminder" : "Create reminder"}</button>{editing && <button className="button button-quiet" type="button" onClick={onCancel}>Cancel</button>}</div></form>;
}

function scheduleLabel(item: Reminder) {
  if (item.schedule_type === "one_time") return item.scheduled_at ? new Date(item.scheduled_at).toLocaleString() : "One time";
  return item.recurrence?.frequency === "daily" ? `Daily at ${item.recurrence.time}` : `${item.recurrence?.weekdays.join(", ")} at ${item.recurrence?.time}`;
}

function toLocalDateInput(value?: string | null) { if (!value) return ""; const date = new Date(value); const offset = date.getTimezoneOffset() * 60_000; return new Date(date.getTime() - offset).toISOString().slice(0, 10); }
function toLocalTimeInput(value?: string | null) { if (!value) return ""; const date = new Date(value); const offset = date.getTimezoneOffset() * 60_000; return new Date(date.getTime() - offset).toISOString().slice(11, 16); }
function publicError(error: unknown) { return error instanceof ApiError ? error.message : "The Planner request could not be completed."; }
function PlannerState({ text, error = false }: { text: string; error?: boolean }) { return <section className="life-page"><PageHeader eyebrow="Planner" title="Planner" /><p className={error ? "form-error" : "muted"} role={error ? "alert" : undefined}>{text}</p></section>; }
