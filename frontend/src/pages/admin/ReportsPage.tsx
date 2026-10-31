import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Report = {
  start_date: string;
  end_date: string;
  revenue_received: string;
  payments_count: number;
  subscriptions_created: number;
  invoices_issued: number;
  outstanding_balance: string;
};
type RevenuePoint = { month: string; revenue: string };

function localDate(date: Date) {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

export function ReportsPage() {
  const today = localDate(new Date());
  const yearStart = `${today.slice(0, 4)}-01-01`;
  const [start, setStart] = useState(yearStart);
  const [end, setEnd] = useState(today);
  const [report, setReport] = useState<Report | null>(null);
  const [revenue, setRevenue] = useState<RevenuePoint[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(from = start, to = end) {
    setLoading(true);
    setError("");
    try {
      const query = `start_date=${encodeURIComponent(from)}&end_date=${encodeURIComponent(to)}`;
      const [summary, trend] = await Promise.all([
        api<Report>(`/analytics/report?${query}`),
        api<RevenuePoint[]>("/analytics/revenue?months=12"),
      ]);
      setReport(summary);
      setRevenue(trend);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load report data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(yearStart, today); }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (start > end) {
      setError("Start date must be on or before the end date.");
      return;
    }
    void load(start, end);
  }

  const cards: [string, string | number][] = [
    ["Revenue received", report?.revenue_received ?? "—"],
    ["Payments recorded", report?.payments_count ?? "—"],
    ["New subscriptions", report?.subscriptions_created ?? "—"],
    ["Invoices issued", report?.invoices_issued ?? "—"],
    ["Outstanding balance", report?.outstanding_balance ?? "—"],
  ];

  return <div className="space-y-6">
    <div><h1 className="page-title">Reports</h1><p className="mt-1 text-sm text-muted">Review payments, subscriptions, invoices, and outstanding balances for a date range.</p></div>
    <Card>
      <form className="flex flex-wrap items-end gap-4" onSubmit={submit}>
        <div className="min-w-40 space-y-1.5"><Label htmlFor="report-start">From</Label><Input id="report-start" type="date" value={start} max={end} onChange={event => setStart(event.target.value)} required /></div>
        <div className="min-w-40 space-y-1.5"><Label htmlFor="report-end">To</Label><Input id="report-end" type="date" value={end} min={start} max={today} onChange={event => setEnd(event.target.value)} required /></div>
        <Button type="submit" disabled={loading}>{loading ? "Loading…" : "Apply dates"}</Button>
      </form>
    </Card>
    {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p>}
    <section aria-live="polite" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      {cards.map(([label, value]) => <Card key={label}><CardDescription>{label}</CardDescription><CardTitle className="mt-3 text-2xl">{loading ? "…" : value}</CardTitle></Card>)}
    </section>
    <Card>
      <CardTitle>Monthly revenue</CardTitle><CardDescription className="mt-1">Recorded payments across the last 12 months.</CardDescription>
      <div role="img" aria-label="Monthly revenue bar chart" className="mt-6 flex h-56 items-end gap-2 border-b border-line px-2 sm:gap-4">
        {revenue.map(point => {
          const max = Math.max(...revenue.map(item => Number(item.revenue)), 1);
          const height = Math.max(4, Number(point.revenue) / max * 100);
          return <div key={point.month} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-2">
            <div className="w-full max-w-12 rounded-t-md bg-primary/80" style={{ height: `${height}%` }} title={`${point.month}: ${point.revenue}`} />
            <span className="pb-2 text-[10px] text-muted">{new Date(`${point.month}-01T00:00:00`).toLocaleDateString(undefined, { month: "short" })}</span>
          </div>;
        })}
      </div>
    </Card>
  </div>;
}
