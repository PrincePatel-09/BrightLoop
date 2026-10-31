import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Discount = { id: number; company_id: number; code: string; name: string; discount_type: string; value: string; minimum_amount: string; starts_at: string | null; ends_at: string | null; usage_limit: number | null; times_used: number; is_active: boolean };
type Company = { id: number; name: string; is_active: boolean };

export function PricingRulesPage() {
  const [discounts, setDiscounts] = useState<Discount[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [discountForm, setDiscountForm] = useState({ company_id: "", code: "", name: "", discount_type: "percentage", value: "", minimum_amount: "0", starts_at: "", ends_at: "", usage_limit: "" });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function load() {
    const [rows, companyRows] = await Promise.all([api<Discount[]>("/pricing/discounts"), api<Company[]>("/companies")]);
    setDiscounts(rows); setCompanies(companyRows);
  }
  useEffect(() => { void load().catch(err => setError(err instanceof ApiError ? err.message : "Unable to load pricing rules")); }, []);
  async function createDiscount(event: FormEvent) {
    event.preventDefault(); setError(""); setMessage("");
    try { await api("/pricing/discounts", { method: "POST", body: JSON.stringify({ ...discountForm, company_id: Number(discountForm.company_id), value: Number(discountForm.value), minimum_amount: Number(discountForm.minimum_amount), starts_at: discountForm.starts_at || null, ends_at: discountForm.ends_at || null, usage_limit: discountForm.usage_limit ? Number(discountForm.usage_limit) : null }) }); setDiscountForm({ company_id: "", code: "", name: "", discount_type: "percentage", value: "", minimum_amount: "0", starts_at: "", ends_at: "", usage_limit: "" }); setMessage("Company discount created."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create discount"); }
  }
  async function toggle(path: string, body: object) {
    setError(""); setMessage("");
    try { await api(path, { method: "PATCH", body: JSON.stringify(body) }); setMessage("Pricing rule updated."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update pricing rule"); }
  }
  return <div className="space-y-6">
    <div><h1 className="page-title">Platform pricing rules</h1><p className="mt-1 text-sm text-muted">Discount codes are captured on quotations. Each company configures its GST rate and registered state in its own workspace.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}{message && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-success">{message}</p>}
    <Card><h2 className="font-semibold">Company tax configuration</h2><p className="mt-2 text-sm text-muted">GST rates are tenant-specific and are configured by each Company Admin under Company → Settings. New invoices snapshot seller/customer GST details and split the configured rate into CGST/SGST for matching states or IGST for different states. Historical platform-wide tax rules are retained for reference and do not affect billing.</p></Card>
    <Card><h2 className="font-semibold">Company discount codes</h2><form onSubmit={createDiscount} className="mt-4 grid gap-4 md:grid-cols-3">
      <div className="space-y-1.5"><Label htmlFor="discount-company">Company workspace</Label><select id="discount-company" className="h-[42px] w-full rounded-xl border border-line bg-white px-3 text-sm" value={discountForm.company_id} onChange={e => setDiscountForm({ ...discountForm, company_id: e.target.value })} required><option value="">Choose company</option>{companies.filter(company => company.is_active).map(company => <option key={company.id} value={company.id}>{company.name}</option>)}</select></div>
      <div className="space-y-1.5"><Label htmlFor="discount-code">Code</Label><Input id="discount-code" required minLength={3} maxLength={40} value={discountForm.code} onChange={e => setDiscountForm({ ...discountForm, code: e.target.value.toUpperCase() })} /></div>
      <div className="space-y-1.5"><Label htmlFor="discount-name">Name</Label><Input id="discount-name" required maxLength={120} value={discountForm.name} onChange={e => setDiscountForm({ ...discountForm, name: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="discount-type">Type</Label><select id="discount-type" className="h-[42px] w-full rounded-xl border border-line bg-white px-3 text-sm" value={discountForm.discount_type} onChange={e => setDiscountForm({ ...discountForm, discount_type: e.target.value })}><option value="percentage">Percentage</option><option value="fixed">Fixed amount</option></select></div>
      <div className="space-y-1.5"><Label htmlFor="discount-value">Value</Label><Input id="discount-value" type="number" min="0.01" max={discountForm.discount_type === "percentage" ? "100" : undefined} step="0.01" required value={discountForm.value} onChange={e => setDiscountForm({ ...discountForm, value: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="discount-minimum">Minimum subtotal</Label><Input id="discount-minimum" type="number" min="0" step="0.01" value={discountForm.minimum_amount} onChange={e => setDiscountForm({ ...discountForm, minimum_amount: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="discount-start">Start date</Label><Input id="discount-start" type="date" value={discountForm.starts_at} onChange={e => setDiscountForm({ ...discountForm, starts_at: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="discount-expiry">End date</Label><Input id="discount-expiry" type="date" value={discountForm.ends_at} onChange={e => setDiscountForm({ ...discountForm, ends_at: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="discount-limit">Usage limit (optional)</Label><Input id="discount-limit" type="number" min="1" step="1" value={discountForm.usage_limit} onChange={e => setDiscountForm({ ...discountForm, usage_limit: e.target.value })} /></div>
      <div className="flex items-end"><Button>Create discount</Button></div>
    </form><div className="mt-4 divide-y divide-line">{discounts.map(discount => <div key={discount.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"><span><strong>{discount.code}</strong> · {companies.find(company => company.id === discount.company_id)?.name ?? `Company #${discount.company_id}`} · {discount.name} · {discount.discount_type === "percentage" ? `${discount.value}%` : discount.value} · Used {discount.times_used}{discount.usage_limit ? ` / ${discount.usage_limit}` : ""} · {discount.is_active ? "Active" : "Inactive"}</span><Button size="sm" variant="secondary" onClick={() => void toggle(`/pricing/discounts/${discount.id}`, { is_active: !discount.is_active })}>{discount.is_active ? "Deactivate" : "Reactivate"}</Button></div>)}{discounts.length === 0 && <p className="py-3 text-sm text-muted">No discount codes.</p>}</div></Card>
  </div>;
}
