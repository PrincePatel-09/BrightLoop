import { useEffect, useState } from "react";

import { Card } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";

type AuditEvent = { id: number; actor_user_id: number | null; action: string; entity_type: string; entity_id: number | null; details: Record<string, unknown>; created_at: string };

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { void api<AuditEvent[]>("/audit?limit=100").then(setEvents).catch(err => setError(err instanceof ApiError ? err.message : "Unable to load audit events")); }, []);
  return <div className="space-y-6"><div><h1 className="page-title">Audit history</h1><p className="mt-1 text-sm text-muted">Recent administrative and financial changes.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
    <div className="grid gap-3">{events.map(event => <Card key={event.id}><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold">{event.action.replaceAll(".", " · ")}</h2><p className="mt-1 text-sm text-muted">{event.entity_type}{event.entity_id ? ` #${event.entity_id}` : ""} · Actor {event.actor_user_id ?? "system"}</p>{Object.keys(event.details).length > 0 && <p className="mt-2 text-xs text-muted">{Object.entries(event.details).map(([key, value]) => `${key}: ${String(value)}`).join(" · ")}</p>}</div><time className="text-xs text-muted">{new Date(event.created_at).toLocaleString()}</time></div></Card>)}{events.length === 0 && <Card className="text-sm text-muted">No audit events recorded yet.</Card>}</div>
  </div>;
}
