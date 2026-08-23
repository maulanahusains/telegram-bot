import { useQuery } from "@tanstack/react-query";

import { lifeApi } from "../../app/api/life";
import { ArrowLink, PageHeader, SectionHeading } from "./LifeUI";
import { Icon } from "./icons";

export function ProgressPage() {
  const progress = useQuery({ queryKey: ["life", "progress"], queryFn: lifeApi.progress });
  if (progress.isPending) return <ProgressState text="Loading progress…" />;
  if (progress.isError) return <ProgressState text="Progress data could not be loaded." error />;

  const data = progress.data;
  const weights = data.weights.slice(-7);
  const weightValues = weights.map((entry) => Number(entry.weight_kg));
  const latestWeight = weightValues.at(-1);
  const firstWeight = weightValues[0];
  const weightChange = latestWeight !== undefined && firstWeight !== undefined ? latestWeight - firstWeight : null;
  const chart = createChart(weightValues);
  const completed = data.days.reduce((total, day) => total + day.workout_done, 0);
  const skipped = data.days.reduce((total, day) => total + day.workout_skipped, 0);
  const planned = completed + skipped;

  return <section className="life-page"><PageHeader eyebrow="Notice the quiet momentum" title="Progress" description="Trends first, details when you need them." action={<div className="range-switch" aria-label="Progress date range"><button className="is-selected" type="button">7 days</button><button type="button" disabled>30 days</button></div>} />
    <section className="progress-feature" aria-labelledby="weight-title"><div className="progress-feature-heading"><div><p className="eyebrow">Weight trend</p><h2 id="weight-title">{weightChange !== null && weightChange <= 0 ? "A steady direction" : "Your latest check-in"}</h2></div>{weightChange !== null && <span className="trend-badge"><Icon name="trend" size={14} />{weightChange > 0 ? "+" : "−"}{Math.abs(weightChange).toFixed(1)} kg</span>}</div>{latestWeight === undefined ? <div className="empty-state"><Icon name="scale" size={22} /><strong>No weight logs yet</strong><p>Log your first check-in from Today.</p></div> : <><div className="weight-metric"><strong>{latestWeight.toFixed(1)}</strong><span>kg</span><small>{firstWeight !== undefined && firstWeight !== latestWeight ? `from ${firstWeight.toFixed(1)} kg at the start of this range` : "latest logged weight"}</small></div><div className="chart-wrap" role="img" aria-label="Weight trend over the selected range"><svg className="trend-chart" viewBox="0 0 620 190" preserveAspectRatio="none" fill="none"><path className="chart-grid" d="M0 25h620M0 83h620M0 141h620" />{chart.area && <path className="chart-area" d={chart.area} />}{chart.line && <path className="chart-line" d={chart.line} />}{chart.last && <circle className="chart-point" cx={chart.last.x} cy={chart.last.y} r="5" />}</svg><div className="chart-labels"><span>{weights[0]?.local_date ?? data.start_date}</span><span>{weights[Math.floor(weights.length / 2)]?.local_date ?? data.start_date}</span><span>{weights.at(-1)?.local_date ?? data.end_date}</span></div></div></>}</section>
    <section className="content-section"><SectionHeading eyebrow="Daily consistency" title="Nutrition" count={`${data.days.filter((day) => isOnTarget(day.calories_consumed, day.calorie_target_kcal)).length} of ${data.days.length} on target`} /><div className="adherence-card">{data.days.length ? data.days.map((day) => { const percent = day.calorie_target_kcal ? (day.calories_consumed / day.calorie_target_kcal) * 100 : 0; const onTarget = isOnTarget(day.calories_consumed, day.calorie_target_kcal); return <div className="adherence-row" key={day.date}><div className="adherence-label"><strong>{day.date}</strong><small>{day.calories_consumed} / {day.calorie_target_kcal ?? "—"} kcal <span aria-hidden="true">·</span> {day.protein_consumed} g protein</small></div><span className={`adherence-status ${onTarget ? "is-on-track" : "is-neutral"}`}>{onTarget ? "On target" : "Partial"}</span><div className="day-bar"><span className={onTarget ? "" : "is-partial"} style={{ width: `${Math.min(100, percent)}%` }} /></div></div>; }) : <div className="empty-state"><Icon name="flame" size={22} /><strong>No nutrition history yet</strong><p>Today’s logs will build this view.</p></div>}</div></section>
    <section className="content-section"><SectionHeading eyebrow="Keep moving in your way" title="Workouts" action={<ArrowLink to="/app/planner">View planner</ArrowLink>} /><div className="workout-summary"><div className="workout-summary-stat"><span className="summary-icon"><Icon name="workout" size={15} /></span><strong>{completed}</strong><small>completed</small></div><div className="workout-summary-stat"><span className="summary-icon summary-icon-warm"><Icon name="clock" size={15} /></span><strong>{planned}</strong><small>planned</small></div><div className="workout-summary-copy"><strong>{planned ? `${completed} of ${planned} completed` : "No workouts logged"}</strong><p>{skipped ? `${skipped} skipped in this range.` : "Your next plan will appear here."}</p></div></div></section>
    <details className="history-disclosure"><summary><span className="disclosure-icon"><Icon name="trend" size={18} /></span><span><strong>View detailed history</strong><small>Meals, weight logs, and workouts</small></span><Icon name="chevron" className="chevron" size={17} /></summary><div className="history-content">{data.weights.slice().reverse().map((entry) => <p key={entry.id}><strong>{entry.local_date}</strong><span>Weight logged · {entry.weight_kg} kg</span></p>)}</div></details>
  </section>;
}

function createChart(values: number[]) {
  if (values.length < 2) return { area: "", line: "", last: null };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = Math.max(max - min, 0.4);
  const points = values.map((value, index) => ({ x: (index / (values.length - 1)) * 620, y: 150 - ((value - min) / spread) * 120 }));
  const line = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ");
  return { line, area: `${line} L620 180 L0 180 Z`, last: points.at(-1) ?? null };
}

function isOnTarget(consumed: number, target: number | null) { return target !== null && consumed >= target * 0.8 && consumed <= target * 1.1; }
function ProgressState({ text, error = false }: { text: string; error?: boolean }) { return <section className="life-page"><PageHeader eyebrow="Progress" title="Progress" /><p className={error ? "form-error" : "muted"} role={error ? "alert" : undefined}>{text}</p></section>; }
