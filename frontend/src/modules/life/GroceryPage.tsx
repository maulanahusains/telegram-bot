import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "../../app/api/client";
import { lifeApi, type CreateGroceryListInput, type GroceryCadence, type GroceryItem, type GroceryList } from "../../app/api/life";
import { CheckControl, PageHeader, SectionHeading } from "./LifeUI";
import { Icon } from "./icons";

const idr = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });

export function GroceryPage() {
  const client = useQueryClient();
  const lists = useQuery({ queryKey: ["life", "grocery-lists"], queryFn: lifeApi.groceryLists, refetchInterval: 60_000 });
  const recurring = useQuery({ queryKey: ["life", "recurring-grocery"], queryFn: lifeApi.recurringGroceryItems });
  const [error, setError] = useState<string | null>(null);
  const [archiveConfirmOpen, setArchiveConfirmOpen] = useState(false);
  const active = lists.data?.find((list) => list.status === "active");
  useEffect(() => { setArchiveConfirmOpen(false); }, [active?.id]);
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: ["life", "grocery-lists"] }), client.invalidateQueries({ queryKey: ["life", "recurring-grocery"] })]);
  const createList = useMutation({ mutationFn: lifeApi.createGroceryList, onSuccess: async () => { setError(null); await refresh(); }, onError: (reason) => setError(publicError(reason)) });
  const archiveList = useMutation({ mutationFn: lifeApi.archiveGroceryList, onSuccess: async () => { setError(null); setArchiveConfirmOpen(false); await refresh(); }, onError: (reason) => setError(publicError(reason)) });
  const addItem = useMutation({ mutationFn: ({ listId, value }: { listId: number; value: object }) => lifeApi.addGroceryItem(listId, value), onSuccess: refresh });
  const patchItem = useMutation({ mutationFn: ({ listId, itemId, value }: { listId: number; itemId: number; value: object }) => lifeApi.patchGroceryItem(listId, itemId, value), onSuccess: refresh });
  const createRecurring = useMutation({ mutationFn: lifeApi.createRecurringGroceryItem, onSuccess: refresh });
  const addRecurring = useMutation({ mutationFn: ({ listId, recurringId }: { listId: number; recurringId: number }) => lifeApi.addRecurringGroceryItem(listId, recurringId), onSuccess: refresh });

  if (lists.isPending || recurring.isPending) return <GroceryState text="Loading grocery lists…" />;
  if (lists.isError || recurring.isError) return <GroceryState text="Grocery data could not be loaded." error />;

  const unboughtCount = active?.items.filter((item) => !item.is_bought).length ?? 0;
  const handleArchive = () => { if (active) setArchiveConfirmOpen(true); };

  return <section className="life-page">
    <PageHeader eyebrow="Make the next choice easy" title="Grocery" description="Everything you need, at a glance." action={active ? <details className="new-reminder"><summary className="button button-primary"><Icon name="plus" size={17} />Add item</summary><GroceryItemForm onSubmit={(value) => addItem.mutate({ listId: active.id, value })} /></details> : undefined} />
    {error && <p className="form-error" role="alert">{error}</p>}
    {!active ? <section className="empty-state-card grocery-empty-state">
      <div className="grocery-empty-intro">
        <span className="grocery-empty-icon"><Icon name="cart" size={21} /></span>
        <strong>No active list</strong>
        <p>Start with a weekly or monthly list. Set custom dates when you need them.</p>
      </div>
      <CreateListForm submitting={createList.isPending} onSubmit={(value) => createList.mutate(value)} />
    </section> : <>
      <section className="grocery-summary">
        <div className="grocery-summary-main"><p className="eyebrow">{cadenceLabel(active.cadence)}</p><h2>{active.name}</h2><p>{formatDateRange(active)} <span aria-hidden="true">·</span> {unboughtCount} items left</p></div>
        <div className="grocery-summary-tools"><div className="grocery-total"><span>Estimated total</span><strong>{idr.format(active.estimated_total_rupiah)}</strong><small>{active.items.filter((item) => item.is_bought).length} of {active.items.length} items bought</small></div>{archiveConfirmOpen ? <div className="grocery-archive-confirm" role="alert"><div className="grocery-archive-message"><span className="grocery-archive-icon"><Icon name="warning" size={16} /></span><div><strong>Archive this list?</strong><p>{unboughtCount ? `${unboughtCount} item${unboughtCount === 1 ? " is" : "s are"} still unbought.` : "Everything is marked bought."}</p></div></div><div className="row-actions"><button className="button button-primary" type="button" onClick={() => archiveList.mutate(active.id)} disabled={archiveList.isPending}>{archiveList.isPending ? "Archiving…" : "Confirm archive"}</button><button className="button button-quiet" type="button" onClick={() => setArchiveConfirmOpen(false)} disabled={archiveList.isPending}>Keep list</button></div></div> : <button className="button button-quiet grocery-archive-button" type="button" onClick={handleArchive} disabled={archiveList.isPending}><Icon name="check" size={15} />Archive list</button>}</div>
      </section>
      <section className="content-section"><SectionHeading eyebrow="Keep it simple" title="To buy" count={`${unboughtCount} items`} /><div className="list-card grocery-list">{unboughtCount ? active.items.filter((item) => !item.is_bought).map((item) => <GroceryRow item={item} key={item.id} onToggle={() => patchItem.mutate({ listId: active.id, itemId: item.id, value: { is_bought: true } })} />) : <div className="empty-state"><Icon name="check" size={22} /><strong>Everything is bought</strong><p>Your active list is clear.</p></div>}<details className="add-row-disclosure"><summary className="add-row"><span className="add-row-icon"><Icon name="plus" size={18} /></span><span><strong>Add another item</strong><small>Keep the list focused on what matters</small></span><Icon name="arrow" className="arrow-icon" size={17} /></summary><GroceryItemForm onSubmit={(value) => addItem.mutate({ listId: active.id, value })} /></details></div></section>
      <details className="bought-disclosure"><summary><span className="disclosure-icon"><Icon name="check" size={18} /></span><span><strong>Bought</strong><small>{active.items.filter((item) => item.is_bought).length} items completed</small></span><Icon name="chevron" className="chevron" size={17} /></summary><div className="bought-items">{active.items.filter((item) => item.is_bought).map((item) => <GroceryRow item={item} key={item.id} onToggle={() => patchItem.mutate({ listId: active.id, itemId: item.id, value: { is_bought: false } })} />)}</div></details>
      <details className="setup-disclosure"><summary><span className="disclosure-icon"><Icon name="cart" size={18} /></span><span><strong>Add essentials</strong><small>Bring back recurring items in one tap</small></span><Icon name="chevron" className="chevron" size={17} /></summary><div className="setup-content"><div className="resource-list">{recurring.data.map((item) => <div className="resource-row" key={item.id}><div><strong>{item.name}</strong><span>{item.quantity} {item.unit} {item.enabled ? "· Active" : "· Paused"}</span></div><button className="button button-secondary" type="button" onClick={() => addRecurring.mutate({ listId: active.id, recurringId: item.id })}>Add to list</button></div>)}</div><form className="compact-form" onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const form = new FormData(event.currentTarget); createRecurring.mutate({ name: form.get("name"), quantity: Number(form.get("quantity")), unit: form.get("unit"), estimated_unit_price_rupiah: Number(form.get("price")) || null, enabled: true }); event.currentTarget.reset(); }}><h3>New recurring item</h3><GroceryItemFields /><button className="button button-primary" disabled={createRecurring.isPending}>{createRecurring.isPending ? "Saving…" : "Save recurring"}</button></form></div></details>
    </>}
  </section>;
}

function GroceryRow({ item, onToggle }: { item: GroceryItem; onToggle: () => void }) {
  return <div className={`grocery-row ${item.is_bought ? "is-bought" : ""}`}><CheckControl checked={item.is_bought} label={`${item.is_bought ? "Unmark" : "Mark"} ${item.name}`} onChange={onToggle} /><span className="grocery-row-main"><strong>{item.name}</strong><small>{item.quantity} {item.unit}</small></span><span className="grocery-price">{item.estimated_total_rupiah === null ? "No estimate" : idr.format(item.estimated_total_rupiah)}</span></div>;
}

function GroceryItemFields() {
  return <div className="field-grid"><label className="field"><span>Item</span><input name="name" required placeholder="Chicken breast" /></label><label className="field"><span>Quantity</span><input name="quantity" type="number" step="0.01" min="0.01" defaultValue="1" required /></label><label className="field"><span>Unit</span><input name="unit" required placeholder="kg" /></label><label className="field"><span>Price / unit</span><input name="price" type="number" min="0" placeholder="IDR" /></label></div>;
}

function GroceryItemForm({ onSubmit }: { onSubmit: (value: object) => void }) {
  return <form className="sheet-form" onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const form = new FormData(event.currentTarget); onSubmit({ name: form.get("name"), quantity: Number(form.get("quantity")), unit: form.get("unit"), estimated_unit_price_rupiah: Number(form.get("price")) || null }); event.currentTarget.reset(); }}><div className="sheet-heading"><div><p className="eyebrow">Quick add</p><h2>Add item</h2></div><Icon name="cart" size={18} /></div><GroceryItemFields /><button className="button button-primary" type="submit">Add item</button></form>;
}

function CreateListForm({ submitting, onSubmit }: { submitting: boolean; onSubmit: (value: CreateGroceryListInput) => void }) {
  const [cadence, setCadence] = useState<GroceryCadence>("weekly");
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") || "Weekly shopping");
    if (cadence === "custom") {
      onSubmit({ name, cadence, starts_on: String(form.get("starts_on")), ends_on: String(form.get("ends_on")) });
      return;
    }
    onSubmit({ name, cadence });
  };

  return <form className="compact-form grocery-create-form w-full max-w-[520px] text-left" onSubmit={submit}>
    <label className="field"><span>List name</span><input name="name" defaultValue="Weekly shopping" required /></label>
    <div className="field"><span>Cadence</span><div className="grid grid-cols-2 gap-2" role="group" aria-label="List cadence"><button className={`inline-flex min-h-10 items-center justify-center gap-1.5 rounded-[11px] border border-life-border-strong bg-transparent px-3 text-xs font-bold text-life-muted transition duration-150 hover:border-life-primary hover:bg-life-primary-soft ${cadence === "weekly" ? "border-life-primary bg-life-primary-soft text-life-primary" : ""}`} type="button" aria-pressed={cadence === "weekly"} onClick={() => setCadence("weekly")}>Weekly {cadence === "weekly" && <Icon name="check" size={14} />}</button><button className={`inline-flex min-h-10 items-center justify-center gap-1.5 rounded-[11px] border border-life-border-strong bg-transparent px-3 text-xs font-bold text-life-muted transition duration-150 hover:border-life-primary hover:bg-life-primary-soft ${cadence === "monthly" ? "border-life-primary bg-life-primary-soft text-life-primary" : ""}`} type="button" aria-pressed={cadence === "monthly"} onClick={() => setCadence("monthly")}>Monthly {cadence === "monthly" && <Icon name="check" size={14} />}</button></div></div>
    {cadence === "custom" ? <><div className="field-grid"><label className="field"><span>Starts</span><input name="starts_on" type="date" required /></label><label className="field"><span>Ends</span><input name="ends_on" type="date" required /></label></div><button className="inline-flex items-center gap-1 self-start border-0 bg-transparent p-0 text-[11px] font-bold text-life-primary" type="button" onClick={() => setCadence("weekly")}><Icon name="arrow" className="rotate-180" size={14} />Use a quick cadence</button></> : <button className="inline-flex items-center gap-1 self-start border-0 bg-transparent p-0 text-[11px] font-bold text-life-primary" type="button" onClick={() => setCadence("custom")}>Set custom dates <Icon name="arrow" size={14} /></button>}
    <button className="button button-primary" disabled={submitting}>{submitting ? "Creating…" : "Create list"}</button>
  </form>;
}

function cadenceLabel(cadence: GroceryCadence) {
  return cadence === "weekly" ? "This week" : cadence === "monthly" ? "This month" : "Custom period";
}

function formatDateRange(list: GroceryList) { return `${new Date(`${list.starts_on}T00:00:00`).toLocaleDateString([], { month: "short", day: "numeric" })} – ${new Date(`${list.ends_on}T00:00:00`).toLocaleDateString([], { month: "short", day: "numeric" })}`; }
function publicError(error: unknown) { return error instanceof ApiError ? error.message : "The grocery list request could not be completed."; }
function GroceryState({ text, error = false }: { text: string; error?: boolean }) { return <section className="life-page"><PageHeader eyebrow="Grocery" title="Grocery" /><p className={error ? "form-error" : "muted"} role={error ? "alert" : undefined}>{text}</p></section>; }
