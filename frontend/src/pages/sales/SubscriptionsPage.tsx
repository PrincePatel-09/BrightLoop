import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";

type Subscription = { id: number; number: string; customer_name: string; customer_email: string; product_name: string; plan_name: string; quantity: number; unit_price: string; billing_interval: string; interval_count: number; status: string; start_date: string; next_billing_date: string };

export function SubscriptionsPage() {
  const [rows, setRows] = useState<Subscription[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function load() { setRows(await api<Subscription[]>("/sales/subscriptions")); }
  useEffect(() => { void load().catch(err => setError(err instanceof ApiError ? err.message : "Unable to load subscriptions")); }, []);
  async function setStatus(row: Subscription, status: string) {
    setError(""); setMessage("");
    try { await api(`/sales/subscriptions/${row.id}`, { method: "PATCH", body: JSON.stringify({ status }) }); setMessage(`${row.number} is now ${status}.`); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update subscription"); }
  }
  return <div className="space-y-6"><div><h1 className="page-title">Subscriptions</h1><p className="mt-1 text-sm text-muted">Review active customer agreements and their next billing dates.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}{message && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-success">{message}</p>}
    <div className="grid gap-4">{rows.map(row => <Card key={row.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="font-semibold">{row.number} <span className="ml-2 rounded-full bg-canvas px-2 py-1 text-xs capitalize">{row.status}</span></h2><p className="mt-1 text-sm text-muted">{row.customer_name} · {row.customer_email}</p><p className="mt-2 text-sm">{row.quantity} × {row.product_name} / {row.plan_name} · {row.unit_price} every {row.interval_count} {row.billing_interval}{row.interval_count > 1 ? "s" : ""}</p><p className="mt-1 text-xs text-muted">Started {row.start_date} · Next bill {row.next_billing_date}</p></div><div className="flex gap-2">{row.status === "active" && <Button size="sm" variant="secondary" onClick={() => void setStatus(row, "paused")}>Pause</Button>}{row.status === "paused" && <Button size="sm" variant="secondary" onClick={() => void setStatus(row, "active")}>Resume</Button>}{["active", "paused"].includes(row.status) && <Button size="sm" variant="danger" onClick={() => void setStatus(row, "cancelled")}>Cancel</Button>}</div></div></Card>)}{rows.length === 0 && <Card className="text-sm text-muted">No subscriptions yet. Convert an accepted quotation to create one.</Card>}</div>
  </div>;
}
