import { useEffect, useState, type FormEvent } from "react";
import { Building2, CreditCard, Package, RefreshCw, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError, downloadFile, printFile } from "@/lib/api";

type Section = "overview" | "products" | "customers" | "quotations" | "discounts" | "subscriptions" | "requests" | "invoices" | "payments" | "credits" | "settings" | "staff";
type Overview = { customers: number; products: number; active_subscriptions: number; revenue_received: string; outstanding_balance: string; mrr: string; arr: string };
type Product = { id: number; name: string; sku: string; product_type: string; sales_price: string; is_active: boolean; plans: { id: number; name: string; price: string; billing_interval: string; interval_count: number; is_active: boolean }[]; variants: { id: number; attribute: string; name: string; price_extra: string; is_active: boolean }[] };
type Customer = { id: number; name: string; email: string; is_active: boolean; company_name: string | null; phone: string | null };
type Subscription = { id: number; number: string; customer_name: string; product_name: string; plan_name: string; status: string; next_billing_date: string; unit_price: string; billing_interval: string };
type Invoice = { id: number; number: string; customer_name: string; due_date: string; total_amount: string; amount_paid: string; credited_amount: string; balance_due: string; status: string; currency_code: string };
type Staff = { id: number; name: string; email: string; is_active: boolean };
type QuoteLine = { plan_id: number; quantity: number; description?: string; unit_price?: string };
type Quotation = { id: number; number: string; customer_name: string; customer_email: string; plan_name: string; quantity: number; unit_price: string; discount_amount: string; status: string; valid_until: string; line_items: QuoteLine[] };
type QuotationTemplate = { id: number; name: string; plan_id: number; plan_name: string; quantity: number; valid_days: number; notes: string | null; discount_code: string | null; line_items: { plan_id: number; quantity: number }[]; created_at: string };
type Payment = { id: number; number: string; invoice_number: string; customer_name: string; amount: string; refunded_amount: string; method: string; paid_at: string };
type CreditNote = { id: number; number: string; invoice_id: number; amount: string; reason: string; status: string; created_at: string };
type PaymentRefund = { id: number; number: string; payment_id: number; amount: string; reason: string; reference: string | null; refunded_at: string; created_at: string };
type WorkspaceSettings = { name: string; legal_name: string | null; email: string | null; phone: string | null; address: string | null; tax_id: string | null; currency_code: string; invoice_prefix: string; payment_terms_days: number; state_name: string | null; state_code: string | null; gst_rate_percent: string };
type ChangeRequest = { id: number; subscription_number: string; customer_name: string; customer_email: string; request_type: string; requested_plan_name: string | null; status: string; notes: string | null; created_at: string };
type Discount = { id: number; code: string; name: string; discount_type: "fixed" | "percentage"; value: string; minimum_amount: string; starts_at: string | null; ends_at: string | null; usage_limit: number | null; times_used: number; is_active: boolean };

const sectionTitles: Record<Section, string> = { overview: "Workspace overview", products: "Products and plans", customers: "Customers", quotations: "Quotations", discounts: "Discounts", subscriptions: "Subscriptions", requests: "Customer requests", invoices: "Invoices", payments: "Payments", credits: "Credit notes and refunds", settings: "Company settings", staff: "Staff" };

export function CompanyWorkspacePage({ section }: { section: Section }) {
  const { user } = useAuth();
  const isCompanyAdmin = user?.role === "company_admin";
  const [overview, setOverview] = useState<Overview | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [quotationTemplates, setQuotationTemplates] = useState<QuotationTemplate[]>([]);
  const [discounts, setDiscounts] = useState<Discount[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [creditNotes, setCreditNotes] = useState<CreditNote[]>([]);
  const [refunds, setRefunds] = useState<PaymentRefund[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [productForm, setProductForm] = useState({ name: "", sku: "", sales_price: "", product_type: "service" });
  const [planForm, setPlanForm] = useState({ name: "", price: "", billing_interval: "month" });
  const [variantForm, setVariantForm] = useState({ attribute: "", name: "", price_extra: "0.00" });
  const [staffForm, setStaffForm] = useState({ name: "", email: "", password: "" });
  const [quotationForm, setQuotationForm] = useState({ customer_id: "", plan_id: "", quantity: "1", valid_until: "", discount_code: "", notes: "", line_items: [] as { plan_id: string; quantity: string }[] });
  const [discountForm, setDiscountForm] = useState({ code: "", name: "", discount_type: "percentage" as "percentage" | "fixed", value: "", minimum_amount: "0", starts_at: "", ends_at: "", usage_limit: "" });
  const [customersForQuote, setCustomersForQuote] = useState<Customer[]>([]);
  const [productsForQuote, setProductsForQuote] = useState<Product[]>([]);

  async function load() {
    setError("");
    try {
      if (section === "overview") setOverview(await api<Overview>("/workspace/overview"));
      if (section === "products") setProducts(await api<Product[]>("/workspace/products?include_inactive=true"));
      if (section === "customers") setCustomers(await api<Customer[]>("/workspace/customers"));
      if (section === "quotations") {
        const [quotes, quoteCustomers, quoteProducts, companyDiscounts, templates] = await Promise.all([
          api<Quotation[]>("/workspace/quotations"), api<Customer[]>("/workspace/customers"), api<Product[]>("/workspace/products"), api<Discount[]>("/workspace/discounts"), api<QuotationTemplate[]>("/workspace/quotation-templates"),
        ]);
        setQuotations(quotes); setCustomersForQuote(quoteCustomers); setProductsForQuote(quoteProducts); setDiscounts(companyDiscounts); setQuotationTemplates(templates);
      }
      if (section === "discounts") setDiscounts(await api<Discount[]>("/workspace/discounts"));
      if (section === "subscriptions") setSubscriptions(await api<Subscription[]>("/workspace/subscriptions"));
      if (section === "requests") setChangeRequests(await api<ChangeRequest[]>("/workspace/requests"));
      if (section === "invoices") setInvoices(await api<Invoice[]>("/workspace/invoices"));
      if (section === "payments") setPayments(await api<Payment[]>("/workspace/payments"));
      if (section === "credits") {
        const [notes, refundRows] = await Promise.all([api<CreditNote[]>("/workspace/credit-notes"), api<PaymentRefund[]>("/workspace/refunds")]);
        setCreditNotes(notes); setRefunds(refundRows);
      }
      if (section === "settings") setSettings(await api<WorkspaceSettings>("/workspace/settings"));
      if (section === "staff" && isCompanyAdmin) setStaff(await api<Staff[]>("/workspace/staff"));
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to load workspace data"); }
  }
  useEffect(() => { void load(); }, [section, isCompanyAdmin]);

  async function createProduct(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      await api("/workspace/products", { method: "POST", body: JSON.stringify({ ...productForm, sales_price: productForm.sales_price, cost_price: "0.00" }) });
      setProductForm({ name: "", sku: "", sales_price: "", product_type: "service" }); setMessage("Product created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create product"); }
    finally { setSaving(false); }
  }

  async function createStaff(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      await api("/workspace/staff", { method: "POST", body: JSON.stringify(staffForm) });
      setStaffForm({ name: "", email: "", password: "" }); setMessage("Staff account created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create staff account"); }
    finally { setSaving(false); }
  }

  async function createPlan(productId: number, event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      await api(`/workspace/products/${productId}/plans`, { method: "POST", body: JSON.stringify({ ...planForm, interval_count: 1, features: [] }) });
      setPlanForm({ name: "", price: "", billing_interval: "month" }); setMessage("Subscription plan created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create plan"); }
    finally { setSaving(false); }
  }

  async function createVariant(productId: number, event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      await api(`/workspace/products/${productId}/variants`, { method: "POST", body: JSON.stringify(variantForm) });
      setVariantForm({ attribute: "", name: "", price_extra: "0.00" }); setMessage("Product variant created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create variant"); }
    finally { setSaving(false); }
  }

  async function createQuotation(event: FormEvent) {
    event.preventDefault(); setError(""); setMessage("");
    if (quotationForm.line_items.some(line => !line.plan_id)) { setError("Select a plan for each add-on line."); return; }
    setSaving(true);
    try {
      await api("/workspace/quotations", { method: "POST", body: JSON.stringify({ ...quotationForm, customer_id: Number(quotationForm.customer_id), plan_id: Number(quotationForm.plan_id), quantity: Number(quotationForm.quantity), line_items: quotationForm.line_items.filter(line => line.plan_id).map(line => ({ plan_id: Number(line.plan_id), quantity: Number(line.quantity) })), discount_code: quotationForm.discount_code || null }) });
      setQuotationForm({ ...quotationForm, customer_id: "", plan_id: "", quantity: "1", notes: "", line_items: [] }); setMessage("Quotation created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create quotation"); }
    finally { setSaving(false); }
  }

  async function saveQuotationTemplate() {
    if (!quotationForm.plan_id) { setError("Choose a plan before saving a quotation template."); return; }
    if (quotationForm.line_items.some(line => !line.plan_id)) { setError("Select a plan for each add-on line."); return; }
    const name = window.prompt("Name this quotation template");
    if (!name?.trim()) return;
    setError(""); setMessage("");
    try {
      await api("/workspace/quotation-templates", { method: "POST", body: JSON.stringify({
        name: name.trim(), plan_id: Number(quotationForm.plan_id), quantity: Number(quotationForm.quantity),
        valid_days: 14, notes: quotationForm.notes || null, discount_code: quotationForm.discount_code || null,
        line_items: quotationForm.line_items.filter(line => line.plan_id).map(line => ({ plan_id: Number(line.plan_id), quantity: Number(line.quantity) })),
      }) });
      setMessage("Quotation template saved for this company."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to save quotation template"); }
  }

  function applyQuotationTemplate(template: QuotationTemplate) {
    const expiry = new Date(); expiry.setDate(expiry.getDate() + template.valid_days);
    const localExpiry = `${expiry.getFullYear()}-${String(expiry.getMonth() + 1).padStart(2, "0")}-${String(expiry.getDate()).padStart(2, "0")}`;
    setQuotationForm({ ...quotationForm, plan_id: String(template.plan_id), quantity: String(template.quantity),
      valid_until: localExpiry, discount_code: template.discount_code || "", notes: template.notes || "",
      line_items: template.line_items.map(line => ({ plan_id: String(line.plan_id), quantity: String(line.quantity) })) });
  }

  async function editQuotation(quotation: Quotation) {
    const quantity = window.prompt("Quantity", String(quotation.quantity));
    if (quantity === null) return;
    const valid_until = window.prompt("Valid through (YYYY-MM-DD)", quotation.valid_until);
    if (valid_until === null) return;
    const notes = window.prompt("Quotation notes (leave blank to clear)");
    if (notes === null) return;
    setError(""); setMessage("");
    try {
      await api(`/workspace/quotations/${quotation.id}`, { method: "PATCH", body: JSON.stringify({
        quantity: Number(quantity), valid_until, notes: notes || null,
      }) });
      setMessage("Draft quotation updated."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to edit quotation"); }
  }

  async function deleteQuotationTemplate(template: QuotationTemplate) {
    if (!window.confirm(`Delete quotation template “${template.name}”?`)) return;
    try { await api(`/workspace/quotation-templates/${template.id}`, { method: "DELETE" }); setMessage("Quotation template deleted."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to delete quotation template"); }
  }

  async function createDiscount(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      await api("/workspace/discounts", { method: "POST", body: JSON.stringify({ ...discountForm, value: Number(discountForm.value), minimum_amount: Number(discountForm.minimum_amount), starts_at: discountForm.starts_at || null, ends_at: discountForm.ends_at || null, usage_limit: discountForm.usage_limit ? Number(discountForm.usage_limit) : null }) });
      setDiscountForm({ code: "", name: "", discount_type: "percentage", value: "", minimum_amount: "0", starts_at: "", ends_at: "", usage_limit: "" });
      setMessage("Discount created for this workspace."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create discount"); }
    finally { setSaving(false); }
  }

  async function toggleDiscount(discount: Discount) {
    setError(""); setMessage("");
    try { await api(`/workspace/discounts/${discount.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !discount.is_active }) }); setMessage("Discount updated."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update discount"); }
  }

  async function quoteAction(quotation: Quotation, action: "send" | "accept" | "convert") {
    setError(""); setMessage("");
    try {
      if (action === "convert") await api(`/workspace/quotations/${quotation.id}/convert`, { method: "POST" });
      else await api(`/workspace/quotations/${quotation.id}`, { method: "PATCH", body: JSON.stringify({ status: action === "send" ? "sent" : "accepted" }) });
      setMessage(action === "convert" ? "Subscription activated from quotation." : `Quotation ${action === "send" ? "sent" : "accepted"}.`); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update quotation"); }
  }

  async function runBilling() {
    setSaving(true); setError(""); setMessage("");
    try { const result = await api<{ invoices_created: number }>("/workspace/billing/run", { method: "POST", body: JSON.stringify({}) }); setMessage(`${result.invoices_created} invoice(s) generated.`); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to run billing"); }
    finally { setSaving(false); }
  }

  async function recordPayment(invoice: Invoice) {
    const amount = window.prompt(`Payment amount due: ${invoice.currency_code} ${invoice.balance_due}`);
    if (!amount) return;
    setError(""); setMessage("");
    try {
      await api(`/workspace/invoices/${invoice.id}/payments`, { method: "POST", body: JSON.stringify({ amount, method: "bank_transfer" }) });
      setMessage("Payment recorded."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to record payment"); }
  }

  async function emailInvoice(invoice: Invoice) {
    setError(""); setMessage("");
    try {
      const result = await api<{ delivered: boolean; recipient: string }>(`/workspace/invoices/${invoice.id}/email`, { method: "POST" });
      setMessage(`Invoice emailed to ${result.recipient}.`);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to email invoice"); }
  }

  async function issueCreditNote(invoice: Invoice) {
    const amount = window.prompt(`Credit amount available: ${invoice.currency_code} ${invoice.balance_due}`);
    if (!amount) return;
    const reason = window.prompt("Reason for this credit note");
    if (!reason) return;
    setError(""); setMessage("");
    try { await api(`/workspace/invoices/${invoice.id}/credit-notes`, { method: "POST", body: JSON.stringify({ amount, reason }) }); setMessage("Credit note issued and applied."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to issue credit note"); }
  }

  async function refundPayment(payment: Payment) {
    const available = Number(payment.amount) - Number(payment.refunded_amount);
    const amount = window.prompt(`Unrefunded payment: ${available.toFixed(2)}`);
    if (!amount) return;
    const reason = window.prompt("Reason for this refund");
    if (!reason) return;
    const reference = window.prompt("External refund reference (optional)") || null;
    setError(""); setMessage("");
    try { await api(`/workspace/payments/${payment.id}/refunds`, { method: "POST", body: JSON.stringify({ amount, reason, reference }) }); setMessage("Refund recorded. Invoice balance was recalculated."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to record refund"); }
  }

  async function voidCreditNote(note: CreditNote) {
    if (!window.confirm(`Void credit note ${note.number}? This will restore the invoice balance.`)) return;
    try { await api(`/workspace/credit-notes/${note.id}`, { method: "PATCH", body: JSON.stringify({ status: "void" }) }); setMessage("Credit note voided."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to void credit note"); }
  }

  async function saveSettings(event: FormEvent) {
    event.preventDefault(); if (!settings) return;
    setSaving(true); setError(""); setMessage("");
    try { setSettings(await api<WorkspaceSettings>("/workspace/settings", { method: "PUT", body: JSON.stringify(settings) })); setMessage("Company settings saved."); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to save company settings"); }
    finally { setSaving(false); }
  }

  async function decideRequest(request: ChangeRequest, status: "approved" | "rejected") {
    setError(""); setMessage("");
    try { await api(`/workspace/requests/${request.id}`, { method: "PATCH", body: JSON.stringify({ status }) }); setMessage(`Request ${status}.`); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update customer request"); }
  }

  const metrics: [string, string | number, typeof Users][] = overview ? [
    ["Customers", overview.customers, Users], ["Products", overview.products, Package],
    ["Active subscriptions", overview.active_subscriptions, RefreshCw], ["MRR", overview.mrr, CreditCard],
    ["ARR", overview.arr, CreditCard], ["Revenue received", overview.revenue_received, CreditCard],
    ["Outstanding", overview.outstanding_balance, Building2],
  ] : [];
  const selectedPrimaryPlan = productsForQuote.flatMap(product => product.plans).find(plan => String(plan.id) === quotationForm.plan_id);
  const compatibleQuotationPlans = productsForQuote.flatMap(product => product.plans.filter(plan => plan.is_active
    && selectedPrimaryPlan && plan.billing_interval === selectedPrimaryPlan.billing_interval
    && plan.interval_count === selectedPrimaryPlan.interval_count).map(plan => ({ ...plan, product_name: product.name })));
  const quotationTotal = (quotation: Quotation) => (quotation.line_items.reduce((total, line) =>
    total + Number(line.unit_price || 0) * line.quantity, 0) - Number(quotation.discount_amount || 0)).toFixed(2);

  return <div className="space-y-6">
    <header><p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Company workspace</p><h1 className="page-title mt-2">{sectionTitles[section]}</h1><p className="mt-1 text-sm text-muted">Company data is scoped to your workspace.</p></header>
    {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p>}
    {message && <p role="status" className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-success">{message}</p>}

    {section === "overview" && <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, Icon]) => <Card key={label}><div className="flex items-start justify-between"><div><CardDescription>{label}</CardDescription><CardTitle className="mt-3 text-2xl">{value}</CardTitle></div><div className="rounded-xl bg-sky p-2.5"><Icon className="h-4 w-4 text-primary" /></div></div></Card>)}</section>}

    {section === "products" && <>
      {isCompanyAdmin && <Card><CardTitle>Add product</CardTitle><form className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" onSubmit={createProduct}>
        <div className="space-y-1.5"><Label htmlFor="workspace-product-name">Name</Label><Input id="workspace-product-name" minLength={2} value={productForm.name} onChange={event => setProductForm({ ...productForm, name: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="workspace-product-sku">SKU</Label><Input id="workspace-product-sku" minLength={2} pattern="[A-Za-z0-9._-]+" value={productForm.sku} onChange={event => setProductForm({ ...productForm, sku: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="workspace-product-price">Sales price</Label><Input id="workspace-product-price" type="number" min="0" step="0.01" value={productForm.sales_price} onChange={event => setProductForm({ ...productForm, sales_price: event.target.value })} required /></div>
        <div className="flex items-end"><Button className="w-full" disabled={saving}>{saving ? "Saving…" : "Add product"}</Button></div>
      </form></Card>}
      <div className="grid gap-4 md:grid-cols-2">{products.map(product => <Card key={product.id}><div className="flex justify-between gap-4"><div><CardTitle>{product.name}</CardTitle><CardDescription className="mt-1">{product.sku} · {product.product_type}</CardDescription></div><span className="text-sm font-semibold">{product.sales_price}</span></div><div className="mt-4 border-t border-line pt-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted">Plans</p>{product.plans.map(plan => <p key={plan.id} className="mt-2 text-sm">{plan.name} <span className="text-muted">· {plan.price} / {plan.billing_interval}</span></p>)}{product.plans.length === 0 && <p className="mt-2 text-sm text-muted">No plans configured.</p>}</div><div className="mt-4 border-t border-line pt-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted">Variants</p>{product.variants.map(variant => <p key={variant.id} className="mt-2 text-sm">{variant.attribute}: {variant.name} <span className="text-muted">· +{variant.price_extra}</span></p>)}{product.variants.length === 0 && <p className="mt-2 text-sm text-muted">No variants configured.</p>}</div>{isCompanyAdmin && product.is_active && <><form className="mt-4 grid gap-3 border-t border-line pt-4 sm:grid-cols-3" onSubmit={event => void createPlan(product.id, event)}><div className="space-y-1"><Label htmlFor={`plan-name-${product.id}`}>Plan name</Label><Input id={`plan-name-${product.id}`} value={planForm.name} onChange={event => setPlanForm({ ...planForm, name: event.target.value })} required /></div><div className="space-y-1"><Label htmlFor={`plan-price-${product.id}`}>Price</Label><Input id={`plan-price-${product.id}`} type="number" min="0" step="0.01" value={planForm.price} onChange={event => setPlanForm({ ...planForm, price: event.target.value })} required /></div><div className="space-y-1"><Label htmlFor={`plan-period-${product.id}`}>Billing period</Label><select id={`plan-period-${product.id}`} className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm" value={planForm.billing_interval} onChange={event => setPlanForm({ ...planForm, billing_interval: event.target.value })}><option value="day">Daily</option><option value="week">Weekly</option><option value="month">Monthly</option><option value="year">Yearly</option></select></div><Button className="sm:col-span-3" disabled={saving}>{saving ? "Saving…" : "Add plan"}</Button></form><form className="mt-4 grid gap-3 border-t border-line pt-4 sm:grid-cols-3" onSubmit={event => void createVariant(product.id, event)}><div className="space-y-1"><Label htmlFor={`variant-attribute-${product.id}`}>Attribute</Label><Input id={`variant-attribute-${product.id}`} placeholder="Storage" value={variantForm.attribute} onChange={event => setVariantForm({ ...variantForm, attribute: event.target.value })} required /></div><div className="space-y-1"><Label htmlFor={`variant-name-${product.id}`}>Option</Label><Input id={`variant-name-${product.id}`} placeholder="1 TB" value={variantForm.name} onChange={event => setVariantForm({ ...variantForm, name: event.target.value })} required /></div><div className="space-y-1"><Label htmlFor={`variant-price-${product.id}`}>Additional price</Label><Input id={`variant-price-${product.id}`} type="number" min="0" step="0.01" value={variantForm.price_extra} onChange={event => setVariantForm({ ...variantForm, price_extra: event.target.value })} required /></div><Button className="sm:col-span-3" disabled={saving}>{saving ? "Saving…" : "Add variant"}</Button></form></>}<p className="mt-3 text-xs text-muted">{product.is_active ? "Available" : "Archived"}</p></Card>)}{products.length === 0 && <Card className="text-sm text-muted">No products in this workspace.</Card>}</div>
    </>}

    {section === "customers" && <DataTable headers={["Customer", "Email", "Business", "Phone", "Status"]} rows={customers.map(row => [row.name, row.email, row.company_name || "—", row.phone || "—", row.is_active ? "Active" : "Inactive"])} empty="No customers are assigned to this workspace." />}
    {section === "quotations" && <>
      <Card><CardTitle>Create quotation</CardTitle>{quotationTemplates.length > 0 && <div className="mt-3 flex flex-wrap items-center gap-3"><Label htmlFor="quote-template">Use template</Label><select id="quote-template" className="h-10 min-w-56 rounded-xl border border-line bg-white px-3 text-sm" defaultValue="" onChange={event => { const item = quotationTemplates.find(template => template.id === Number(event.target.value)); if (item) applyQuotationTemplate(item); event.target.value = ""; }}><option value="">Select a saved template</option>{quotationTemplates.map(item => <option key={item.id} value={item.id}>{item.name} · {item.plan_name}</option>)}</select></div>}<form className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-5" onSubmit={createQuotation}>
        <div className="space-y-1.5"><Label htmlFor="quote-customer">Customer</Label><select id="quote-customer" className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm" value={quotationForm.customer_id} onChange={event => setQuotationForm({ ...quotationForm, customer_id: event.target.value })} required><option value="">Select customer</option>{customersForQuote.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></div>
        <div className="space-y-1.5"><Label htmlFor="quote-plan">Plan</Label><select id="quote-plan" className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm" value={quotationForm.plan_id} onChange={event => setQuotationForm({ ...quotationForm, plan_id: event.target.value })} required><option value="">Select plan</option>{productsForQuote.flatMap(product => product.plans.filter(plan => plan.is_active).map(plan => <option key={plan.id} value={plan.id}>{product.name} · {plan.name}</option>))}</select></div>
        <div className="space-y-1.5"><Label htmlFor="quote-quantity">Quantity</Label><Input id="quote-quantity" type="number" min="1" max="10000" value={quotationForm.quantity} onChange={event => setQuotationForm({ ...quotationForm, quantity: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="quote-expiry">Valid through</Label><Input id="quote-expiry" type="date" min={new Date().toISOString().slice(0, 10)} value={quotationForm.valid_until} onChange={event => setQuotationForm({ ...quotationForm, valid_until: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="quote-discount">Discount code</Label><select id="quote-discount" className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm" value={quotationForm.discount_code} onChange={event => setQuotationForm({ ...quotationForm, discount_code: event.target.value })}><option value="">No discount</option>{discounts.filter(discount => discount.is_active && (!discount.starts_at || discount.starts_at <= new Date().toISOString().slice(0, 10)) && (!discount.ends_at || discount.ends_at >= new Date().toISOString().slice(0, 10)) && (discount.usage_limit === null || discount.times_used < discount.usage_limit)).map(discount => <option key={discount.id} value={discount.code}>{discount.code} · {discount.discount_type === "percentage" ? `${discount.value}%` : discount.value}</option>)}</select></div>
        <div className="space-y-1.5"><Label htmlFor="quote-notes">Notes</Label><Input id="quote-notes" maxLength={5000} value={quotationForm.notes} onChange={event => setQuotationForm({ ...quotationForm, notes: event.target.value })} /></div>
        <div className="space-y-2 sm:col-span-2 xl:col-span-5"><div className="flex items-center justify-between"><Label>Recurring add-on plans</Label><Button type="button" size="sm" variant="secondary" disabled={!selectedPrimaryPlan} onClick={() => setQuotationForm({ ...quotationForm, line_items: [...quotationForm.line_items, { plan_id: "", quantity: "1" }] })}>Add line</Button></div>{quotationForm.line_items.map((line, index) => <div key={index} className="grid gap-2 sm:grid-cols-[1fr_130px_auto]"><select aria-label={`Add-on plan ${index + 1}`} className="h-10 rounded-xl border border-line bg-white px-3 text-sm" value={line.plan_id} onChange={event => setQuotationForm({ ...quotationForm, line_items: quotationForm.line_items.map((item, row) => row === index ? { ...item, plan_id: event.target.value } : item) })}><option value="">Select add-on plan</option>{compatibleQuotationPlans.map(plan => <option key={plan.id} value={plan.id}>{plan.product_name} · {plan.name} · {plan.billing_interval}</option>)}</select><Input aria-label={`Add-on quantity ${index + 1}`} type="number" min="1" max="10000" value={line.quantity} onChange={event => setQuotationForm({ ...quotationForm, line_items: quotationForm.line_items.map((item, row) => row === index ? { ...item, quantity: event.target.value } : item) })} /><Button type="button" variant="secondary" onClick={() => setQuotationForm({ ...quotationForm, line_items: quotationForm.line_items.filter((_, row) => row !== index) })}>Remove</Button></div>)}</div>
        <div className="flex items-end gap-2"><Button className="flex-1" disabled={saving}>{saving ? "Saving…" : "Create quote"}</Button><Button type="button" variant="secondary" onClick={() => void saveQuotationTemplate()}>Save template</Button></div>
      </form></Card>
      {quotationTemplates.length > 0 && <Card><CardTitle>Saved quotation templates</CardTitle><div className="mt-3 space-y-2">{quotationTemplates.map(item => <div key={item.id} className="flex items-center justify-between border-t border-line pt-2 text-sm"><span>{item.name} · {item.plan_name} · quantity {item.quantity} · {item.line_items.length} add-on(s) · {item.valid_days} day validity</span><button className="text-danger hover:underline" onClick={() => void deleteQuotationTemplate(item)}>Delete</button></div>)}</div></Card>}
      <div className="grid gap-3">{quotations.map(row => <Card key={row.id}><div className="flex flex-wrap items-center justify-between gap-3"><div><CardTitle>{row.number}</CardTitle><CardDescription className="mt-1">{row.customer_name} · {row.plan_name}</CardDescription><ul className="mt-2 space-y-1 text-xs text-muted">{row.line_items.map((line, index) => <li key={`${line.plan_id}-${index}`}>{line.description || line.plan_name} · qty {line.quantity} × {line.unit_price}</li>)}</ul><p className="mt-2 text-sm font-semibold">Recurring total after discount: {quotationTotal(row)}</p><p className="mt-2 text-xs capitalize text-muted">{row.status} · valid through {row.valid_until}</p></div><div className="flex gap-2">{row.status === "draft" && <><Button size="sm" variant="secondary" onClick={() => void editQuotation(row)}>Edit draft</Button><Button size="sm" variant="secondary" onClick={() => void quoteAction(row, "send")}>Mark sent</Button></>}{row.status === "sent" && <Button size="sm" variant="secondary" onClick={() => void quoteAction(row, "accept")}>Accept</Button>}{row.status === "accepted" && <Button size="sm" onClick={() => void quoteAction(row, "convert")}>Activate subscription</Button>}</div></div></Card>)}{quotations.length === 0 && <Card className="text-sm text-muted">No quotations yet.</Card>}</div>
    </>}
    {section === "discounts" && <>
      {isCompanyAdmin && <Card><CardTitle>Create discount code</CardTitle><CardDescription className="mt-1">Codes are only valid for quotations and subscriptions in this company.</CardDescription><form className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" onSubmit={createDiscount}>
        <div className="space-y-1.5"><Label htmlFor="company-discount-code">Code</Label><Input id="company-discount-code" minLength={3} maxLength={40} pattern="[A-Za-z0-9_-]+" value={discountForm.code} onChange={event => setDiscountForm({ ...discountForm, code: event.target.value.toUpperCase() })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="company-discount-name">Name</Label><Input id="company-discount-name" minLength={2} maxLength={120} value={discountForm.name} onChange={event => setDiscountForm({ ...discountForm, name: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="company-discount-type">Discount type</Label><select id="company-discount-type" className="h-10 w-full rounded-xl border border-line bg-white px-3 text-sm" value={discountForm.discount_type} onChange={event => setDiscountForm({ ...discountForm, discount_type: event.target.value as "percentage" | "fixed" })}><option value="percentage">Percentage</option><option value="fixed">Fixed amount</option></select></div>
        <div className="space-y-1.5"><Label htmlFor="company-discount-value">Value</Label><Input id="company-discount-value" type="number" min="0.01" max={discountForm.discount_type === "percentage" ? 100 : undefined} step="0.01" value={discountForm.value} onChange={event => setDiscountForm({ ...discountForm, value: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="company-discount-minimum">Minimum subtotal</Label><Input id="company-discount-minimum" type="number" min="0" step="0.01" value={discountForm.minimum_amount} onChange={event => setDiscountForm({ ...discountForm, minimum_amount: event.target.value })} /></div>
        <div className="space-y-1.5"><Label htmlFor="company-discount-start">Start date</Label><Input id="company-discount-start" type="date" value={discountForm.starts_at} onChange={event => setDiscountForm({ ...discountForm, starts_at: event.target.value })} /></div>
        <div className="space-y-1.5"><Label htmlFor="company-discount-expiry">End date</Label><Input id="company-discount-expiry" type="date" value={discountForm.ends_at} onChange={event => setDiscountForm({ ...discountForm, ends_at: event.target.value })} /></div>
        <div className="space-y-1.5"><Label htmlFor="company-discount-limit">Usage limit</Label><Input id="company-discount-limit" type="number" min="1" step="1" value={discountForm.usage_limit} onChange={event => setDiscountForm({ ...discountForm, usage_limit: event.target.value })} /></div>
        <div className="flex items-end"><Button disabled={saving}>{saving ? "Saving…" : "Create discount"}</Button></div>
      </form></Card>}
      <div className="grid gap-3">{discounts.map(discount => <Card key={discount.id} className="flex flex-wrap items-center justify-between gap-3"><div><CardTitle>{discount.code} · {discount.name}</CardTitle><CardDescription className="mt-1">{discount.discount_type === "percentage" ? `${discount.value}%` : discount.value} discount · minimum {discount.minimum_amount} · used {discount.times_used}{discount.usage_limit ? ` / ${discount.usage_limit}` : ""}{discount.ends_at ? ` · through ${discount.ends_at}` : ""}</CardDescription><p className="mt-1 text-xs capitalize text-muted">{discount.is_active ? "Active" : "Inactive"}</p></div>{isCompanyAdmin && <Button size="sm" variant="secondary" onClick={() => void toggleDiscount(discount)}>{discount.is_active ? "Deactivate" : "Activate"}</Button>}</Card>)}{discounts.length === 0 && <Card className="text-sm text-muted">No discount codes in this workspace.</Card>}</div>
    </>}
    {section === "subscriptions" && <DataTable headers={["Subscription", "Customer", "Product / plan", "Renewal", "Status"]} rows={subscriptions.map(row => [row.number, row.customer_name, `${row.product_name} · ${row.plan_name}`, row.next_billing_date, row.status])} empty="No subscriptions in this workspace." />}
    {section === "requests" && <div className="grid gap-3">{changeRequests.map(row => <Card key={row.id}><div className="flex flex-wrap items-start justify-between gap-4"><div><CardTitle className="capitalize">{row.request_type} request · {row.subscription_number}</CardTitle><CardDescription className="mt-1">{row.customer_name} · {row.customer_email}{row.requested_plan_name ? ` · Plan: ${row.requested_plan_name}` : ""}</CardDescription>{row.notes && <p className="mt-2 text-sm text-ink">{row.notes}</p>}<p className="mt-2 text-xs capitalize text-muted">{row.status} · {new Date(row.created_at).toLocaleString()}</p></div>{row.status === "pending" && <div className="flex gap-2"><Button size="sm" onClick={() => void decideRequest(row, "approved")}>Approve</Button><Button size="sm" variant="secondary" onClick={() => void decideRequest(row, "rejected")}>Reject</Button></div>}</div></Card>)}{changeRequests.length === 0 && <Card className="text-sm text-muted">No customer requests in this workspace.</Card>}</div>}
    {section === "invoices" && <><div className="flex justify-end"><Button variant="secondary" disabled={saving} onClick={() => void runBilling()}>{saving ? "Processing…" : "Run due billing"}</Button></div><Card className="overflow-x-auto p-0"><table className="w-full min-w-[820px] text-left text-sm"><thead className="bg-canvas text-xs font-semibold uppercase text-muted"><tr>{["Invoice", "Customer", "Due date", "Total", "Balance", "Status", "Actions"].map(header => <th className="px-5 py-3" key={header}>{header}</th>)}</tr></thead><tbody>{invoices.length === 0 ? <tr><td colSpan={7} className="px-5 py-8 text-muted">No invoices in this workspace.</td></tr> : invoices.map(row => <tr key={row.id} className="border-t border-line"><td className="px-5 py-3">{row.number}</td><td className="px-5 py-3">{row.customer_name}</td><td className="px-5 py-3">{row.due_date}</td><td className="px-5 py-3">{row.currency_code} {row.total_amount}</td><td className="px-5 py-3">{row.currency_code} {row.balance_due}</td><td className="px-5 py-3 capitalize">{row.status}</td><td className="px-5 py-3"><div className="flex gap-3"><button className="text-primary hover:underline" onClick={() => void downloadFile(`/workspace/invoices/${row.id}/pdf`).catch(err => setError(err instanceof ApiError ? err.message : "Unable to download PDF"))}>PDF</button><button className="text-primary hover:underline" onClick={() => void printFile(`/workspace/invoices/${row.id}/pdf`).catch(err => setError(err instanceof ApiError ? err.message : "Unable to print PDF"))}>Print</button><button className="text-primary hover:underline" onClick={() => void emailInvoice(row)}>Email</button>{Number(row.balance_due) > 0 && <><button className="text-primary hover:underline" onClick={() => void recordPayment(row)}>Record payment</button><button className="text-primary hover:underline" onClick={() => void issueCreditNote(row)}>Credit note</button></>}</div></td></tr>)}</tbody></table></Card></>}
    {section === "payments" && <div className="grid gap-3">{payments.map(row => <Card key={row.id} className="flex flex-wrap items-center justify-between gap-3"><div><CardTitle>{row.number} · {row.invoice_number}</CardTitle><CardDescription className="mt-1">{row.customer_name} · {row.method} · {row.paid_at}</CardDescription><p className="mt-1 text-xs text-muted">Received {row.amount} · refunded {row.refunded_amount}</p></div>{Number(row.amount) > Number(row.refunded_amount) && <Button size="sm" variant="secondary" onClick={() => void refundPayment(row)}>Record refund</Button>}</Card>)}{payments.length === 0 && <Card className="text-sm text-muted">No payments recorded in this workspace.</Card>}</div>}
    {section === "credits" && <div className="grid gap-6 xl:grid-cols-2"><Card><CardTitle>Credit notes</CardTitle><div className="mt-4 space-y-3">{creditNotes.map(note => <div key={note.id} className="flex items-center justify-between gap-3 border-t border-line pt-3"><div><p className="text-sm font-semibold">{note.number}</p><p className="mt-1 text-xs text-muted">Invoice #{note.invoice_id} · {note.amount} · {note.reason}</p><p className="mt-1 text-xs capitalize text-muted">{note.status}</p></div>{isCompanyAdmin && note.status === "issued" && <Button size="sm" variant="secondary" onClick={() => void voidCreditNote(note)}>Void</Button>}</div>)}{creditNotes.length === 0 && <p className="border-t border-line pt-3 text-sm text-muted">No credit notes.</p>}</div></Card><Card><CardTitle>Refund history</CardTitle><div className="mt-4 space-y-3">{refunds.map(refund => <div key={refund.id} className="border-t border-line pt-3"><p className="text-sm font-semibold">{refund.number} · {refund.amount}</p><p className="mt-1 text-xs text-muted">Payment #{refund.payment_id} · {refund.refunded_at} · {refund.reason}{refund.reference ? ` · ${refund.reference}` : ""}</p></div>)}{refunds.length === 0 && <p className="border-t border-line pt-3 text-sm text-muted">No refunds recorded.</p>}</div></Card></div>}
    {section === "settings" && settings && <Card><CardTitle>Business and invoice details</CardTitle><CardDescription className="mt-1">These details are used for billing generated in this workspace.</CardDescription><form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={saveSettings}>
      <div className="space-y-1.5"><Label htmlFor="ws-name">Business name</Label><Input id="ws-name" minLength={2} value={settings.name} onChange={event => setSettings({ ...settings, name: event.target.value })} required /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-legal">Legal name</Label><Input id="ws-legal" value={settings.legal_name ?? ""} onChange={event => setSettings({ ...settings, legal_name: event.target.value || null })} /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-email">Business email</Label><Input id="ws-email" type="email" value={settings.email ?? ""} onChange={event => setSettings({ ...settings, email: event.target.value || null })} /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-phone">Business phone</Label><Input id="ws-phone" value={settings.phone ?? ""} onChange={event => setSettings({ ...settings, phone: event.target.value || null })} /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-tax-id">Tax ID / GSTIN</Label><Input id="ws-tax-id" value={settings.tax_id ?? ""} onChange={event => setSettings({ ...settings, tax_id: event.target.value || null })} /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-state-name">Registered state</Label><Input id="ws-state-name" maxLength={80} value={settings.state_name ?? ""} onChange={event => setSettings({ ...settings, state_name: event.target.value || null })} /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-state-code">Registered state code</Label><Input id="ws-state-code" maxLength={12} pattern="[A-Za-z0-9-]{2,12}" value={settings.state_code ?? ""} onChange={event => setSettings({ ...settings, state_code: event.target.value.toUpperCase() || null })} /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-gst-rate">Configured GST rate (%)</Label><Input id="ws-gst-rate" type="number" min="0" max="100" step="0.01" value={settings.gst_rate_percent} onChange={event => setSettings({ ...settings, gst_rate_percent: event.target.value })} required /><p className="text-xs text-muted">Set 0 to disable GST. A non-zero rate requires company GSTIN/state and customer billing state.</p></div>
      <div className="space-y-1.5"><Label htmlFor="ws-currency">Currency code</Label><Input id="ws-currency" minLength={3} maxLength={3} pattern="[A-Za-z]{3}" value={settings.currency_code} onChange={event => setSettings({ ...settings, currency_code: event.target.value.toUpperCase() })} required /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-prefix">Invoice prefix</Label><Input id="ws-prefix" minLength={2} maxLength={12} pattern="[A-Za-z0-9_-]+" value={settings.invoice_prefix} onChange={event => setSettings({ ...settings, invoice_prefix: event.target.value.toUpperCase() })} required /></div>
      <div className="space-y-1.5"><Label htmlFor="ws-terms">Payment terms (days)</Label><Input id="ws-terms" type="number" min="1" max="90" value={settings.payment_terms_days} onChange={event => setSettings({ ...settings, payment_terms_days: Number(event.target.value) })} required /></div>
      <div className="space-y-1.5 md:col-span-2"><Label htmlFor="ws-address">Registered business address</Label><textarea id="ws-address" maxLength={2000} rows={3} className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm" value={settings.address ?? ""} onChange={event => setSettings({ ...settings, address: event.target.value || null })} /></div>
      <div className="md:col-span-2"><Button disabled={saving}>{saving ? "Saving…" : "Save company settings"}</Button></div>
    </form></Card>}
    {section === "staff" && <>
      {isCompanyAdmin && <Card><CardTitle>Add staff member</CardTitle><form className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" onSubmit={createStaff}>
        <div className="space-y-1.5"><Label htmlFor="company-staff-name">Name</Label><Input id="company-staff-name" minLength={2} value={staffForm.name} onChange={event => setStaffForm({ ...staffForm, name: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="company-staff-email">Email</Label><Input id="company-staff-email" type="email" value={staffForm.email} onChange={event => setStaffForm({ ...staffForm, email: event.target.value })} required /></div>
        <div className="space-y-1.5"><Label htmlFor="company-staff-password">Temporary password</Label><Input id="company-staff-password" type="password" minLength={8} value={staffForm.password} onChange={event => setStaffForm({ ...staffForm, password: event.target.value })} required /></div>
        <div className="flex items-end"><Button className="w-full" disabled={saving}>{saving ? "Saving…" : "Add staff"}</Button></div>
      </form><p className="helper mt-3">Use at least 8 characters with a letter and a number.</p></Card>}
      <DataTable headers={["Name", "Email", "Status"]} rows={staff.map(row => [row.name, row.email, row.is_active ? "Active" : "Inactive"])} empty="No company staff have been added." />
    </>}
  </div>;
}

function DataTable({ headers, rows, empty }: { headers: string[]; rows: string[][]; empty: string }) {
  return <Card className="overflow-x-auto p-0"><table className="w-full min-w-[640px] text-left text-sm"><thead className="bg-canvas text-xs font-semibold uppercase text-muted"><tr>{headers.map(header => <th className="px-5 py-3" key={header}>{header}</th>)}</tr></thead><tbody>{rows.length === 0 ? <tr><td colSpan={headers.length} className="px-5 py-8 text-muted">{empty}</td></tr> : rows.map((row, index) => <tr key={index} className="border-t border-line">{row.map((value, cell) => <td key={cell} className="px-5 py-3">{value}</td>)}</tr>)}</tbody></table></Card>;
}
