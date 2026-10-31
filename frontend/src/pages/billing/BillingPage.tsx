import { useEffect, useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError, downloadFile } from "@/lib/api";

type Invoice = { id: number; number: string; customer_name: string; customer_email: string; product_name: string; plan_name: string; company_name: string; currency_code: string; quantity: number; period_start: string; period_end: string; due_date: string; subtotal: string; tax_amount: string; discount_amount: string; total_amount: string; amount_paid: string; balance_due: string; status: string };
type Payment = { id: number; number: string; invoice_id: number; invoice_number: string; customer_name: string; amount: string; method: string; reference: string | null; paid_at: string };

export function BillingPage() {
  const paymentsView = useLocation().pathname.endsWith("/payments");
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [selectedInvoice, setSelectedInvoice] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("bank_transfer");
  const [reference, setReference] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function load() {
    const [invoiceRows, paymentRows] = await Promise.all([
      api<Invoice[]>("/billing/invoices"), api<Payment[]>("/billing/payments"),
    ]);
    setInvoices(invoiceRows); setPayments(paymentRows);
    const open = invoiceRows.find(row => Number(row.balance_due) > 0 && row.status !== "cancelled");
    if (!selectedInvoice && open) setSelectedInvoice(String(open.id));
  }
  useEffect(() => { void load().catch(err => setError(err instanceof ApiError ? err.message : "Unable to load billing records")); }, []);

  async function runBilling() {
    setPending(true); setError(""); setMessage("");
    try {
      const result = await api<{ invoices_created: number; periods_processed: number }>("/billing/run", { method: "POST", body: JSON.stringify({ as_of: new Date().toISOString().slice(0, 10) }) });
      setMessage(`Billing processed ${result.periods_processed} periods and created ${result.invoices_created} invoices.`); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Billing run failed"); }
    finally { setPending(false); }
  }

  async function recordPayment(event: FormEvent) {
    event.preventDefault(); if (!selectedInvoice) return;
    setPending(true); setError(""); setMessage("");
    try {
      await api(`/billing/invoices/${selectedInvoice}/payments`, { method: "POST", body: JSON.stringify({ amount: Number(amount), method, reference: reference || null }) });
      setMessage("Payment recorded and invoice balance updated."); setAmount(""); setReference(""); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to record payment"); }
    finally { setPending(false); }
  }

  return <div className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="page-title">{paymentsView ? "Payments" : "Invoices"}</h1><p className="mt-1 text-sm text-muted">{paymentsView ? "Record manual or partial payments and review payment history." : "Run recurring billing and review invoice balances."}</p></div>{!paymentsView && <Button disabled={pending} onClick={() => void runBilling()}>{pending ? "Processing..." : "Run billing now"}</Button>}</div>
    {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}{message && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-success">{message}</p>}
    {paymentsView && <Card><h2 className="font-semibold">Record a payment</h2><form className="mt-4 grid gap-4 md:grid-cols-4" onSubmit={recordPayment}>
      <div className="space-y-1.5 md:col-span-2"><Label htmlFor="payment-invoice">Invoice</Label><select id="payment-invoice" required className="h-[42px] w-full rounded-xl border border-line bg-white px-3 text-sm" value={selectedInvoice} onChange={e => setSelectedInvoice(e.target.value)}><option value="">Select an open invoice</option>{invoices.filter(i => Number(i.balance_due) > 0 && i.status !== "cancelled").map(i => <option key={i.id} value={i.id}>{i.number} · {i.customer_name} · Balance {i.balance_due}</option>)}</select></div>
      <div className="space-y-1.5"><Label htmlFor="payment-amount">Amount</Label><Input id="payment-amount" type="number" min="0.01" step="0.01" required value={amount} onChange={e => setAmount(e.target.value)} /></div>
      <div className="space-y-1.5"><Label htmlFor="payment-method">Method</Label><select id="payment-method" className="h-[42px] w-full rounded-xl border border-line bg-white px-3 text-sm" value={method} onChange={e => setMethod(e.target.value)}><option value="bank_transfer">Bank transfer</option><option value="cash">Cash</option><option value="card">Card</option><option value="other">Other</option></select></div>
      <div className="space-y-1.5 md:col-span-3"><Label htmlFor="payment-reference">Reference</Label><Input id="payment-reference" maxLength={120} value={reference} onChange={e => setReference(e.target.value)} /></div>
      <div className="flex items-end"><Button disabled={pending || !selectedInvoice}>{pending ? "Saving..." : "Record payment"}</Button></div>
    </form></Card>}
    {!paymentsView ? <div className="grid gap-4">{invoices.map(invoice => <Card key={invoice.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="font-semibold">{invoice.number} <span className="ml-2 rounded-full bg-canvas px-2 py-1 text-xs capitalize">{invoice.status.replace("_", " ")}</span></h2><p className="mt-1 text-sm text-muted">{invoice.customer_name} · {invoice.customer_email}</p><p className="mt-2 text-sm">{invoice.quantity} × {invoice.product_name} / {invoice.plan_name} · Period {invoice.period_start} to {invoice.period_end}</p><p className="mt-1 text-xs text-muted">Due {invoice.due_date} · Subtotal {invoice.currency_code} {invoice.subtotal} · Tax {invoice.currency_code} {invoice.tax_amount} · Discount {invoice.currency_code} {invoice.discount_amount}</p></div><div className="text-right text-sm"><p>Total <strong>{invoice.currency_code} {invoice.total_amount}</strong></p><p>Paid {invoice.currency_code} {invoice.amount_paid}</p><p>Balance <strong>{invoice.currency_code} {invoice.balance_due}</strong></p><Button className="mt-2" size="sm" variant="secondary" onClick={() => void downloadFile(`/billing/invoices/${invoice.id}/pdf`).catch(err => setError(err instanceof ApiError ? err.message : "Unable to download invoice"))}>Download PDF</Button></div></div></Card>)}{invoices.length === 0 && <Card className="text-sm text-muted">No invoices yet. Convert a quotation to a subscription, then run billing.</Card>}</div>
      : <div className="grid gap-4">{payments.map(payment => <Card key={payment.id} className="flex flex-wrap justify-between gap-3"><div><h2 className="font-semibold">{payment.number} · {payment.customer_name}</h2><p className="mt-1 text-sm text-muted">{payment.invoice_number} · {payment.method.replace("_", " ")} · {payment.paid_at}</p>{payment.reference && <p className="mt-1 text-xs text-muted">Reference: {payment.reference}</p>}</div><strong>{payment.amount}</strong></Card>)}{payments.length === 0 && <Card className="text-sm text-muted">No payments recorded yet.</Card>}</div>}
  </div>;
}
