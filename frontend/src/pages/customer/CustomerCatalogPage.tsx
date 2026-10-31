import { useEffect, useState } from "react";
import { ArrowRight, Check, Package, ShoppingBag } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Catalog = {
  company_name: string;
  company_slug: string;
  company_email: string | null;
  products: {
    id: number;
    name: string;
    sku: string;
    product_type: string;
    description: string | null;
    plans: { id: number; name: string; price: string; billing_interval: string; interval_count: number; features: string[] }[];
  }[];
};

type PurchasedSubscription = { number: string; product_name: string; plan_name: string; status: string };
type SubscriptionRequest = { number: string; status: string };

export function CustomerCatalogPage() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [couponCode, setCouponCode] = useState("");
  const [purchasingPlanId, setPurchasingPlanId] = useState<number | null>(null);
  const [requestingPlanId, setRequestingPlanId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    void api<Catalog>("/my/catalog")
      .then(setCatalog)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load services"))
      .finally(() => setLoading(false));
  }, []);

  async function buyPlan(planId: number) {
    setError("");
    setMessage("");
    setPurchasingPlanId(planId);
    try {
      const purchased = await api<PurchasedSubscription>("/my/subscriptions", {
        method: "POST",
        body: JSON.stringify({
          plan_id: planId,
          quantity: 1,
          ...(couponCode.trim() ? { discount_code: couponCode.trim().toUpperCase() } : {}),
        }),
      });
      setMessage(`${purchased.product_name} · ${purchased.plan_name} is active on your account (${purchased.number}). You can view it under My subscriptions.`);
      setCouponCode("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to start this subscription");
    } finally {
      setPurchasingPlanId(null);
    }
  }

  async function requestPlan(planId: number) {
    setError("");
    setMessage("");
    setRequestingPlanId(planId);
    try {
      const request = await api<SubscriptionRequest>("/my/subscription-requests", {
        method: "POST",
        body: JSON.stringify({ plan_id: planId, quantity: 1, ...(couponCode.trim() ? { discount_code: couponCode.trim().toUpperCase() } : {}) }),
      });
      setCouponCode("");
      setMessage(`Request ${request.number} was sent to your company for review. Track it in your dashboard quotations.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to request this subscription");
    } finally {
      setRequestingPlanId(null);
    }
  }
  const planCount = catalog?.products.reduce((total, product) => total + product.plans.length, 0) ?? 0;

  return (
    <div className="mx-auto max-w-[1200px] space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Customer services</p>
          <h1 className="page-title mt-2">Choose a subscription</h1>
          <p className="mt-2 text-sm text-muted">Buy a plan now or send a request for your company to review first.</p>
        </div>
        <Button asChild variant="secondary"><Link to="/my/subscriptions">My subscriptions <ArrowRight className="h-4 w-4" /></Link></Button>
      </div>

      {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p>}
      {message && <p role="status" className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-success">{message}</p>}

      <Card className="flex flex-wrap items-center gap-4 bg-sidebar text-white">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10"><ShoppingBag className="h-6 w-6" /></div>
        <div className="min-w-[180px] flex-1">
          <p className="text-sm font-semibold">Start a plan when you’re ready</p>
          <p className="mt-1 text-sm text-white/70">Buy now to activate immediately, or request approval from your company.</p>
        </div>
        <div className="w-full max-w-xs space-y-1.5 sm:w-auto">
          <Label htmlFor="shop-discount" className="text-white/80">Discount code (optional)</Label>
          <Input id="shop-discount" maxLength={40} pattern="[A-Za-z0-9_-]+" value={couponCode} onChange={(event) => setCouponCode(event.target.value.toUpperCase())} placeholder="Enter company code" />
        </div>
      </Card>

      {loading && <Card className="text-sm text-muted">Loading available services…</Card>}
      {!loading && catalog && planCount === 0 && <Card className="text-sm text-muted">There are no subscription plans available right now. Check again later or contact {catalog.company_name}.</Card>}

      {!loading && catalog?.products.filter((product) => product.plans.length > 0).map((product) => (
        <Card key={product.id}>
          <div className="flex items-start gap-3 border-b border-line pb-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky text-primary"><Package className="h-5 w-5" /></div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2"><CardTitle>{product.name}</CardTitle><span className="rounded-full bg-canvas px-2.5 py-1 text-[11px] font-semibold capitalize text-muted">{product.product_type}</span></div>
              {product.description && <CardDescription className="mt-1">{product.description}</CardDescription>}
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {product.plans.map((plan) => (
              <div key={plan.id} className="flex flex-col rounded-xl border border-line bg-white p-4">
                <div><p className="text-xs font-semibold uppercase tracking-wide text-primary">Subscription plan</p><h3 className="mt-2 text-lg font-semibold text-ink">{plan.name}</h3></div>
                <p className="mt-3 text-2xl font-bold text-ink">{plan.price}<span className="ml-1 text-sm font-normal text-muted">/ {plan.interval_count} {plan.billing_interval}{plan.interval_count > 1 ? "s" : ""}</span></p>
                <ul className="mt-4 flex-1 space-y-2 text-sm text-muted">
                  {plan.features.length ? plan.features.map((feature) => <li key={feature} className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />{feature}</li>) : <li>Recurring access to this service.</li>}
                </ul>
                <div className="mt-5 grid gap-2">
                  <Button className="w-full" disabled={purchasingPlanId !== null || requestingPlanId !== null} onClick={() => void buyPlan(plan.id)}>
                    {purchasingPlanId === plan.id ? "Starting subscription…" : `Buy now · ${plan.price}`}
                  </Button>
                  <Button className="w-full" variant="secondary" disabled={purchasingPlanId !== null || requestingPlanId !== null} onClick={() => void requestPlan(plan.id)}>
                    {requestingPlanId === plan.id ? "Sending request…" : "Request company approval"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ))}

      {catalog?.company_email && <p className="text-center text-sm text-muted">Questions about a service? <a className="font-medium text-primary hover:underline" href={`mailto:${catalog.company_email}`}>Contact {catalog.company_name}</a></p>}
    </div>
  );
}
