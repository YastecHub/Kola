import { Activity, Banknote, Building2, CheckCircle2, CircleDollarSign, ClipboardCheck, ShieldCheck, Users } from "lucide-react";

export type EventTone = "success" | "warning" | "info";

export const steps = [
  { title: "Group Registers", body: "Mama Bisi creates her group on KOLA. Each member gets a Squad Virtual Account.", icon: Users },
  { title: "Aminat Contributes", body: "Every Friday, N5,000 lands in her Squad VA and becomes a signed contribution event.", icon: CircleDollarSign },
  { title: "Trade Proof Added", body: "Supplier payments through Squad links add trade behavior to the story.", icon: ClipboardCheck },
  { title: "AI Builds Her Score", body: "Five behavioral signals become a KOLA Score with plain-English explanations.", icon: Activity },
  { title: "Lender Sees Her", body: "A lender queries the API and approves her loan in milliseconds.", icon: Building2 }
];

export const scoreFactors = [
  { name: "Payment streak", value: 18, tone: "success" },
  { name: "Supplier consistency", value: 12, tone: "success" },
  { name: "Recovery speed", value: 8, tone: "success" },
  { name: "Collector trust", value: 4, tone: "success" },
  { name: "Amount variation", value: -6, tone: "warning" }
];

export const events: { title: string; amount: string; meta: string; tone: EventTone }[] = [
  { title: "Week 12 Contribution", amount: "N5,000", meta: "09:42:17 · Squad verified", tone: "success" },
  { title: "Supplier Payment - Kano Market", amount: "N47,500", meta: "Trade event recorded", tone: "info" },
  { title: "Week 11 Contribution", amount: "N5,000", meta: "On time · Squad verified", tone: "success" },
  { title: "Week 10 Contribution", amount: "N5,000", meta: "On time · Squad verified", tone: "success" },
  { title: "Week 7 Contribution - Late", amount: "N5,000", meta: "3 days late · recovered same week", tone: "warning" }
];

export const members = [
  { name: "Aminat Ibrahim", phone: "+234 803 XXX XXXX", account: "0123456789", score: 714, status: "Good" },
  { name: "Chika Okonkwo", phone: "+234 806 XXX XXXX", account: "0123456790", score: 692, status: "Good" },
  { name: "Fatima Yusuf", phone: "+234 809 XXX XXXX", account: "0123456791", score: 731, status: "Excellent" },
  { name: "Bola Adeyemi", phone: "+234 701 XXX XXXX", account: "0123456792", score: 648, status: "Fair" }
];

export const stats = [
  ["14M+", "Nigerians in informal savings groups"],
  ["N5B/mo", "Already flowing through digitized Ajo platforms"],
  ["<5%", "Default rate in Ajo-based lending"],
  ["40M", "Informal MSMEs KOLA can eventually score"]
];

export const lenderStats = [
  ["24", "Queries today"],
  ["18", "Approved today"],
  ["671", "Avg score queried"],
  ["976", "API calls remaining"]
];

export const approvalSignals = [
  "11-week consecutive payment streak",
  "Consistent supplier payments recorded",
  "Fast recovery after 1 near-miss"
];

export const trustItems = [
  { icon: ShieldCheck, label: "Squad-verified" },
  { icon: CheckCircle2, label: "Zero credit risk" },
  { icon: Banknote, label: "14M+ participants" }
];
