import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { ArrowUpRight, CalendarClock, CheckCircle2, CreditCard, FileText, Package, RefreshCw, WalletCards } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError, downloadFile } from "@/lib/api";

type Summary = { active_subscriptions: number; outstanding_balance: string; overdue_invoices: number; payments_recorded: number };
type Subscription = { id: number; number: string; product_name: string; plan_name: string; quantity: number; unit_price: string; billing_interval: string; interval_count: number; features?: string[]; status: string; start_date: string; next_billing_date: string; created_at?: string };
type Invoice = { id: number; number: string; subscription_id: number; period_start: string; period_end: string; due_date: string; total_amount: string; amount_paid: string; credited_amount: string; balance_due: string; status: string; product_name: string; plan_name: string; currency_code: string; created_at?: string };
type Payment = { id: number; number: string; invoice_number: string; amount: string; refunded_amount: string; method: string; paid_at: string; created_at?: string; reference: string | null };
type Profile = { name: string; email: string; company_name: string | null; phone: string | null; billing_address: string | null; gstin: string | null; state_code: string | null };
type Catalog = { company_name: string; company_slug: string; company_email: string | null; products: { id: number; name: string; sku: string; product_type: string; description: string | null; plans: { id: number; name: string; price: string; billing_interval: string; interval_count: number; features: string[] }[] }[] };
type CustomerQuotation = { id: number; number: string; plan_name: string; quantity: number; unit_price: string; status: string; valid_until: string; created_at: string };
type ChangeRequest = { id: number; subscription_id: number; subscription_number: string; request_type: string; requested_plan_name: string | null; status: string; notes: string | null; created_at: string };
type PaymentOrder = { order_id: string; amount: number; currency: string; key_id: string; company_name: string; customer_name: string; customer_email: string };
type RazorpayResult = { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string };
type RazorpayOptions = { key: string; amount: number; currency: string; name: string; description: string; order_id: string; prefill: { name: string; email: string }; handler: (result: RazorpayResult) => void; modal?: { ondismiss?: () => void } };
type RazorpayCheckout = { open: () => void; on: (event: string, handler: (event: { error?: { description?: string } }) => void) => void };

declare global { interface Window { Razorpay?: new (options: RazorpayOptions) => RazorpayCheckout } }

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

export function CustomerPortalPage({ section = "dashboard" }: { section?: "dashboard" | "subscriptions" | "invoices" | "payments" }) {
  const { user, refreshUser } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [quotations, setQuotations] = useState<CustomerQuotation[]>([]);
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([]);
  const [selectedPlans, setSelectedPlans] = useState<Record<number, string>>({});
  const [couponCode, setCouponCode] = useState("");
  const [purchasingPlanId, setPurchasingPlanId] = useState<number | null>(null);
  const [profileMessage, setProfileMessage] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [payingInvoiceId, setPayingInvoiceId] = useState<number | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    void Promise.all([
      api<Summary>("/my/summary"), api<Subscription[]>("/my/subscriptions"), api<Invoice[]>("/my/invoices"), api<Payment[]>("/my/payments"), api<Profile>("/my/profile"),
      api<Catalog>("/my/catalog"), api<CustomerQuotation[]>("/my/quotations"), api<ChangeRequest[]>("/my/requests"),
    ]).then(([s, subs, inv, pays, account, products, quotes, requests]) => { setSummary(s); setSubscriptions(subs); setInvoices(inv); setPayments(pays); setProfile(account); setCatalog(products); setQuotations(quotes); setChangeRequests(requests); })
      .catch(err => setError(err instanceof ApiError ? err.message : "Unable to load your account"));
  }, []);

  async function refreshRequests() {
    const [quotes, requests, subs] = await Promise.all([
      api<CustomerQuotation[]>("/my/quotations"), api<ChangeRequest[]>("/my/requests"), api<Subscription[]>("/my/subscriptions"),
    ]);
    setQuotations(quotes); setChangeRequests(requests); setSubscriptions(subs);
  }

  async function buyPlan(planId: number) {
    setError(""); setProfileMessage(""); setPurchasingPlanId(planId);
    try {
      const purchased = await api<Subscription>("/my/subscriptions", { method: "POST", body: JSON.stringify({ plan_id: planId, quantity: 1, ...(couponCode.trim() ? { discount_code: couponCode.trim().toUpperCase() } : {}) }) });
      setSubscriptions(current => [purchased, ...current.filter(item => item.id !== purchased.id)]);
      setCouponCode("");
      setProfileMessage(`${purchased.product_name} · ${purchased.plan_name} is active on your account (${purchased.number}).`);
      const [subsResult, summaryResult, invoicesResult] = await Promise.allSettled([api<Subscription[]>("/my/subscriptions"), api<Summary>("/my/summary"), api<Invoice[]>("/my/invoices")]);
      if (subsResult.status === "fulfilled") setSubscriptions(subsResult.value);
      if (summaryResult.status === "fulfilled") setSummary(summaryResult.value);
      if (invoicesResult.status === "fulfilled") setInvoices(invoicesResult.value);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to start this subscription"); }
    finally { setPurchasingPlanId(null); }
  }

  async function requestChange(subscription: Subscription, requestType: "pause" | "resume" | "cancel" | "upgrade" | "downgrade", planId?: number) {
    setError(""); setProfileMessage("");
    try {
      await api(`/my/subscriptions/${subscription.id}/requests`, { method: "POST", body: JSON.stringify({ request_type: requestType, ...(planId ? { requested_plan_id: planId } : {}) }) });
      setProfileMessage(`${requestType[0].toUpperCase()}${requestType.slice(1)} request sent to the company.`); await refreshRequests();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to send subscription request"); }
  }

  async function acceptQuotation(quotation: CustomerQuotation) {
    setError(""); setProfileMessage("");
    try {
      await api(`/my/quotations/${quotation.id}`, { method: "PATCH", body: JSON.stringify({ status: "accepted" }) });
      setProfileMessage("Quotation accepted. The company can now activate the subscription."); await refreshRequests();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to accept quotation"); }
  }

  function normalizedMonthly(price: number, interval: string, count: number) {
    if (interval === "year") return price / (12 * count);
    if (interval === "week") return price * 52 / (12 * count);
    if (interval === "day") return price * 365 / (12 * count);
    return price / count;
  }

  const activity = [
    ...subscriptions.map(item => ({ key: `subscription-${item.id}`, kind: "Subscription purchased", detail: `${item.product_name} · ${item.plan_name}`, number: item.number, date: item.created_at ?? item.start_date, amount: item.unit_price, state: item.status, currency: invoices.find(invoice => invoice.subscription_id === item.id)?.currency_code ?? "INR" })),
    ...invoices.map(item => ({ key: `invoice-${item.id}`, kind: "Invoice issued", detail: `${item.product_name} · ${item.plan_name}`, number: item.number, date: item.created_at ?? item.due_date, amount: item.total_amount, state: item.status, currency: item.currency_code })),
    ...payments.map(item => ({ key: `payment-${item.id}`, kind: "Payment received", detail: `Applied to ${item.invoice_number}`, number: item.number, date: item.created_at ?? item.paid_at, amount: item.amount, state: "paid", currency: invoices.find(invoice => invoice.number === item.invoice_number)?.currency_code ?? "INR" })),
  ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).slice(0, 8);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;
    setSavingProfile(true); setError(""); setProfileMessage("");
    try {
      const updated = await api<Profile>("/my/profile", { method: "PATCH", body: JSON.stringify(profile) });
      setProfile(updated); setProfileMessage("Your account details have been saved.");
      await refreshUser();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to save account details"); }
    finally { setSavingProfile(false); }
  }

  async function payInvoice(invoice: Invoice) {
    setError(""); setProfileMessage(""); setPayingInvoiceId(invoice.id);
    try {
      const order = await api<PaymentOrder>(`/my/invoices/${invoice.id}/payment-orders`, { method: "POST" });
      if (!window.Razorpay) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement("script");
          script.src = "https://checkout.razorpay.com/v1/checkout.js";
          script.onload = () => resolve(); script.onerror = () => reject(new Error("Unable to load secure checkout"));
          document.body.appendChild(script);
        });
      }
      if (!window.Razorpay) throw new Error("Secure checkout is unavailable");
      const checkout = new window.Razorpay({ key: order.key_id, amount: order.amount, currency: order.currency,
        name: order.company_name, description: `Invoice ${invoice.number}`, order_id: order.order_id,
        prefill: { name: order.customer_name, email: order.customer_email },
        handler: async result => {
          try {
            await api(`/my/invoices/${invoice.id}/verify-payment`, { method: "POST", body: JSON.stringify({
              order_id: result.razorpay_order_id, payment_id: result.razorpay_payment_id, signature: result.razorpay_signature,
            }) });
            const [nextInvoices, nextPayments, nextSummary] = await Promise.all([
              api<Invoice[]>("/my/invoices"), api<Payment[]>("/my/payments"), api<Summary>("/my/summary"),
            ]);
            setInvoices(nextInvoices); setPayments(nextPayments); setSummary(nextSummary);
            setProfileMessage("Payment received and applied to your invoice.");
          } catch (err) { setError(err instanceof ApiError ? err.message : "Payment verification failed. Contact the company before retrying."); }
          finally { setPayingInvoiceId(null); }
        }, modal: { ondismiss: () => setPayingInvoiceId(null) },
      });
      checkout.on("payment.failed", event => { setError(event.error?.description ?? "Payment failed. Please try again."); setPayingInvoiceId(null); });
      checkout.open();
    } catch (err) { setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Unable to start payment"); setPayingInvoiceId(null); }
  }
  return (
    <div className="mx-auto max-w-[1200px] space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Customer portal</p><h1 className="page-title mt-2">{section === "dashboard" ? `Good to see you, ${user?.name?.split(" ")[0]}.` : section === "subscriptions" ? "Your subscriptions" : section === "invoices" ? "Your invoices" : "Your payments"}</h1><p className="mt-2 text-sm text-muted">{section === "dashboard" ? "A simple view of your plan, billing status, and account history." : section === "subscriptions" ? "Review your plans and manage changes to your service." : section === "invoices" ? "Review balances, download invoices, and pay securely." : "A record of payments applied to your account."}</p></div>
        <div className="text-right text-xs text-muted"><p>Signed in as</p><p className="mt-1 font-semibold text-ink">{user?.email}</p></div>
        {section === "dashboard" && <Button asChild><Link to="/my/catalog">Browse and buy plans</Link></Button>}
      </div>
      {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p>}
      {profileMessage && <p role="status" className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-success">{profileMessage}</p>}

      {section === "dashboard" && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Active subscriptions" value={summary?.active_subscriptions ?? "-"} icon={RefreshCw} tone="bg-sky" />
        <SummaryCard label="Outstanding balance" value={summary?.outstanding_balance ?? "-"} icon={WalletCards} tone={summary?.outstanding_balance && summary.outstanding_balance !== "0.00" ? "bg-[#FFF4E5]" : "bg-mint"} />
        <SummaryCard label="Overdue invoices" value={summary?.overdue_invoices ?? "-"} icon={CalendarClock} tone={summary?.overdue_invoices ? "bg-[#FDEBEC]" : "bg-mint"} />
        <SummaryCard label="Payments recorded" value={summary?.payments_recorded ?? "-"} icon={CreditCard} tone="bg-sky" />
      </div>}

      {section === "dashboard" && <><div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <div className="flex items-start justify-between gap-4"><div><CardTitle>Subscription status</CardTitle><CardDescription className="mt-1">Your current recurring plans.</CardDescription></div><RefreshCw className="h-5 w-5 text-primary" /></div>
          <div className="mt-5 divide-y divide-line">
            {subscriptions.slice(0, 3).map(sub => <div key={sub.id} className="py-4 first:pt-0 last:pb-0"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold text-ink">{sub.product_name}</p><p className="mt-1 text-xs text-muted">{sub.plan_name} · {sub.number}</p></div><div className="text-right"><span className="inline-flex items-center gap-1 rounded-full bg-mint px-2.5 py-1 text-xs font-semibold capitalize text-success"><CheckCircle2 className="h-3.5 w-3.5" />{sub.status}</span><p className="mt-2 text-xs text-muted">Valid through {displayDate(sub.next_billing_date)}</p></div></div><div className="mt-4 grid gap-3 border-t border-line pt-4 text-xs sm:grid-cols-3"><div><p className="text-muted">Payment plan</p><p className="mt-1 font-semibold text-ink">{sub.unit_price} / {sub.interval_count} {sub.billing_interval}</p></div><div><p className="text-muted">Started</p><p className="mt-1 font-semibold text-ink">{displayDate(sub.start_date)}</p></div><div><p className="text-muted">Next renewal</p><p className="mt-1 font-semibold text-ink">{displayDate(sub.next_billing_date)}</p></div></div><div className="mt-4"><p className="text-xs font-semibold uppercase tracking-wide text-muted">Included features</p><div className="mt-2 flex flex-wrap gap-2">{sub.features?.length ? sub.features.map(feature => <span key={feature} className="rounded-full bg-sky px-2.5 py-1 text-xs text-ink">{feature}</span>) : <span className="text-xs text-muted">No feature list provided.</span>}</div></div></div>)}
            {subscriptions.length === 0 && <p className="py-3 text-sm text-muted">No subscriptions yet.</p>}
          </div>
        </Card>
        <Card className="bg-sidebar text-white">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/60">Billing attention</p>
          <h2 className="mt-3 text-lg font-semibold">{summary?.overdue_invoices ? "A payment needs your attention" : "Your account is up to date"}</h2>
          <p className="mt-2 text-sm leading-6 text-white/65">{summary?.overdue_invoices ? `${summary.overdue_invoices} invoice(s) are overdue. Review your invoice list for the balance and due date.` : "There are no overdue invoices on your account right now."}</p>
          <div className="mt-6 flex items-center gap-2 text-sm font-semibold text-white"><FileText className="h-4 w-4" /> {invoices.length} invoice(s) on file</div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <div className="flex items-start justify-between"><div><CardTitle>Available plans</CardTitle><CardDescription className="mt-1">Plans offered by {catalog?.company_name ?? "your company"}.</CardDescription></div><Package className="h-5 w-5 text-primary" /></div>
          <div className="mt-4 max-w-sm space-y-1.5"><Label htmlFor="coupon-code">Discount code (optional)</Label><Input id="coupon-code" maxLength={40} pattern="[A-Za-z0-9_-]+" value={couponCode} onChange={event => setCouponCode(event.target.value.toUpperCase())} placeholder="Enter company code" /></div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">{catalog?.products.flatMap(product => product.plans.map(plan => <div key={plan.id} className="rounded-xl border border-line p-4"><p className="text-xs text-muted">{product.name}</p><h3 className="mt-1 font-semibold">{plan.name}</h3><p className="mt-2 text-lg font-bold">{plan.price}<span className="text-xs font-normal text-muted"> / {plan.interval_count} {plan.billing_interval}</span></p><ul className="mt-3 space-y-1 text-xs text-muted">{plan.features.slice(0, 4).map(feature => <li key={feature}>{feature}</li>)}</ul><Button size="sm" className="mt-4 w-full" disabled={purchasingPlanId !== null} onClick={() => void buyPlan(plan.id)}>{purchasingPlanId === plan.id ? "Starting subscription…" : "Buy subscription"}</Button></div>))}{!catalog?.products.some(product => product.plans.length) && <p className="text-sm text-muted">No plans are available right now.</p>}</div>
          {catalog?.company_email && <p className="mt-4 text-xs text-muted">Need help? <a className="text-primary hover:underline" href={`mailto:${catalog.company_email}`}>Contact {catalog.company_name}</a></p>}
        </Card>
        <Card>
          <CardTitle>Quotations</CardTitle><CardDescription className="mt-1">Review your requests and accept quotations sent by the company.</CardDescription>
          <div className="mt-4 space-y-3">{quotations.map(quote => <div key={quote.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3"><div><p className="text-sm font-semibold">{quote.number} · {quote.plan_name}</p><p className="mt-1 text-xs capitalize text-muted">{quote.status} · valid through {displayDate(quote.valid_until)}</p></div>{quote.status === "sent" && <Button size="sm" variant="secondary" onClick={() => void acceptQuotation(quote)}>Accept quote</Button>}</div>)}{quotations.length === 0 && <p className="border-t border-line pt-3 text-sm text-muted">No quotations yet.</p>}</div>
        </Card>
      </div></>}

      {(section === "dashboard" || section === "subscriptions") && <Card>
        <CardTitle>Manage subscriptions</CardTitle><CardDescription className="mt-1">Send pause, resume, cancellation, or plan change requests to the company.</CardDescription>
        <div className="mt-4 space-y-4">{subscriptions.map(sub => {
          const pending = changeRequests.some(request => request.subscription_id === sub.id && request.status === "pending");
          const plans = catalog?.products.flatMap(product => product.plans.map(plan => ({ ...plan, product_name: product.name }))) ?? [];
          const selected = plans.find(plan => String(plan.id) === selectedPlans[sub.id]);
          const selectedType: "upgrade" | "downgrade" = selected && normalizedMonthly(Number(selected.price), selected.billing_interval, selected.interval_count) > normalizedMonthly(Number(sub.unit_price), sub.billing_interval, sub.interval_count) ? "upgrade" : "downgrade";
          return <div key={sub.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4"><div><p className="text-sm font-semibold">{sub.number} · {sub.plan_name}</p><p className="mt-1 text-xs capitalize text-muted">{sub.status}{pending ? " · Request pending" : ""}</p></div>{pending ? <span className="text-xs text-warning">Awaiting company review</span> : <div className="flex flex-wrap items-center gap-2">{sub.status === "active" && <><Button size="sm" variant="secondary" onClick={() => void requestChange(sub, "pause")}>Request pause</Button><Button size="sm" variant="secondary" onClick={() => void requestChange(sub, "cancel")}>Request cancellation</Button><select aria-label={`Choose plan for ${sub.number}`} className="h-10 rounded-xl border border-line bg-white px-2 text-xs" value={selectedPlans[sub.id] ?? ""} onChange={event => setSelectedPlans(current => ({ ...current, [sub.id]: event.target.value }))}><option value="">Change plan</option>{plans.filter(plan => plan.id !== sub.plan_id).map(plan => <option key={plan.id} value={plan.id}>{plan.product_name} · {plan.name} ({plan.price}/{plan.billing_interval})</option>)}</select>{selected && <Button size="sm" onClick={() => void requestChange(sub, selectedType, selected.id)}>Request {selectedType}</Button>}</>}{sub.status === "paused" && <Button size="sm" variant="secondary" onClick={() => void requestChange(sub, "resume")}>Request resume</Button>}</div>}</div>;
        })}{subscriptions.length === 0 && <p className="border-t border-line pt-4 text-sm text-muted">Your active subscriptions will appear here.</p>}</div>
        <div className="mt-5 border-t border-line pt-4"><h3 className="text-sm font-semibold">Request history</h3><div className="mt-3 space-y-2">{changeRequests.slice(0, 6).map(request => <div key={request.id} className="rounded-lg bg-canvas px-3 py-2 text-sm"><span className="capitalize">{request.request_type}</span> · {request.subscription_number}{request.requested_plan_name ? ` · ${request.requested_plan_name}` : ""}<span className="ml-2 text-xs capitalize text-muted">{request.status}</span></div>)}{changeRequests.length === 0 && <p className="text-sm text-muted">No subscription requests.</p>}</div></div>
      </Card>}

      {(section === "dashboard" || section === "invoices") && <ActivityTable title={section === "dashboard" ? "Recent invoices" : "Invoices"} description="Your billing documents and outstanding balances." icon={FileText}>
          {invoices.map(invoice => <div key={invoice.id} className="grid grid-cols-[1fr_auto] items-center gap-3 border-t border-line py-3 first:border-t-0"><div><p className="text-sm font-semibold text-ink">{invoice.number}</p><p className="mt-1 text-xs text-muted">Due {displayDate(invoice.due_date)} · {invoice.product_name}</p></div><div className="text-right"><p className="text-sm font-semibold">{invoice.currency_code} {invoice.balance_due}</p><div className="mt-1 flex items-center justify-end gap-3"><button type="button" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline" onClick={() => void downloadFile(`/my/invoices/${invoice.id}/pdf`).catch(err => setError(err instanceof ApiError ? err.message : "Unable to download invoice"))}>PDF <ArrowUpRight className="h-3 w-3" /></button>{Number(invoice.balance_due) > 0 && invoice.status !== "cancelled" && <button type="button" disabled={payingInvoiceId !== null} className="text-xs font-semibold text-primary hover:underline disabled:opacity-50" onClick={() => void payInvoice(invoice)}>{payingInvoiceId === invoice.id ? "Opening…" : "Pay online"}</button>}</div></div></div>)}
          {invoices.length === 0 && <p className="border-t border-line py-3 text-sm text-muted">No invoices yet.</p>}
        </ActivityTable>}
      {(section === "dashboard" || section === "payments") && <ActivityTable title={section === "dashboard" ? "Recent payments" : "Payments"} description="Payments applied to your account." icon={CreditCard}>
          {payments.map(payment => <div key={payment.id} className="flex items-center justify-between gap-3 border-t border-line py-3 first:border-t-0"><div><p className="text-sm font-semibold text-ink">{payment.number}</p><p className="mt-1 text-xs text-muted">{payment.invoice_number} · {displayDate(payment.paid_at)}{Number(payment.refunded_amount) > 0 ? ` · refunded ${payment.refunded_amount}` : ""}</p></div><p className="text-sm font-semibold text-success">{payment.amount}</p></div>)}
          {payments.length === 0 && <p className="border-t border-line py-3 text-sm text-muted">No payments recorded yet.</p>}
        </ActivityTable>}
      {section === "dashboard" && <ActivityTable title="All transactions" description="Purchases, invoices, and payments in one account history." icon={CreditCard}>
        {activity.map(item => <div key={item.key} className="grid grid-cols-[1fr_auto] items-center gap-3 border-t border-line py-3 first:border-t-0"><div><p className="text-sm font-semibold text-ink">{item.kind} · {item.number}</p><p className="mt-1 text-xs text-muted">{item.detail} · {displayDate(item.date.slice(0, 10))} · <span className="capitalize">{item.state}</span></p></div><p className="text-sm font-semibold text-ink">{item.currency} {item.amount}</p></div>)}
        {activity.length === 0 && <div className="border-t border-line pt-3 text-sm text-muted">No transactions yet. <Link className="font-semibold text-primary hover:underline" to="/my/catalog">Browse available plans</Link> to get started.</div>}
      </ActivityTable>}
      {section === "dashboard" && <Card><div><CardTitle>Account and billing details</CardTitle><CardDescription className="mt-1">Keep your contact and invoice information up to date.</CardDescription></div>
        {profile && <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={saveProfile}>
          <div className="space-y-1.5"><Label htmlFor="profile-name">Full name</Label><Input id="profile-name" required minLength={2} maxLength={120} value={profile.name} onChange={event => setProfile({ ...profile, name: event.target.value })} /></div>
          <div className="space-y-1.5"><Label htmlFor="profile-email">Email</Label><Input id="profile-email" type="email" value={profile.email} disabled /></div>
          <div className="space-y-1.5"><Label htmlFor="profile-company">Company name</Label><Input id="profile-company" maxLength={180} value={profile.company_name ?? ""} onChange={event => setProfile({ ...profile, company_name: event.target.value || null })} /></div>
          <div className="space-y-1.5"><Label htmlFor="profile-phone">Phone</Label><Input id="profile-phone" type="tel" maxLength={40} value={profile.phone ?? ""} onChange={event => setProfile({ ...profile, phone: event.target.value || null })} /></div>
          <div className="space-y-1.5"><Label htmlFor="profile-gstin">GSTIN (optional)</Label><Input id="profile-gstin" maxLength={20} value={profile.gstin ?? ""} onChange={event => setProfile({ ...profile, gstin: event.target.value.toUpperCase() || null })} /></div>
          <div className="space-y-1.5"><Label htmlFor="profile-state-code">Billing state code</Label><Input id="profile-state-code" maxLength={12} pattern="[A-Za-z0-9-]{2,12}" value={profile.state_code ?? ""} onChange={event => setProfile({ ...profile, state_code: event.target.value.toUpperCase() || null })} /></div>
          <div className="space-y-1.5 md:col-span-2"><Label htmlFor="profile-address">Billing address</Label><textarea id="profile-address" maxLength={2000} rows={3} className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" value={profile.billing_address ?? ""} onChange={event => setProfile({ ...profile, billing_address: event.target.value || null })} /></div>
          <div className="md:col-span-2"><Button type="submit" disabled={savingProfile}>{savingProfile ? "Saving…" : "Save account details"}</Button></div>
        </form>}
      </Card>}
    </div>
  );
}

function SummaryCard({ label, value, icon: Icon, tone }: { label: string; value: string | number; icon: typeof RefreshCw; tone: string }) {
  return <Card className="transition hover:-translate-y-0.5 hover:shadow-lift"><div className="flex items-start justify-between gap-3"><div><CardDescription>{label}</CardDescription><CardTitle className="mt-3 text-2xl">{value}</CardTitle></div><div className={`rounded-xl p-2.5 ${tone}`}><Icon className="h-4 w-4 text-primary" /></div></div></Card>;
}

function ActivityTable({ title, description, icon: Icon, children }: { title: string; description: string; icon: typeof FileText; children: ReactNode }) {
  return <Card><div className="flex items-start justify-between gap-3"><div><CardTitle>{title}</CardTitle><CardDescription className="mt-1">{description}</CardDescription></div><Icon className="h-5 w-5 text-primary" /></div><div className="mt-4">{children}</div></Card>;
}
