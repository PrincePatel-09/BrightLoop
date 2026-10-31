import { useEffect, useState } from "react";
import { ArrowUpRight, CircleAlert, CreditCard, RefreshCw, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";

type Role = "admin" | "staff";
type Metrics = {
  companies: number;
  users: number;
  customers: number;
  subscriptions: number;
  active_subscriptions: number;
  mrr: string;
  arr: string;
  revenue_received: string;
  outstanding_balance: string;
  overdue_invoices: number;
  upcoming_renewals: number;
};
type RevenuePoint = { month: string; revenue: string };
type SubscriptionStatus = { status: string; count: number };
type Activity = { type: string; label: string; date: string; amount: string };

const CONFIG = {
  admin: {
    eyebrow: "Control room",
    title: "Keep the business moving.",
    subtitle: "A clear view of revenue, customer growth, and the settings behind every recurring charge.",
    links: [["/admin/customers", "Review customers"], ["/admin/settings", "Open settings"], ["/admin/audit", "View audit history"]],
  },
  staff: {
    eyebrow: "Operations desk",
    title: "The next action is clear.",
    subtitle: "Work through renewals, customer requests, invoices, and payments from one focused queue.",
    links: [["/staff/customers", "Open customers"], ["/staff/invoices", "Process invoices"], ["/staff/payments", "Record payment"]],
  },
} as const;

const staffStatConfig = [
  ["Customers", "customers", Users, "bg-sky"],
  ["Active subscriptions", "active_subscriptions", RefreshCw, "bg-mint"],
  ["Revenue received", "revenue_received", CreditCard, "bg-[#FFF0DD]"],
  ["Outstanding balance", "outstanding_balance", CircleAlert, "bg-[#FDE5E5]"],
] as const;
const adminStatConfig = [
  ["Companies", "companies", Users, "bg-sky"],
  ["Users", "users", Users, "bg-mint"],
  ["Subscriptions", "subscriptions", RefreshCw, "bg-[#FFF0DD]"],
  ["MRR", "mrr", CreditCard, "bg-sky"],
  ["ARR", "arr", CreditCard, "bg-mint"],
  ["Revenue received", "revenue_received", CreditCard, "bg-[#FFF0DD]"],
  ["Outstanding balance", "outstanding_balance", CircleAlert, "bg-[#FDE5E5]"],
] as const;

export function RoleDashboard({ role }: { role: Role }) {
  const { user } = useAuth();
  const config = CONFIG[role];
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [revenue, setRevenue] = useState<RevenuePoint[]>([]);
  const [statuses, setStatuses] = useState<SubscriptionStatus[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void Promise.all([api<Metrics>("/analytics/overview"), api<RevenuePoint[]>("/analytics/revenue?months=6"), api<SubscriptionStatus[]>("/analytics/subscription-statuses"), api<Activity[]>("/analytics/activity?limit=6")])
      .then(([overview, trend, breakdown, recent]) => { setMetrics(overview); setRevenue(trend); setStatuses(breakdown); setActivity(recent); })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load dashboard metrics"));
  }, []);

  return (
    <div className="mx-auto max-w-[1400px] space-y-6">
      <section className="relative overflow-hidden rounded-xl bg-sidebar px-6 py-7 text-white shadow-lift md:px-8">
        <div className="relative z-10 max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-200">{config.eyebrow}</p>
          <h1 className="mt-3 text-2xl font-semibold md:text-3xl">{config.title}</h1>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">{config.subtitle}</p>
          <p className="mt-5 text-sm text-slate-400">Signed in as <span className="font-semibold text-white">{user?.name}</span></p>
        </div>
        <div className="absolute -right-10 -top-20 h-64 w-64 rounded-full border-[32px] border-white/5" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <Card>
          <CardTitle>Revenue received</CardTitle><CardDescription className="mt-1">Payments recorded by month, over the last six months.</CardDescription>
          <div role="img" aria-label="Monthly revenue received bar chart" className="mt-5 flex h-48 items-end gap-3 border-b border-line px-2">
            {revenue.map(point => { const max = Math.max(...revenue.map(item => Number(item.revenue)), 1); const height = Math.max(6, Number(point.revenue) / max * 100); return <div key={point.month} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2"><span className="truncate text-[10px] text-muted">{point.revenue}</span><div className="w-full max-w-12 rounded-t-md bg-primary/80" style={{ height: `${height}%` }} title={`${point.month}: ${point.revenue}`} /><span className="pb-2 text-[10px] text-muted">{new Date(`${point.month}-01T00:00:00`).toLocaleDateString(undefined, { month: "short" })}</span></div>; })}
          </div>
        </Card>
        <Card>
          <CardTitle>Subscription status</CardTitle><CardDescription className="mt-1">Current subscription count by status.</CardDescription>
          <div className="mt-5 space-y-3">{statuses.map(item => <div key={item.status} className="flex items-center justify-between rounded-xl bg-canvas px-4 py-3"><span className="text-sm capitalize">{item.status}</span><span className="font-semibold">{item.count}</span></div>)}{statuses.length === 0 && <p className="text-sm text-muted">No subscriptions recorded yet.</p>}</div>
        </Card>
      </section>

      {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p>}

      <section className={`grid gap-4 sm:grid-cols-2 ${role === "admin" ? "xl:grid-cols-5" : "xl:grid-cols-4"}`}>
        {(role === "admin" ? adminStatConfig : staffStatConfig).map(([label, key, Icon, tone]) => (
          <Card key={label} className="group transition hover:-translate-y-0.5 hover:shadow-lift">
            <div className="flex items-start justify-between">
              <div><CardDescription>{label}</CardDescription><CardTitle className="mt-3 text-2xl tracking-[-0.03em]">{metrics?.[key] ?? "-"}</CardTitle></div>
              <div className={`rounded-xl p-2.5 ${tone}`}><Icon className="h-4 w-4 text-ink" /></div>
            </div>
          </Card>
        ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <Card>
          <div className="flex items-start justify-between gap-4"><div><CardTitle>{role === "admin" ? "Business pulse" : "Work queue"}</CardTitle><CardDescription className="mt-1">{role === "admin" ? "Signals worth a closer look today." : "Priorities based on live billing records."}</CardDescription></div><ArrowUpRight className="h-5 w-5 text-primary" /></div>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <MetricRow label="Overdue invoices" value={metrics?.overdue_invoices ?? "-"} tone="text-danger" />
            <MetricRow label="Renewals in 30 days" value={metrics?.upcoming_renewals ?? "-"} tone="text-primary" />
          </div>
          <div className="mt-6 border-t border-line pt-4"><h3 className="text-sm font-semibold">Recent activity</h3><div className="mt-3 space-y-2">{activity.map((item, index) => <div key={`${item.type}-${index}`} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-canvas px-3 py-2"><div><p className="text-sm">{item.label}</p><p className="text-xs text-muted">{new Date(item.date).toLocaleString()}</p></div><span className="text-sm font-medium">{item.amount}</span></div>)}{activity.length === 0 && <p className="text-sm text-muted">No recent activity.</p>}</div></div>
        </Card>
        <Card>
          <CardTitle>Quick actions</CardTitle>
          <div className="mt-4 space-y-2">
            {config.links.map(([to, label]) => <Link key={to} to={to} className="flex items-center justify-between rounded-xl border border-line px-3 py-3 text-sm font-semibold text-ink transition hover:border-primary/40 hover:bg-sky/40"><span>{label}</span><ArrowUpRight className="h-4 w-4 text-primary" /></Link>)}
          </div>
        </Card>
      </div>
    </div>
  );
}

function MetricRow({ label, value, tone }: { label: string; value: string | number; tone: string }) {
  return <div className="rounded-xl bg-canvas px-4 py-4"><p className="text-sm text-muted">{label}</p><p className={`mt-2 text-2xl font-bold ${tone}`}>{value}</p></div>;
}
