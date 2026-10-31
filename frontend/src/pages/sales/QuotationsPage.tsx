import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Customer = { id: number; name: string; email: string };
type Plan = { id: number; product_id: number; name: string; price: string; billing_interval: string; interval_count: number };
type Product = { id: number; variants: { id: number; attribute: string; name: string; price_extra: string; is_active: boolean }[] };
type Quote = { id: number; number: string; customer_id: number; customer_name: string; customer_email: string; product_name: string; plan_name: string; quantity: number; unit_price: string; billing_interval: string; interval_count: number; status: string; valid_until: string; discount_code: string | null; discount_amount: string };

export function QuotationsPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [form, setForm] = useState({ customer_id: "", plan_id: "", variant_id: "", quantity: "1", valid_until: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10), discount_code: "" });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function load() {
    const [customerRows, planRows, quoteRows, productRows] = await Promise.all([
      api<Customer[]>("/customers?limit=100"), api<Plan[]>("/catalog/plans"), api<Quote[]>("/sales/quotations"), api<Product[]>("/catalog/products"),
    ]);
    setCustomers(customerRows); setPlans(planRows); setQuotes(quoteRows); setProducts(productRows);
    setForm(current => ({ ...current, customer_id: current.customer_id || String(customerRows[0]?.id ?? ""), plan_id: current.plan_id || String(planRows[0]?.id ?? "") }));
  }
  useEffect(() => { void load().catch(err => setError(err instanceof ApiError ? err.message : "Unable to load quotations")); }, []);

  async function create(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(""); setMessage("");
    try {
      await api("/sales/quotations", { method: "POST", body: JSON.stringify({ ...form, customer_id: Number(form.customer_id), plan_id: Number(form.plan_id), variant_id: form.variant_id ? Number(form.variant_id) : null, quantity: Number(form.quantity), notes: null }) });
      setMessage("Quotation created as draft."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create quotation"); }
    finally { setPending(false); }
  }

  const selectedPlan = plans.find(plan => String(plan.id) === form.plan_id);
  const variants = products.find(product => product.id === selectedPlan?.product_id)?.variants.filter(variant => variant.is_active) ?? [];

  async function changeStatus(quote: Quote, status: string) {
    setError(""); setMessage("");
    try { await api(`/sales/quotations/${quote.id}`, { method: "PATCH", body: JSON.stringify({ status }) }); setMessage(`${quote.number} marked ${status}.`); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update quotation"); }
  }
  async function convert(quote: Quote) {
    setError(""); setMessage("");
    try { await api(`/sales/quotations/${quote.id}/convert`, { method: "POST" }); setMessage(`${quote.number} converted to an active subscription.`); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to convert quotation"); }
  }

  return <div className="space-y-6">
    <div><h1 className="page-title">Quotations</h1><p className="mt-1 text-sm text-muted">Prepare a customer offer from an active plan and convert accepted offers to subscriptions.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}{message && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-success">{message}</p>}
    <Card><h2 className="font-semibold">New quotation</h2><form onSubmit={create} className="mt-4 grid gap-4 md:grid-cols-4">
      <div className="space-y-1.5"><Label htmlFor="quote-customer">Customer</Label><select id="quote-customer" required className="h-[42px] w-full rounded-xl border border-line bg-white px-3 text-sm" value={form.customer_id} onChange={e => setForm({ ...form, customer_id: e.target.value })}>{customers.map(c => <option key={c.id} value={c.id}>{c.name} · {c.email}</option>)}</select></div>
      <div className="space-y-1.5"><Label htmlFor="quote-plan">Plan</Label><select id="quote-plan" required className="h-[42px] w-full rounded-xl border border-line bg-white px-3 text-sm" value={form.plan_id} onChange={e => setForm({ ...form, plan_id: e.target.value, variant_id: "" })}>{plans.map(p => <option key={p.id} value={p.id}>{p.name} · {p.price}/{p.billing_interval}</option>)}</select></div>
      {variants.length > 0 && <div className="space-y-1.5"><Label htmlFor="quote-variant">Product variant</Label><select id="quote-variant" className="h-[42px] w-full rounded-xl border border-line bg-white px-3 text-sm" value={form.variant_id} onChange={e => setForm({ ...form, variant_id: e.target.value })}><option value="">Standard (no surcharge)</option>{variants.map(v => <option key={v.id} value={v.id}>{v.attribute}: {v.name} (+{v.price_extra})</option>)}</select></div>}
      <div className="space-y-1.5"><Label htmlFor="quote-quantity">Quantity</Label><Input id="quote-quantity" type="number" min="1" max="10000" value={form.quantity} onChange={e => setForm({ ...form, quantity: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="quote-expiry">Valid until</Label><Input id="quote-expiry" type="date" min={new Date().toISOString().slice(0, 10)} required value={form.valid_until} onChange={e => setForm({ ...form, valid_until: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="quote-discount">Discount code (optional)</Label><Input id="quote-discount" maxLength={40} value={form.discount_code} onChange={e => setForm({ ...form, discount_code: e.target.value.toUpperCase() })} /></div>
      <div className="md:col-span-4"><Button disabled={pending || customers.length === 0 || plans.length === 0}>{pending ? "Saving..." : "Create quotation"}</Button>{(!customers.length || !plans.length) && <span className="ml-3 text-sm text-muted">Add a customer and an active plan first.</span>}</div>
    </form></Card>
    <div className="grid gap-4">{quotes.map(q => <Card key={q.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="font-semibold">{q.number} <span className="ml-2 rounded-full bg-canvas px-2 py-1 text-xs font-medium capitalize">{q.status}</span></h2><p className="mt-1 text-sm text-muted">{q.customer_name} · {q.customer_email}</p><p className="mt-2 text-sm">{q.quantity} × {q.product_name} / {q.plan_name} · {q.unit_price} per {q.interval_count} {q.billing_interval}{q.interval_count > 1 ? "s" : ""}</p>{q.discount_code && <p className="mt-1 text-sm text-success">{q.discount_code} discount: {q.discount_amount}</p>}<p className="mt-1 text-xs text-muted">Valid through {q.valid_until}</p></div><div className="flex flex-wrap gap-2">{q.status === "draft" && <Button size="sm" variant="secondary" onClick={() => void changeStatus(q, "sent")}>Mark sent</Button>}{q.status === "sent" && <Button size="sm" variant="secondary" onClick={() => void changeStatus(q, "accepted")}>Accept</Button>}{q.status === "accepted" && <Button size="sm" onClick={() => void convert(q)}>Convert to subscription</Button>}{["draft", "sent", "accepted"].includes(q.status) && <Button size="sm" variant="danger" onClick={() => void changeStatus(q, "cancelled")}>Cancel</Button>}</div></div></Card>)}{quotes.length === 0 && <Card className="text-sm text-muted">No quotations created yet.</Card>}</div>
  </div>;
}
