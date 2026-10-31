import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Customer = { id: number; name: string; email: string; is_active: boolean; company_name: string | null; phone: string | null; billing_address: string | null; created_at: string };
type Contact = { company_name: string; phone: string; billing_address: string };
type History = { subscriptions: { number: string; plan: string; status: string; next_billing_date: string; unit_price: string; quantity: number }[]; invoices: { number: string; status: string; issued: string; total: string; balance: string }[]; payments: { number: string; amount: string; method: string; paid_at: string; reference: string | null }[] };

export function CustomersPage() {
  const [rows, setRows] = useState<Customer[]>([]);
  const [contacts, setContacts] = useState<Record<number, Contact>>({});
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<Record<number, History>>({});
  const [expanded, setExpanded] = useState<number | null>(null);

  async function load(term = search, start = offset) {
    setLoading(true); setError("");
    try {
      const data = await api<Customer[]>(`/customers?limit=25&offset=${start}&search=${encodeURIComponent(term)}`);
      setRows(data);
      setContacts(Object.fromEntries(data.map(row => [row.id, { company_name: row.company_name ?? "", phone: row.phone ?? "", billing_address: row.billing_address ?? "" }])));
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to load customers"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(""); }, []);

  async function save(customer: Customer) {
    setError(""); setMessage("");
    try {
      const contact = contacts[customer.id];
      await api(`/customers/${customer.id}`, { method: "PATCH", body: JSON.stringify({ company_name: contact.company_name || null, phone: contact.phone || null, billing_address: contact.billing_address || null }) });
      setMessage(`Contact details saved for ${customer.name}.`);
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to save customer"); }
  }

  async function toggleHistory(customerId: number) {
    if (expanded === customerId) { setExpanded(null); return; }
    setExpanded(customerId);
    if (history[customerId]) return;
    try { const data = await api<History>(`/customers/${customerId}/history`); setHistory({ ...history, [customerId]: data }); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to load customer history"); }
  }

  return <div className="space-y-6">
    <div><h1 className="page-title">Customers</h1><p className="mt-1 text-sm text-muted">Search registered customers and maintain their billing contact details.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
    {message && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-success">{message}</p>}
    <form className="flex gap-2" onSubmit={event => { event.preventDefault(); setOffset(0); void load(search, 0); }}><Input aria-label="Search customers" placeholder="Search name, email or company" value={search} onChange={event => setSearch(event.target.value)} /><Button variant="secondary">Search</Button></form>
    {loading ? <Card className="text-sm text-muted">Loading customers...</Card> : rows.length === 0 ? <Card className="text-sm text-muted">No customers found.</Card> : <div className="grid gap-4">{rows.map(customer => <Card key={customer.id}>
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold">{customer.name}</h2><p className="text-sm text-muted">{customer.email} · {customer.is_active ? "Active" : "Inactive"}</p></div><p className="text-xs text-muted">Joined {new Date(customer.created_at).toLocaleDateString()}</p></div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <div className="space-y-1.5"><Label htmlFor={`company-${customer.id}`}>Company</Label><Input id={`company-${customer.id}`} maxLength={180} value={contacts[customer.id]?.company_name ?? ""} onChange={event => setContacts({ ...contacts, [customer.id]: { ...contacts[customer.id], company_name: event.target.value } })} /></div>
        <div className="space-y-1.5"><Label htmlFor={`phone-${customer.id}`}>Phone</Label><Input id={`phone-${customer.id}`} maxLength={40} value={contacts[customer.id]?.phone ?? ""} onChange={event => setContacts({ ...contacts, [customer.id]: { ...contacts[customer.id], phone: event.target.value } })} /></div>
        <div className="space-y-1.5"><Label htmlFor={`address-${customer.id}`}>Billing address</Label><Input id={`address-${customer.id}`} maxLength={2000} value={contacts[customer.id]?.billing_address ?? ""} onChange={event => setContacts({ ...contacts, [customer.id]: { ...contacts[customer.id], billing_address: event.target.value } })} /></div>
      </div>
      <div className="mt-4 flex justify-between"><Button size="sm" variant="secondary" onClick={() => void toggleHistory(customer.id)}>{expanded === customer.id ? "Hide account history" : "View account history"}</Button><Button size="sm" onClick={() => void save(customer)}>Save contact</Button></div>
      {expanded === customer.id && <div className="mt-4 grid gap-4 border-t border-line pt-4 md:grid-cols-3"><HistoryList title="Subscriptions" rows={history[customer.id]?.subscriptions.map(row => `${row.number} · ${row.plan} · ${row.status} · next ${row.next_billing_date}`) ?? []} /><HistoryList title="Invoices" rows={history[customer.id]?.invoices.map(row => `${row.number} · ${row.status} · ${row.total} total · ${row.balance} due`) ?? []} /><HistoryList title="Payments" rows={history[customer.id]?.payments.map(row => `${row.number} · ${row.amount} · ${row.method} · ${row.paid_at}`) ?? []} /></div>}
    </Card>)}<div className="flex items-center justify-between"><Button variant="secondary" disabled={offset === 0} onClick={() => { const next = Math.max(0, offset - 25); setOffset(next); void load(search, next); }}>Previous</Button><span className="text-sm text-muted">Showing {offset + 1}–{offset + rows.length}</span><Button variant="secondary" disabled={rows.length < 25} onClick={() => { const next = offset + 25; setOffset(next); void load(search, next); }}>Next</Button></div></div>}
  </div>;
}

function HistoryList({ title, rows }: { title: string; rows: string[] }) {
  return <section><h3 className="text-sm font-semibold">{title}</h3>{rows.length ? <ul className="mt-2 space-y-2 text-xs text-muted">{rows.map((row, index) => <li key={`${title}-${index}`} className="rounded-lg bg-canvas p-2">{row}</li>)}</ul> : <p className="mt-2 text-xs text-muted">No records.</p>}</section>;
}
