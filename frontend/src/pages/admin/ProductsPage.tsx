import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Plan = { id: number; name: string; price: string; billing_interval: string; interval_count: number; is_active: boolean };
type Variant = { id: number; attribute: string; name: string; price_extra: string; is_active: boolean };
type Product = { id: number; name: string; sku: string; product_type: string; sales_price: string; cost_price: string; notes: string | null; is_active: boolean; plans: Plan[]; variants: Variant[] };

export function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [form, setForm] = useState({ name: "", sku: "", product_type: "service", sales_price: "", cost_price: "0", notes: "" });
  const [planForms, setPlanForms] = useState<Record<number, { name: string; price: string; billing_interval: string }>>({});
  const [editingProduct, setEditingProduct] = useState<number | null>(null);
  const [productEdits, setProductEdits] = useState<Record<number, { name: string; sales_price: string; cost_price: string; notes: string }>>({});
  const [planEdits, setPlanEdits] = useState<Record<number, { name: string; price: string; billing_interval: string; interval_count: string }>>({});
  const [variantForms, setVariantForms] = useState<Record<number, { attribute: string; name: string; price_extra: string }>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function load() { setProducts(await api<Product[]>("/catalog/products?include_inactive=true")); }
  useEffect(() => { void load().catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load products")); }, []);

  async function createProduct(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(""); setMessage("");
    try {
      await api("/catalog/products", { method: "POST", body: JSON.stringify({ ...form, sales_price: Number(form.sales_price), cost_price: Number(form.cost_price), notes: form.notes || null }) });
      setForm({ name: "", sku: "", product_type: "service", sales_price: "", cost_price: "0", notes: "" });
      setMessage("Product created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create product"); }
    finally { setPending(false); }
  }

  async function savePlan(productId: number) {
    const plan = planForms[productId]; if (!plan) return;
    setError(""); setMessage("");
    try {
      await api(`/catalog/products/${productId}/plans`, { method: "POST", body: JSON.stringify({ ...plan, price: Number(plan.price), interval_count: 1 }) });
      setPlanForms({ ...planForms, [productId]: { name: "", price: "", billing_interval: "month" } });
      setMessage("Plan created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create plan"); }
  }

  async function toggleProduct(product: Product) {
    try { await api(`/catalog/products/${product.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !product.is_active }) }); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update product"); }
  }

  function beginProductEdit(product: Product) {
    setEditingProduct(product.id);
    setProductEdits({ ...productEdits, [product.id]: { name: product.name, sales_price: product.sales_price, cost_price: product.cost_price, notes: product.notes ?? "" } });
  }

  async function saveProduct(productId: number) {
    const edit = productEdits[productId]; if (!edit) return;
    setError(""); setMessage("");
    try {
      await api(`/catalog/products/${productId}`, { method: "PATCH", body: JSON.stringify({ ...edit, sales_price: Number(edit.sales_price), cost_price: Number(edit.cost_price), notes: edit.notes || null }) });
      setEditingProduct(null); setMessage("Product updated."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update product"); }
  }

  function beginPlanEdit(plan: Plan) {
    setPlanEdits({ ...planEdits, [plan.id]: { name: plan.name, price: plan.price, billing_interval: plan.billing_interval, interval_count: String(plan.interval_count) } });
  }

  async function savePlanEdit(planId: number) {
    const edit = planEdits[planId]; if (!edit) return;
    setError(""); setMessage("");
    try {
      await api(`/catalog/plans/${planId}`, { method: "PATCH", body: JSON.stringify({ ...edit, price: Number(edit.price), interval_count: Number(edit.interval_count) }) });
      const next = { ...planEdits }; delete next[planId]; setPlanEdits(next); setMessage("Plan updated."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update plan"); }
  }

  async function togglePlan(plan: Plan) {
    try { await api(`/catalog/plans/${plan.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !plan.is_active }) }); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update plan"); }
  }

  async function saveVariant(productId: number) {
    const variant = variantForms[productId]; if (!variant) return;
    setError(""); setMessage("");
    try {
      await api(`/catalog/products/${productId}/variants`, { method: "POST", body: JSON.stringify({ ...variant, price_extra: Number(variant.price_extra || 0) }) });
      setVariantForms({ ...variantForms, [productId]: { attribute: "", name: "", price_extra: "0" } }); setMessage("Variant created."); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create variant"); }
  }

  async function toggleVariant(variant: Variant) {
    try { await api(`/catalog/variants/${variant.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !variant.is_active }) }); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Unable to update variant"); }
  }

  return <div className="space-y-6">
    <div><h1 className="page-title">Products and plans</h1><p className="mt-1 text-sm text-muted">Manage the catalogue used to build subscriptions.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
    {message && <p role="status" className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-success">{message}</p>}
    <Card><h2 className="font-semibold">Add product</h2><form onSubmit={createProduct} className="mt-4 grid gap-4 md:grid-cols-3">
      <div className="space-y-1.5"><Label htmlFor="product-name">Name</Label><Input id="product-name" required minLength={2} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="product-sku">SKU</Label><Input id="product-sku" required value={form.sku} onChange={e => setForm({ ...form, sku: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="product-type">Type</Label><select id="product-type" className="h-[42px] w-full rounded-xl border border-line bg-white px-3 text-sm" value={form.product_type} onChange={e => setForm({ ...form, product_type: e.target.value })}><option value="service">Service</option><option value="digital">Digital</option><option value="physical">Physical</option></select></div>
      <div className="space-y-1.5"><Label htmlFor="sales-price">Sales price</Label><Input id="sales-price" type="number" min="0" step="0.01" required value={form.sales_price} onChange={e => setForm({ ...form, sales_price: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="cost-price">Cost price</Label><Input id="cost-price" type="number" min="0" step="0.01" required value={form.cost_price} onChange={e => setForm({ ...form, cost_price: e.target.value })} /></div>
      <div className="space-y-1.5"><Label htmlFor="product-notes">Notes</Label><Input id="product-notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
      <div className="md:col-span-3"><Button disabled={pending}>{pending ? "Saving..." : "Create product"}</Button></div>
    </form></Card>
    <div className="space-y-4">{products.map(product => <Card key={product.id}>
      <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1"><h2 className="font-semibold">{product.name} <span className="text-xs font-normal text-muted">{product.sku}</span></h2><p className="mt-1 text-sm text-muted">{product.product_type} · Sales {product.sales_price} · Cost {product.cost_price} · {product.is_active ? "Active" : "Inactive"}</p>
      {editingProduct === product.id && <div className="mt-3 grid gap-2 md:grid-cols-4">{(["name", "sales_price", "cost_price", "notes"] as const).map(field => <Input key={field} aria-label={`Product ${field}`} placeholder={field.replace("_", " ")} type={field.endsWith("price") ? "number" : "text"} min={field.endsWith("price") ? "0" : undefined} step={field.endsWith("price") ? "0.01" : undefined} value={productEdits[product.id]?.[field] ?? ""} onChange={e => setProductEdits({ ...productEdits, [product.id]: { ...productEdits[product.id], [field]: e.target.value } })} />)}<Button size="sm" onClick={() => void saveProduct(product.id)}>Save product</Button><Button size="sm" variant="secondary" onClick={() => setEditingProduct(null)}>Cancel</Button></div>}</div><div className="flex gap-2"><Button variant="secondary" size="sm" onClick={() => beginProductEdit(product)}>Edit</Button><Button variant="secondary" size="sm" onClick={() => void toggleProduct(product)}>{product.is_active ? "Deactivate" : "Reactivate"}</Button></div></div>
      <div className="mt-4 border-t border-line pt-4"><h3 className="text-sm font-semibold">Plans</h3>{product.plans.length ? <ul className="mt-2 space-y-2 text-sm">{product.plans.map(plan => { const edit = planEdits[plan.id]; return <li key={plan.id} className="flex flex-wrap items-center gap-2">{edit ? <><Input aria-label="Plan name" value={edit.name} onChange={e => setPlanEdits({ ...planEdits, [plan.id]: { ...edit, name: e.target.value } })} /><Input aria-label="Plan price" type="number" min="0" step="0.01" value={edit.price} onChange={e => setPlanEdits({ ...planEdits, [plan.id]: { ...edit, price: e.target.value } })} /><select aria-label="Billing interval" className="h-10 rounded-xl border border-line bg-white px-3" value={edit.billing_interval} onChange={e => setPlanEdits({ ...planEdits, [plan.id]: { ...edit, billing_interval: e.target.value } })}>{["day", "week", "month", "year"].map(interval => <option key={interval}>{interval}</option>)}</select><Input aria-label="Interval count" type="number" min="1" max="120" value={edit.interval_count} onChange={e => setPlanEdits({ ...planEdits, [plan.id]: { ...edit, interval_count: e.target.value } })} /><Button size="sm" onClick={() => void savePlanEdit(plan.id)}>Save</Button><Button size="sm" variant="secondary" onClick={() => { const next = { ...planEdits }; delete next[plan.id]; setPlanEdits(next); }}>Cancel</Button></> : <><span>{plan.name} — {plan.price} / {plan.interval_count} {plan.billing_interval}{plan.interval_count > 1 ? "s" : ""} {plan.is_active ? "" : "(inactive)"}</span><Button variant="secondary" size="sm" onClick={() => beginPlanEdit(plan)}>Edit</Button><Button variant="secondary" size="sm" onClick={() => void togglePlan(plan)}>{plan.is_active ? "Deactivate" : "Reactivate"}</Button></>}</li>; })}</ul> : <p className="mt-2 text-sm text-muted">No plans yet.</p>}
        {product.is_active && <div className="mt-3 grid gap-2 md:grid-cols-[1fr_150px_150px_auto]">{(["name", "price", "billing_interval"] as const).map(field => <Input key={field} aria-label={`Plan ${field}`} placeholder={field === "billing_interval" ? "month" : field === "price" ? "Price" : "Plan name"} type={field === "price" ? "number" : "text"} min={field === "price" ? "0" : undefined} step={field === "price" ? "0.01" : undefined} value={planForms[product.id]?.[field] ?? (field === "billing_interval" ? "month" : "")} onChange={e => setPlanForms({ ...planForms, [product.id]: { name: "", price: "", billing_interval: "month", ...planForms[product.id], [field]: e.target.value } })} />)}<Button size="sm" onClick={() => void savePlan(product.id)} disabled={!planForms[product.id]?.name || !planForms[product.id]?.price}>Add plan</Button></div>}
      </div>
      <div className="mt-4 border-t border-line pt-4"><h3 className="text-sm font-semibold">Variants</h3>{product.variants.length ? <ul className="mt-2 space-y-2 text-sm">{product.variants.map(variant => <li key={variant.id} className="flex flex-wrap items-center gap-2"><span>{variant.attribute}: {variant.name} · +{variant.price_extra} {variant.is_active ? "" : "(inactive)"}</span><Button variant="secondary" size="sm" onClick={() => void toggleVariant(variant)}>{variant.is_active ? "Deactivate" : "Reactivate"}</Button></li>)}</ul> : <p className="mt-2 text-sm text-muted">No variants yet.</p>}{product.is_active && <div className="mt-3 grid gap-2 md:grid-cols-[1fr_1fr_160px_auto]">{(["attribute", "name", "price_extra"] as const).map(field => <Input key={field} aria-label={`Variant ${field}`} placeholder={field === "price_extra" ? "Additional price" : field} type={field === "price_extra" ? "number" : "text"} min={field === "price_extra" ? "0" : undefined} step={field === "price_extra" ? "0.01" : undefined} value={variantForms[product.id]?.[field] ?? (field === "price_extra" ? "0" : "")} onChange={e => setVariantForms({ ...variantForms, [product.id]: { attribute: "", name: "", price_extra: "0", ...variantForms[product.id], [field]: e.target.value } })} />)}<Button size="sm" onClick={() => void saveVariant(product.id)} disabled={!variantForms[product.id]?.attribute || !variantForms[product.id]?.name}>Add variant</Button></div>}</div>
    </Card>)}</div>
    {!products.length && <Card className="text-sm text-muted">No products have been created.</Card>}
  </div>;
}
