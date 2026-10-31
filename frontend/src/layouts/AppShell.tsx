import { Bell, LogOut, Search } from "lucide-react";
import type { ComponentType } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { cn, roleLabel } from "@/lib/utils";

type NavItem = { to: string; label: string; icon: ComponentType<{ className?: string }> };

export function AppShell({
  title,
  items,
  variant = "internal",
}: {
  title: string;
  items: NavItem[];
  variant?: "internal" | "portal";
}) {
  const { user, logout } = useAuth();

  if (variant === "portal") {
    return (
      <div className="flex min-h-screen bg-canvas">
        <aside className="hidden w-[250px] shrink-0 bg-sidebar text-white md:flex md:flex-col">
          <div className="flex h-20 items-center px-5"><div className="rounded-md bg-white px-2.5 py-1.5"><img src="/BrightLoop%20Rounded%20Wordmark%20(2).png" alt="Brightloop" className="h-8 w-24 object-contain" /></div></div>
          <p className="px-6 pb-4 text-xs uppercase tracking-wide text-slate-400">{title}</p>
          <nav className="flex flex-1 flex-col gap-1 px-3">
            {items.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => cn("flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium", isActive ? "bg-primary text-white" : "text-slate-300 hover:bg-white/5 hover:text-white")}><item.icon className="h-4 w-4" />{item.label}</NavLink>)}
          </nav>
          <div className="border-t border-white/10 p-4"><div className="text-sm font-medium">{user?.name}</div><div className="text-xs text-slate-400">Customer account</div></div>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-line bg-white">
            <div className="flex h-16 items-center justify-between px-5 md:px-6"><div className="flex items-center gap-3 md:hidden"><img src="/BrightLoop%20Rounded%20Wordmark%20(2).png" alt="Brightloop" className="h-9 w-24 object-contain" /><span className="text-sm font-semibold text-ink">{title}</span></div><span className="hidden text-sm text-muted md:block">{user?.name} <span className="text-line">·</span> {user?.email}</span><Button variant="secondary" size="sm" onClick={() => void logout()}><LogOut className="h-4 w-4" />Sign out</Button></div>
            <nav aria-label="Customer navigation" className="flex gap-1 overflow-x-auto px-4 pb-3 md:hidden">{items.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => cn("whitespace-nowrap rounded-lg px-3 py-2 text-xs font-medium", isActive ? "bg-primary/10 text-primary" : "text-muted hover:bg-canvas")}>{item.label}</NavLink>)}</nav>
          </header>
          <main className="flex-1 px-4 py-5 sm:px-6 md:py-6"><Outlet /></main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-canvas">
      <aside className="hidden w-[250px] shrink-0 bg-sidebar text-white md:flex md:flex-col">
        <div className="flex h-20 items-center px-5">
          <div className="rounded-md bg-white px-2.5 py-1.5">
            <img src="/BrightLoop%20Rounded%20Wordmark%20(2).png" alt="Brightloop" className="h-8 w-24 object-contain" />
          </div>
        </div>
        <p className="px-6 pb-4 text-xs uppercase tracking-wide text-slate-400">{title}</p>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
                  isActive ? "bg-primary text-white" : "text-slate-300 hover:bg-white/5 hover:text-white",
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 p-4">
          <div className="text-sm font-medium">{user?.name}</div>
          <div className="text-xs text-slate-400">{roleLabel(user?.role || "")}</div>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-line bg-white px-6">
          <div className="flex items-center gap-3 text-sm text-muted">
            <Search className="h-4 w-4" />
            <span className="hidden sm:inline">Search arrives with catalogue and billing</span>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" className="rounded-lg p-2 text-muted hover:bg-canvas" aria-label="Notifications">
              <Bell className="h-4 w-4" />
            </button>
            <Button variant="secondary" size="sm" onClick={() => void logout()}>
              <LogOut className="h-4 w-4" />
              Sign out
            </Button>
          </div>
        </header>
        <main className="flex-1 px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
