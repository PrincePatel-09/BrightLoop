import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function roleHome(role: string) {
  if (role === "admin") return "/admin/dashboard";
  if (role === "staff") return "/staff/dashboard";
  if (role === "company_admin" || role === "company_staff") return "/company/dashboard";
  return "/my/dashboard";
}

export function roleLabel(role: string) {
  if (role === "admin") return "Admin";
  if (role === "staff") return "Staff";
  if (role === "company_admin") return "Company admin";
  if (role === "company_staff") return "Company staff";
  return "Customer";
}
