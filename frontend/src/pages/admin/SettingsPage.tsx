import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Settings = { company_name: string; currency_code: string; invoice_prefix: string; payment_terms_days: number };

export function SettingsPage() {
  const [form, setForm] = useState<Settings>({ company_name: "Brightloop Software", currency_code: "INR", invoice_prefix: "INV", payment_terms_days: 14 });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  useEffect(() => { void api<Settings>("/settings").then(setForm).catch(err => setError(err instanceof ApiError ? err.message : "Unable to load settings")); }, []);
  async function save(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(""); setMessage("");
    try { setForm(await api<Settings>("/settings", { method: "PUT", body: JSON.stringify(form) })); setMessage("Company settings saved."); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to save settings"); }
    finally { setPending(false); }
  }
  return <div className="space-y-6"><div><h1 className="page-title">Settings</h1><p className="mt-1 text-sm text-muted">Company identity, invoice numbering, currency and payment terms.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}{message && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-success">{message}</p>}
    <Card><form onSubmit={save} className="grid gap-4 md:grid-cols-2">
      <div className="space-y-1.5"><Label htmlFor="company-name">Company name</Label><Input id="company-name" required maxLength={180} value={form.company_name} onChange={e => setForm({ ...form, company_name: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="currency-code">Currency code</Label><Input id="currency-code" required minLength={3} maxLength={3} value={form.currency_code} onChange={e => setForm({ ...form, currency_code: e.target.value.toUpperCase() })} /></div>
      <div className="space-y-1.5"><Label htmlFor="invoice-prefix">Invoice prefix</Label><Input id="invoice-prefix" required maxLength={12} value={form.invoice_prefix} onChange={e => setForm({ ...form, invoice_prefix: e.target.value.toUpperCase() })} /></div>
      <div className="space-y-1.5"><Label htmlFor="payment-terms">Payment terms (days)</Label><Input id="payment-terms" type="number" required min="1" max="90" value={form.payment_terms_days} onChange={e => setForm({ ...form, payment_terms_days: Number(e.target.value) })} /></div>
      <div className="md:col-span-2"><Button disabled={pending}>{pending ? "Saving..." : "Save settings"}</Button></div>
    </form></Card>
  </div>;
}
