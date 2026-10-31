import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BriefcaseBusiness, Building2, Eye, EyeOff, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/api";
import { roleHome } from "@/lib/utils";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const demoAccounts = [
    { label: "Admin", email: "admin@example.com", icon: ShieldCheck },
    { label: "Staff", email: "staff@example.com", icon: BriefcaseBusiness },
    { label: "Customer", email: "customer@example.com", icon: Building2 },
  ];

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const user = await login(email, password);
      navigate(roleHome(user.role), { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to sign in");
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthFrame
      title="Sign in to Brightloop"
      subtitle="Subscription Management and Recurring Billing System. Choose your workspace to continue."
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        {error ? <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{error}</p> : null}
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <div className="relative">
            <Input
              id="password"
              type={show ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="pr-10"
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted"
              onClick={() => setShow((value) => !value)}
              aria-label={show ? "Hide password" : "Show password"}
            >
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>
        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-sm text-primary hover:underline">
            Forgot password
          </Link>
        </div>
        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        New customer?{" "}
        <Link to="/register" className="font-medium text-primary hover:underline">
          Create an account
        </Link>
      </p>
      <div className="mt-6 border-t border-line pt-5">
        <p className="text-center text-xs font-semibold uppercase tracking-[0.16em] text-muted">Try a demo workspace</p>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {demoAccounts.map(({ label, email, icon: Icon }) => (
            <button
              key={email}
              type="button"
              className="flex flex-col items-center gap-1 rounded-xl border border-line bg-canvas px-2 py-3 text-xs font-semibold text-ink transition hover:-translate-y-0.5 hover:border-primary/40 hover:bg-white"
              onClick={() => { setEmail(email); setPassword("DemoPass123!"); setError(""); }}
            >
              <Icon className="h-4 w-4 text-primary" />
              {label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-center text-xs text-muted">Password: DemoPass123!</p>
      </div>
    </AuthFrame>
  );
}

export function AuthFrame({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <img src="/BrightLoop%20Rounded%20Wordmark%20(2).png" alt="Brightloop" className="mx-auto h-16 w-48 object-contain" />
          <p className="mt-2 text-sm text-muted">Subscription Management and Recurring Billing System.</p>
        </div>
        <Card>
          <h1 className="text-[20px] font-semibold text-ink">{title}</h1>
          <p className="mt-1 text-sm text-muted">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </Card>
      </div>
    </div>
  );
}
