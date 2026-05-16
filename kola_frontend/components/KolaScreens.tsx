"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, ArrowLeft, ArrowRight, Banknote, Check, CheckCircle2, ChevronDown, Clipboard, Cpu, CreditCard, Eye, EyeOff, Menu, Phone, Plus, Radio, Search, ShieldCheck, Trash2, UserRound, X } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { LoadingDots } from "@/components/ui/LoadingDots";
import { Logo } from "@/components/Logo";
import { approvalSignals, events, lenderStats, members, scoreFactors, stats, steps, trustItems } from "@/lib/data";
import { createKolaGroup, fetchAminatAiScore, fetchAminatScore, fetchTraderScore, KolaGroup, KolaScore } from "@/lib/kolaApi";
import { useClipboard } from "@/hooks/useClipboard";
import { useCountUp } from "@/hooks/useCountUp";
import { useSSE } from "@/hooks/useSSE";

const accountOptions = [
  { value: "group" as const, icon: UserRound, title: "Group Admin", body: "I manage an Ajo group and want to digitize contributions." },
  { value: "lender" as const, icon: Banknote, title: "Lender / MFB", body: "I want to query KOLA Scores for credit decisions." }
];

const fade = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" }
} as const;

function Orbs() {
  return (
    <>
      <span className="absolute inset-x-0 top-20 h-px bg-gradient-to-r from-transparent via-kola-300/40 to-transparent" />
      <span className="absolute inset-x-0 bottom-24 h-px bg-gradient-to-r from-transparent via-amber-300/30 to-transparent" />
      <span className="absolute left-1/2 top-0 h-full w-px bg-gradient-to-b from-transparent via-white/10 to-transparent" />
    </>
  );
}

export function Navbar() {
  const [open, setOpen] = useState(false);
  const nav = ["How it Works", "For Lenders", "For Groups", "About"];
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-kola-950/70 backdrop-blur-xl">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:h-[72px] lg:px-8">
        <Link href="/" aria-label="KOLA home"><Logo /></Link>
        <div className="hidden items-center gap-8 text-sm font-medium text-white/75 lg:flex">
          {nav.map((item) => <a key={item} href={`/#${item.toLowerCase().replaceAll(" ", "-")}`} className="hover:text-white">{item}</a>)}
        </div>
        <div className="hidden gap-3 lg:flex">
          <Button href="/auth/signin" variant="secondary">Sign In</Button>
          <Button href="/auth/signup">Get Started</Button>
        </div>
        <button className="grid h-11 w-11 place-items-center text-white lg:hidden" aria-label="Open navigation" onClick={() => setOpen(true)}>
          <Menu />
        </button>
      </nav>
      {open ? (
        <motion.div initial={{ x: "100%" }} animate={{ x: 0 }} className="fixed inset-0 z-50 bg-kola-950/95 p-6 text-white backdrop-blur-xl lg:hidden">
          <div className="flex justify-between">
            <Logo />
            <button aria-label="Close navigation" onClick={() => setOpen(false)}><X /></button>
          </div>
          <div className="mt-16 grid gap-7 text-3xl font-dm-serif">
            {nav.map((item, index) => (
              <motion.a initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.08 }} key={item} href={`/#${item.toLowerCase().replaceAll(" ", "-")}`} onClick={() => setOpen(false)}>{item}</motion.a>
            ))}
          </div>
          <div className="mt-12 grid gap-3">
            <Button href="/auth/signin" variant="secondary">Sign In</Button>
            <Button href="/auth/signup">Get Started</Button>
          </div>
        </motion.div>
      ) : null}
    </header>
  );
}

export function Footer() {
  return (
    <footer className="grain bg-ink-950 px-4 py-14 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 rounded-none bg-kola-500 px-6 py-8 text-center font-fraunces text-2xl italic text-kola-950">
          14 million Nigerians have been proving their creditworthiness every Friday. KOLA makes it count.
        </div>
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {["Product", "For Lenders", "Company", "Legal"].map((col) => (
            <div key={col}>
              <h3 className="mb-4 font-semibold">{col}</h3>
              <div className="grid gap-2 text-sm text-white/60">
                <span>Score API</span><span>Ajo Groups</span><span>Squad Verification</span><span>Security</span>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-col justify-between gap-3 border-t border-white/10 pt-6 text-sm text-white/50 sm:flex-row">
          <span>© 2025 KOLA Technologies. All rights reserved.</span>
          <span>Built on Squad</span>
        </div>
      </div>
    </footer>
  );
}

type ScoreFactor = {
  name: string;
  value: number;
  tone: string;
};

type DisplayEvent = { title: string; amount: string; meta: string; tone: "success" | "warning" | "info" };

function formatNaira(value: number | string | null | undefined) {
  const amount = Number(value ?? 0);
  return `N${Number.isFinite(amount) ? amount.toLocaleString() : "0"}`;
}

function scoreToFactors(scoreData: KolaScore): ScoreFactor[] {
  return [
    { name: "Payment streak", value: scoreData.shap.streak, tone: scoreData.shap.streak >= 0 ? "success" : "warning" },
    { name: "Supplier consistency", value: scoreData.shap.trade, tone: scoreData.shap.trade >= 0 ? "success" : "warning" },
    { name: "Recovery speed", value: scoreData.shap.catchup, tone: scoreData.shap.catchup >= 0 ? "success" : "warning" },
    { name: "Collector trust", value: scoreData.shap.collector, tone: scoreData.shap.collector >= 0 ? "success" : "warning" },
    { name: "Amount variation", value: scoreData.shap.amount_std, tone: scoreData.shap.amount_std >= 0 ? "success" : "warning" }
  ];
}

function eventFromBackend(event: NonNullable<KolaScore["events"]>[number], index: number): DisplayEvent {
  const occurredAt = event.occurred_at ? new Date(event.occurred_at) : new Date();
  const type = event.event_type?.toLowerCase() ?? "contribution";
  return {
    title: type.includes("trade") ? "Trade payment received" : `Week ${index + 1} Contribution`,
    amount: formatNaira(event.amount),
    meta: `${occurredAt.toLocaleDateString()} · ${event.verified ? "Squad verified" : "Pending verification"}`,
    tone: event.verified ? "success" : "warning"
  };
}

function RealtimePlatformStrip() {
  const items = [
    { icon: Radio, label: "Squad Webhooks", value: "Listening" },
    { icon: Cpu, label: "AI Scoring", value: "Live SHAP" },
    { icon: CreditCard, label: "Virtual Accounts", value: "Auto-issued" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 22 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1.18, duration: 0.55 }}
      className="mx-auto mt-12 grid max-w-4xl gap-3 rounded-2xl border border-white/15 bg-white/[0.08] p-3 text-left shadow-glow backdrop-blur-xl sm:grid-cols-3"
    >
      {items.map(({ icon: Icon, label, value }) => (
        <div key={label} className="group rounded-xl border border-white/10 bg-kola-950/35 p-4 transition duration-300 hover:-translate-y-1 hover:border-kola-300/50 hover:bg-white/[0.1]">
          <div className="flex items-center justify-between">
            <Icon className="text-kola-300" size={20} />
            <span className="live-dot" />
          </div>
          <p className="mt-4 text-xs uppercase tracking-[0.18em] text-white/45">{label}</p>
          <p className="mt-1 font-mono text-lg text-white">{value}</p>
        </div>
      ))}
    </motion.div>
  );
}

function AiActivityPanel({ scoreData }: { scoreData?: KolaScore | null }) {
  const score = scoreData?.score ?? 714;
  const confidence = scoreData?.confidence ?? "Awaiting live model";
  const eventsCount = scoreData?.verified_events_count ?? 0;

  return (
    <div className="glass-card-dark p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-white/45">Realtime Model</p>
          <h3 className="mt-1 font-dm-serif text-2xl text-white">Underwriting engine</h3>
        </div>
        <Activity className="animate-pulse text-kola-300" />
      </div>
      <div className="mt-5 grid gap-3">
        {[
          ["Score stream", String(score)],
          ["Confidence", confidence],
          ["Verified events", String(eventsCount)],
        ].map(([label, value]) => (
          <div key={label} className="flex items-center justify-between border-b border-white/10 pb-3 text-sm">
            <span className="text-white/50">{label}</span>
            <span className="font-mono text-kola-200">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BackendErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-error/20 bg-red-50 p-4 text-sm text-error">
      <div className="flex items-start gap-3">
        <X className="mt-0.5 shrink-0" size={16} />
        <div>
          <p className="font-semibold">Frontend could not reach the KOLA backend.</p>
          <p className="mt-1">{message}</p>
          <p className="mt-2 text-ink-600">Set `KOLA_API_URL` and `KOLA_API_KEY` in `kola_frontend/.env.local`, then restart `npm run dev`.</p>
        </div>
      </div>
    </div>
  );
}

export function ScoreDisplay({ compact = false, value = 714, confidence = "Good · Low Risk" }: { compact?: boolean; value?: number; confidence?: string }) {
  const score = useCountUp(value, 1200, true, 600);
  return (
    <div aria-live="polite" className={`rounded-2xl border border-kola-400/30 bg-kola-950 p-6 text-white shadow-glow ${compact ? "" : "md:p-10"}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-kola-300">KOLA Score</p>
      <div className={`font-mono font-semibold ${compact ? "text-6xl" : "text-8xl md:text-9xl"}`}>{score}</div>
      <span className="rounded-full bg-kola-400 px-3 py-1 text-sm font-semibold text-kola-950">{confidence}</span>
      <div className="mt-8">
        <div className="h-3 rounded-full bg-gradient-to-r from-error via-amber-400 to-kola-400">
          <div className="ml-[73%] h-5 w-5 -translate-y-1 rounded-full border-4 border-white bg-kola-500" />
        </div>
        <div className="mt-2 flex justify-between text-xs text-white/50"><span>Poor</span><span>Fair</span><span>Good</span><span>Excellent</span></div>
      </div>
    </div>
  );
}

export function ShapBars({ factors = scoreFactors }: { factors?: ScoreFactor[] }) {
  return (
    <div className="space-y-4">
      {factors.map((factor, index) => (
        <div key={factor.name} className="grid grid-cols-[150px_1fr_42px] items-center gap-3 text-sm">
          <span className="text-ink-600">{factor.name}</span>
          <motion.div initial={{ width: 0 }} whileInView={{ width: `${Math.abs(factor.value) * 5}%` }} viewport={{ once: true }} transition={{ delay: index * 0.15 }} className={`h-4 rounded ${factor.tone === "success" ? "bg-kola-400" : "bg-amber-400"}`} />
          <span className="font-mono text-ink-500">{factor.value > 0 ? "+" : ""}{factor.value}</span>
        </div>
      ))}
    </div>
  );
}

function LandingHero() {
  return (
    <section className="hero-grid grain relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-28 text-center text-white">
      <Orbs />
      <motion.div initial="initial" animate="whileInView" className="relative z-10 mx-auto max-w-4xl">
        <motion.div {...fade} transition={{ delay: 0.3 }}><Badge dark>Squad-Verified Credit Intelligence</Badge></motion.div>
        <motion.h1 initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8, duration: 0.8 }} className="mt-7 font-fraunces text-5xl font-extrabold leading-[1.02] tracking-normal sm:text-6xl lg:text-7xl">
          Before finance can read you,<br />someone has to write your story.
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.05 }} className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-white/65">
          Aminat has contributed N5,000 every Friday for three years. She has never missed a payment. KOLA makes her visible.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.1 }} className="mt-9 flex flex-col justify-center gap-4 sm:flex-row">
          <Button href="/onboarding">Start Your Group <ArrowRight size={18} /></Button>
          <Button href="/lender/dashboard" variant="secondary">For Lenders <ArrowRight size={18} /></Button>
        </motion.div>
        <RealtimePlatformStrip />
        <div className="mt-12 flex flex-wrap justify-center gap-5 text-sm text-white/70">
          {trustItems.map(({ icon: Icon, label }) => <span key={label} className="inline-flex items-center gap-2"><Icon size={16} />{label}</span>)}
        </div>
      </motion.div>
      <ChevronDown className="absolute bottom-8 animate-bounce text-white/50" />
    </section>
  );
}

export function LandingPage() {
  return (
    <>
      <Navbar />
      <main>
        <LandingHero />
        <section className="bg-kola-950 px-4 py-24 text-white sm:px-6 lg:px-8">
          <motion.div {...fade} className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-kola-300">The Problem</p>
              <h2 className="mt-4 font-fraunces text-4xl italic leading-tight sm:text-5xl">N13 trillion. That is the credit gap no bank will touch.</h2>
              <p className="mt-6 max-w-xl text-lg leading-8 text-white/65">Nigeria's formal bureaus score loan histories and bank accounts. They are blind to the 14 million Nigerians running disciplined Ajo groups.</p>
              <blockquote className="mt-8 border-l-4 border-kola-400 pl-5 text-white/80">She has been running a more disciplined credit operation than most bank customers for three years, and the bank cannot see a single day of it.</blockquote>
            </div>
            <div className="relative min-h-[360px]">
              {stats.slice(0, 3).map(([number, label], index) => (
                <Card key={number} tone="dark" className={`absolute left-${index * 8} top-${index * 20} w-[85%] p-6 shadow-glow`} style={{ transform: `translate(${index * 30}px, ${index * 76}px) rotate(${index === 0 ? -2 : index === 2 ? 2 : 0}deg)` }}>
                  <div className="font-mono text-4xl text-kola-300">{number}</div>
                  <p className="mt-2 text-white/70">{label}</p>
                </Card>
              ))}
            </div>
          </motion.div>
        </section>
        <section id="how-it-works" className="bg-ink-50 px-4 py-24 sm:px-6 lg:px-8">
          <motion.div {...fade} className="mx-auto max-w-7xl text-center">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-kola-600">How It Works</p>
            <h2 className="mt-4 font-dm-serif text-4xl sm:text-5xl">Five steps. Zero behavior change.</h2>
            <p className="mx-auto mt-4 max-w-2xl text-ink-600">Aminat keeps doing what she already does. KOLA makes it count.</p>
            <div className="scroll-snap mt-12 flex gap-4 overflow-x-auto pb-4 lg:grid lg:grid-cols-5">
              {steps.map(({ title, body, icon: Icon }, index) => (
                <Card key={title} className="min-w-[260px] scroll-ml-4 scroll-snap-align-start p-6 text-left">
                  <div className="font-mono text-6xl text-kola-100">0{index + 1}</div>
                  <Icon className="my-5 text-kola-500" />
                  <h3 className="font-dm-serif text-2xl">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-ink-600">{body}</p>
                </Card>
              ))}
            </div>
          </motion.div>
        </section>
        <section className="bg-kola-900 px-4 py-24 text-white sm:px-6 lg:px-8">
          <motion.div {...fade} className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[.9fr_1.1fr] lg:items-center">
            <ScoreDisplay />
            <Card tone="dark" className="p-6 md:p-8">
              <h3 className="font-dm-serif text-3xl">What shaped this score</h3>
              <p className="mb-8 mt-2 text-white/60">Plain-English credit signals a lender can trust.</p>
              <ShapBars />
            </Card>
          </motion.div>
        </section>
        <section className="bg-ink-950 px-4 py-20 text-white sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-6xl gap-8 text-center sm:grid-cols-2 lg:grid-cols-4">
            {stats.map(([number, label]) => <div key={number} className="border-white/10 lg:border-r"><div className="font-mono text-4xl text-kola-300">{number}</div><p className="mt-2 text-white/60">{label}</p></div>)}
          </div>
        </section>
        <section id="for-lenders" className="grain bg-kola-500 px-4 py-24 text-kola-950 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-4xl text-center">
            <h2 className="font-fraunces text-5xl text-white">Ready to lend to Nigeria's most reliable borrowers?</h2>
            <p className="mx-auto mt-5 max-w-2xl text-lg text-kola-950/75">Query KOLA's API. Get a Squad-verified credit score in milliseconds. No risk on your balance sheet.</p>
            <Button href="/lender/dashboard" variant="light" className="mt-8">Access Lender Dashboard <ArrowRight size={18} /></Button>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function AuthShell({ mode }: { mode: "signin" | "signup" }) {
  return (
    <main className="grid min-h-screen bg-ink-50 lg:grid-cols-2">
      <section className="hero-grid grain relative hidden overflow-hidden p-10 text-white lg:block">
        <Orbs />
        <Link href="/"><Logo /></Link>
        <div className="relative z-10 flex h-full flex-col justify-center">
          <p className="max-w-md font-fraunces text-5xl italic leading-tight">{mode === "signin" ? "156 consecutive Fridays. Zero missed payments. That is creditworthiness." : "Before finance can read you, someone has to write your story. KOLA writes it."}</p>
          <div className="mt-10 grid max-w-md gap-3">
            {["Mama Bisi · 42 members", "GTBank MFB · lender", "Mile 12 Traders · verified"].map((item) => <Card key={item} tone="dark" className="p-4 text-sm text-white/75">{item}</Card>)}
          </div>
          <div className="mt-5 max-w-md"><AiActivityPanel /></div>
        </div>
      </section>
      <section className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <Link href="/" className="mb-8 inline-flex items-center gap-2 text-sm text-ink-500"><ArrowLeft size={16} /> KOLA</Link>
          {mode === "signin" ? <SignInForm /> : <SignupWizard />}
        </div>
      </section>
    </main>
  );
}

function SignInForm() {
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  return (
    <Card className="p-8">
      <h1 className="font-dm-serif text-4xl">Welcome back</h1>
      <p className="mt-2 text-ink-500">Sign in to your KOLA account</p>
      <form className="mt-8 grid gap-5" onSubmit={(event) => { event.preventDefault(); setLoading(true); setTimeout(() => setLoading(false), 900); }}>
        <Input label="Email address" type="email" required />
        <div className="relative">
          <Input label="Password" type={show ? "text" : "password"} required />
          <button type="button" aria-label={show ? "Hide password" : "Show password"} className="absolute right-3 top-9 text-ink-500" onClick={() => setShow(!show)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
        </div>
        <Link href="/auth/signup" className="text-right text-sm text-kola-600">Forgot password?</Link>
        <Button full>{loading ? <LoadingDots /> : "Sign In"}</Button>
      </form>
      <div className="my-6 flex items-center gap-3 text-sm text-ink-400"><span className="h-px flex-1 bg-ink-200" />or<span className="h-px flex-1 bg-ink-200" /></div>
      <Button href="/lender/dashboard" variant="ghost" full>Sign in as a Lender</Button>
      <p className="mt-6 text-center text-sm text-ink-500">Don't have an account? <Link className="text-kola-600" href="/auth/signup">Get started</Link></p>
    </Card>
  );
}

function SignupWizard() {
  const [step, setStep] = useState(0);
  const [role, setRole] = useState<"group" | "lender">("group");
  const strength = 3;
  return (
    <Card className="overflow-hidden p-8">
      <div className="mb-8 flex items-center gap-2 text-xs text-ink-500">
        {["Account Type", "Your Details", "Verification"].map((label, index) => <span key={label} className={`flex items-center gap-2 ${index <= step ? "text-kola-600" : ""}`}><span className={`h-3 w-3 rounded-full border ${index < step ? "bg-kola-500" : index === step ? "border-kola-500" : "border-ink-300"}`} />{label}</span>)}
      </div>
      {step === 0 ? (
        <div>
          <h1 className="font-dm-serif text-3xl">Who are you joining as?</h1>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {accountOptions.map(({ value, icon: Icon, title, body }) => (
              <button key={value} className={`relative rounded-2xl border-2 p-5 text-left transition ${role === value ? "border-kola-500 bg-kola-50 shadow-green" : "border-ink-200"}`} onClick={() => setRole(value)}>
                {role === value ? <Check className="absolute right-4 top-4 text-kola-500" /> : null}
                <Icon className="mb-4 text-kola-600" />
                <h3 className="font-semibold">{title}</h3>
                <p className="mt-2 text-sm text-ink-500">{body}</p>
              </button>
            ))}
          </div>
        </div>
      ) : step === 1 ? (
        <div className="grid gap-4">
          <h1 className="font-dm-serif text-3xl">{role === "group" ? "Your group admin details" : "Your institution details"}</h1>
          <Input label={role === "group" ? "Full name" : "Institution name"} required />
          <Input label="Phone number" inputMode="numeric" autoComplete="tel" placeholder="+234" required />
          <Input label={role === "group" ? "Email address" : "Work email"} type="email" required />
          <Input label="Password" type="password" required />
          <div>
            <div className="grid grid-cols-4 gap-2">{[0, 1, 2, 3].map((i) => <span key={i} className={`h-2 rounded ${i < strength ? "bg-amber-400" : "bg-ink-200"} ${i === 2 ? "bg-kola-400" : ""}`} />)}</div>
            <p className="mt-2 text-sm text-kola-600">Good</p>
          </div>
        </div>
      ) : (
        <div className="text-center">
          <Phone className="mx-auto mb-4 h-12 w-12 text-kola-500" />
          <h1 className="font-dm-serif text-3xl">Verify your phone</h1>
          <p className="mt-2 text-ink-500">We've sent a 6-digit code to +234 XXX XXX XXXX</p>
          <div className="mt-6 grid grid-cols-6 gap-2">
            {Array.from({ length: 6 }).map((_, index) => <input key={index} aria-label={`OTP digit ${index + 1}`} maxLength={1} inputMode="numeric" autoComplete={index === 0 ? "one-time-code" : undefined} className="h-12 rounded-md border border-ink-200 text-center text-lg focus:border-kola-500 focus:ring-4 focus:ring-kola-500/10" />)}
          </div>
          <p className="mt-4 text-sm text-ink-500">Resend in 45s</p>
        </div>
      )}
      <div className="mt-8 flex justify-between">
        <button className="inline-flex items-center gap-2 text-sm text-ink-500" disabled={step === 0} onClick={() => setStep((s) => Math.max(0, s - 1))}><ArrowLeft size={16} /> Back</button>
        <Button onClick={() => step < 2 ? setStep(step + 1) : undefined} href={step === 2 ? (role === "group" ? "/onboarding" : "/lender/dashboard") : undefined}>Continue <ArrowRight size={18} /></Button>
      </div>
    </Card>
  );
}

export function SignInPage() { return <AuthShell mode="signin" />; }
export function SignupPage() { return <AuthShell mode="signup" />; }

export function OnboardingPage() {
  const [membersList, setMembersList] = useState(members.slice(0, 3));
  const [createdGroup, setCreatedGroup] = useState<KolaGroup | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const progress = createdGroup ? 100 : 66;

  async function handleCreateGroup() {
    setIsCreating(true);
    setCreateError(null);
    try {
      const group = await createKolaGroup({
        name: "Mile 12 Tomato Traders",
        description: "Weekly tomato trader contribution group",
        contribution_amount: "5000.00",
        contribution_frequency: "weekly",
        members: membersList.map((member, index) => ({
          full_name: member.name,
          phone: `080300000${index + 1}`,
          email: `${member.name.toLowerCase().replaceAll(" ", ".")}@kola.local`,
          bvn: `2234321165${index}`,
          dob: "07/19/1990",
          gender: "2",
          address: "Mile 12 Market, Lagos",
        })),
      });
      setCreatedGroup(group);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "Unable to create group");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <main className="min-h-screen bg-ink-50">
      <div className="fixed inset-x-0 top-0 z-50 h-1 bg-ink-200"><div className="h-full bg-kola-500 transition-all" style={{ width: `${progress}%` }} /></div>
      <section className="mx-auto max-w-3xl px-4 py-14 sm:px-6">
        <Link href="/" className="text-sm text-ink-500">Dashboard / Create Group</Link>
        <h1 className="mt-4 font-dm-serif text-4xl">Create your Ajo group</h1>
        <div className="mt-8 grid gap-6">
          <Card className="p-6">
            <h2 className="font-dm-serif text-2xl">Group Details</h2>
            <div className="mt-5 grid gap-4">
              <Input label="Group name" defaultValue="Mile 12 Tomato Traders" />
              <Input label="Weekly contribution amount (N)" inputMode="decimal" defaultValue="5,000" />
              <div><span className="mb-2 block text-sm font-medium text-ink-700">Contribution day</span><div className="grid grid-cols-7 gap-2">{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map((d) => <button key={d} className={`min-h-11 rounded-md border ${d === "Fri" ? "border-kola-500 bg-kola-500 text-white" : "border-ink-200"}`}>{d}</button>)}</div></div>
              <label><span className="mb-2 block text-sm font-medium text-ink-700">Group description</span><textarea maxLength={200} className="min-h-28 w-full rounded-md border border-ink-200 p-4" /></label>
            </div>
          </Card>
          <Card className="p-6">
            <h2 className="font-dm-serif text-2xl">Add group members</h2>
            <p className="mt-1 text-ink-500">Each member will receive a Squad Virtual Account number.</p>
            <div className="mt-5 grid gap-3">
              {membersList.map((member, index) => <div key={member.account} className="grid gap-3 rounded-xl border border-ink-200 p-4 sm:grid-cols-[40px_1fr_1fr_40px]"><span className="grid h-10 w-10 place-items-center rounded-full bg-kola-100 text-kola-700">{member.name[0]}</span><Input label="Full name" defaultValue={member.name} /><Input label="Phone number" defaultValue={member.phone} /><button aria-label="Delete member row" onClick={() => setMembersList((list) => list.filter((_, i) => i !== index))} className="text-error"><Trash2 /></button></div>)}
            </div>
            <button onClick={() => setMembersList([...membersList, members[3]])} className="mt-4 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-dashed border-kola-500 text-kola-600"><Plus size={18} /> Add another member</button>
            <p className="mt-3 text-sm text-ink-500">{membersList.length} members added · Minimum 2 required</p>
          </Card>
          <Card className="relative p-6">
            <h2 className="font-dm-serif text-2xl">Review & Create</h2>
            <div className="mt-4 border-l-4 border-kola-500 bg-kola-50 p-4 text-sm text-kola-800">Group: Mile 12 Tomato Traders<br />Weekly contribution: N5,000 every Friday<br />Members: {membersList.length} people<br />Backend: Squad VA generation via KOLA API</div>
            <label className="mt-5 flex gap-3 text-sm text-ink-600"><input type="checkbox" /> I confirm all member details are correct and I have their consent.</label>
            {createError ? <div className="mt-4 border-l-4 border-error bg-red-50 p-4 text-sm text-error">{createError}</div> : null}
            <Button full className="mt-5" onClick={handleCreateGroup} disabled={isCreating}>{isCreating ? <LoadingDots /> : "Create Group & Generate Accounts"}</Button>
            {createdGroup ? <SuccessOverlay group={createdGroup} /> : null}
          </Card>
        </div>
      </section>
    </main>
  );
}

function SuccessOverlay({ group }: { group: KolaGroup }) {
  return (
    <div className="absolute inset-0 z-10 rounded-2xl bg-white/95 p-6 backdrop-blur">
      <CheckCircle2 className="mx-auto h-16 w-16 text-kola-500" />
      <h3 className="mt-3 text-center font-dm-serif text-3xl">Group created successfully</h3>
      <p className="mt-2 text-center text-sm text-ink-500">KOLA backend returned {group.members.length} Squad virtual accounts.</p>
      <table className="mt-6 w-full text-sm"><tbody>{group.members.map((member) => <CopyRow key={member.id} member={member} />)}</tbody></table>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row"><Button href="/group/mile-12/feed" full>View Group Dashboard</Button><Button variant="ghost" full>Share Account Numbers</Button></div>
    </div>
  );
}

function CopyRow({ member }: { member: KolaGroup["members"][number] }) {
  const account = member.squad_va_number ?? "Pending";
  const { copied, copy } = useClipboard(account);
  return <tr className="border-b border-ink-100"><td className="py-2">{member.full_name}</td><td className="font-mono">{account}</td><td><button aria-label={`Copy ${member.full_name} account number`} onClick={copy}>{copied ? <Check size={16} /> : <Clipboard size={16} />}</button></td></tr>;
}

function DashboardShell({ children, title = "Contribution Feed" }: { children: React.ReactNode; title?: string }) {
  return (
    <main className="app-surface min-h-screen lg:grid lg:grid-cols-[280px_1fr]">
      <aside className="hidden border-r border-white/10 bg-kola-950/95 p-6 text-white shadow-glow lg:flex lg:flex-col">
        <Logo />
        <p className="mt-10 text-sm text-white/50">Mile 12 Tomato Traders</p>
        <div className="mt-4 rounded-xl border border-kola-300/20 bg-white/[0.06] p-4">
          <div className="flex items-center gap-2 text-sm text-kola-200"><Radio size={16} /> Live backend sync</div>
          <p className="mt-2 text-xs text-white/45">Events, scores, and virtual accounts are read through KOLA API proxies.</p>
        </div>
        <nav className="mt-6 grid gap-2 text-white/70">{["Overview","Members","Contributions","Payouts","Settings"].map((item) => <Link key={item} className="rounded-lg px-3 py-2 hover:bg-white/10" href="/group/mile-12/feed">{item}</Link>)}</nav>
        <div className="mt-auto flex items-center gap-3 text-sm text-white/70"><span className="grid h-9 w-9 place-items-center rounded-full bg-kola-500">A</span>Aminat · Sign out</div>
      </aside>
      <section className="px-4 py-8 sm:px-6 lg:px-10">
        <p className="text-sm text-ink-500">Groups / Mile 12 Tomato Traders / Contributions</p>
        <h1 className="mt-2 font-dm-serif text-4xl">{title}</h1>
        {children}
      </section>
    </main>
  );
}

export function FeedPage() {
  const live = useSSE("/api/events");
  const [scoreData, setScoreData] = useState<KolaScore | null>(null);
  const [scoreError, setScoreError] = useState<string | null>(null);

 useEffect(() => {
    Promise.allSettled([fetchAminatAiScore(), fetchAminatScore()])
      .then(([aiResult, backendResult]) => {
        const ai = aiResult.status === "fulfilled" ? aiResult.value : null;
        const backend = backendResult.status === "fulfilled" ? backendResult.value : null;

        if (ai) {
          setScoreData({
            ...ai,
            events: backend?.events ?? [],
            verified_events_count: backend?.verified_events_count ?? ai.verified_events_count,
            streak_weeks: backend?.streak_weeks,
            last_updated: backend?.last_updated,
          });
          setScoreError(null);
        } else if (backend) {
          setScoreData(backend);
          setScoreError(null);
        } else {
          setScoreError("Unable to reach both AI and backend APIs.");
        }
      });
  }, []);

  const allEvents = [...live.events.map((e) => ({ ...e, tone: "success" as const })), ...events];
  return (
    <DashboardShell>
      <div className="mt-8 grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
        <Card className="overflow-hidden p-6"><div className="grid gap-6 lg:grid-cols-[1fr_280px]"><div><h2 className="font-dm-serif text-2xl">Aminat Ibrahim</h2><p className="text-ink-500">+234 803 XXX XXXX</p><div className="mt-6"><ScoreDisplay compact value={scoreData?.score ?? 714} confidence={scoreData?.confidence ?? "Loading live score"} /></div></div><AiActivityPanel scoreData={scoreData} /></div></Card>
        <Card className="p-6" role="status"><div className="flex items-center justify-between"><div><h2 className="font-dm-serif text-2xl">Live Contribution Events</h2><p className="text-sm text-ink-500">{live.isConnected ? "Connected · Squad-verified" : live.error ?? "Reconnecting"}</p></div><span className={`h-3 w-3 rounded-full ${live.isConnected ? "animate-pulse bg-kola-500" : "bg-amber-400"}`} /></div><div className="mt-5 grid gap-3">{allEvents.map((event) => <EventCard key={event.title + event.meta} event={event} />)}</div></Card>
      </div>
      {scoreError ? <div className="mt-6"><BackendErrorBanner message={scoreError} /></div> : null}
      <Card className="mt-6 overflow-x-auto p-6"><h2 className="font-dm-serif text-2xl">Members</h2><table className="mt-4 w-full min-w-[680px] text-left text-sm"><thead className="text-ink-500"><tr><th>Member</th><th>Account Number</th><th>Contributions</th><th>KOLA Score</th><th>Status</th></tr></thead><tbody>{members.map((m, index) => <tr key={m.account} className="border-t border-ink-100 hover:bg-kola-50"><td className="py-3">{m.name}</td><td className="font-mono">{m.account}</td><td>{index === 0 ? scoreData?.verified_events_count ?? 12 : 12}</td><td>{index === 0 ? scoreData?.score ?? m.score : m.score}</td><td>{index === 0 ? scoreData?.confidence ?? m.status : m.status}</td></tr>)}</tbody></table></Card>
    </DashboardShell>
  );
}

function EventCard({ event }: { event: { title: string; amount: string; meta: string; tone: "success" | "warning" | "info" } }) {
  const color = event.tone === "success" ? "border-kola-400" : event.tone === "warning" ? "border-amber-400" : "border-info";
  return <motion.div layout initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} className={`rounded-xl border bg-white/90 p-4 shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:shadow-green ${color} border-l-4`}><div className="flex justify-between gap-3"><h3 className="font-semibold">{event.title}</h3><span className="font-mono">{event.amount}</span></div><p className="mt-1 text-sm text-ink-500">{event.meta}</p><Badge>Squad verified</Badge></motion.div>;
}

export function ScorePage() {
  const [scoreData, setScoreData] = useState<KolaScore | null>(null);
  const [scoreError, setScoreError] = useState<string | null>(null);

useEffect(() => {
    Promise.allSettled([fetchAminatAiScore(), fetchAminatScore()])
      .then(([aiResult, backendResult]) => {
        const ai = aiResult.status === "fulfilled" ? aiResult.value : null;
        const backend = backendResult.status === "fulfilled" ? backendResult.value : null;

        if (ai) {
          setScoreData({
            ...ai,
            events: backend?.events ?? [],
            verified_events_count: backend?.verified_events_count ?? ai.verified_events_count,
            streak_weeks: backend?.streak_weeks,
            last_updated: backend?.last_updated,
          });
          setScoreError(null);
        } else if (backend) {
          setScoreData(backend);
          setScoreError(null);
        } else {
          setScoreError("Unable to reach both AI and backend APIs.");
        }
      });
  }, []);
  if (scoreData === null) {
    return (
      <main>
        <section className="hero-grid grain px-4 py-24 text-white sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl"><Link href="/group/mile-12/feed" className="text-white/60">Groups / Mile 12 / Aminat Ibrahim</Link><div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]"><div><h1 className="font-fraunces text-6xl">Aminat Ibrahim</h1><p className="mt-4 text-white/60">Member since March 2024 · 20-member Ajo group</p></div><div className="rounded-2xl border border-kola-400/30 bg-kola-950 p-6 text-white shadow-glow"><div className="h-4 w-24 animate-pulse rounded bg-white/20" /><div className="mt-4 h-16 w-44 animate-pulse rounded bg-white/20" /><div className="mt-4 h-7 w-32 animate-pulse rounded-full bg-kola-400/30" /><div className="mt-8 h-3 animate-pulse rounded-full bg-white/20" /></div></div></div>
        </section>
        <section className="px-4 py-10 sm:px-6 lg:px-8"><div className="mx-auto grid max-w-6xl gap-6">{scoreError ? <BackendErrorBanner message={scoreError} /> : null}<div className="grid gap-4 sm:grid-cols-3">{[["--","Squad-verified events"],["--","Current streak"],["Live","Backend status"]].map(([n,l]) => <Card key={l} className="p-6"><div className="font-mono text-3xl text-kola-600">{n}</div><p className="text-ink-500">{l}</p></Card>)}</div><Card className="p-6"><div className="h-8 w-56 animate-pulse rounded bg-ink-100" /><div className="mt-8 space-y-4">{Array.from({ length: 5 }).map((_, index) => <div key={index} className="grid grid-cols-[150px_1fr_42px] items-center gap-3"><div className="h-4 animate-pulse rounded bg-ink-100" /><div className="h-4 animate-pulse rounded bg-ink-100" /><div className="h-4 animate-pulse rounded bg-ink-100" /></div>)}</div></Card></div></section>
      </main>
    );
  }

  const liveScoreFactors = scoreToFactors(scoreData);
  const verifiedEvents = scoreData.events?.length ? scoreData.events.map(eventFromBackend) : events;
  const positiveLift = liveScoreFactors.reduce((total, factor) => total + Math.max(factor.value, 0), 0);
  const modelCards = [
    ["Model", "Behavioral SHAP v1"],
    ["Signal lift", `+${positiveLift}`],
    ["Decision", scoreData.score >= 700 ? "Pre-qualified" : "Review queue"],
  ];

  return (
    <main className="min-h-screen bg-ink-50">
      <section className="hero-grid grain px-4 py-8 text-white sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
            <Link href="/group/mile-12/feed" className="text-sm text-white/60">Groups / Mile 12 / Aminat Ibrahim</Link>
            <div className="flex flex-wrap gap-2 text-xs text-white/70">
              <span className="rounded-full border border-white/15 px-3 py-1">Squad VA verified</span>
              <span className="rounded-full border border-white/15 px-3 py-1">API decision ready</span>
              <span className="rounded-full border border-white/15 px-3 py-1">Last sync: live</span>
            </div>
          </div>
          {scoreData.anomaly_flag ? <div className="mt-6 border-l-4 border-amber-400 bg-amber-50 p-4 text-sm font-medium text-amber-900">Warning: unusual score activity detected for this member.</div> : null}
          <div className="grid gap-8 py-10 lg:grid-cols-[1fr_380px] lg:items-end">
            <div>
              <Badge dark>Member Credit File</Badge>
              <h1 className="mt-5 font-fraunces text-5xl leading-tight sm:text-6xl">Aminat Ibrahim</h1>
              <p className="mt-4 max-w-2xl text-white/65">Mile 12 Tomato Traders · Member since March 2024 · 20-member Ajo group. Behavioral score generated from verified contribution and trade events.</p>
              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                {modelCards.map(([label, value]) => <div key={label} className="border border-white/10 bg-white/[0.04] p-4"><p className="text-xs uppercase tracking-[0.2em] text-white/40">{label}</p><p className="mt-2 font-mono text-xl text-kola-300">{value}</p></div>)}
              </div>
            </div>
            <div className="grid gap-4">
              <ScoreDisplay compact value={scoreData.score} confidence={scoreData.confidence} />
              <AiActivityPanel scoreData={scoreData} />
            </div>
          </div>
        </div>
      </section>
      <section className="px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto grid max-w-7xl gap-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[[String(scoreData.verified_events_count ?? 0),"Squad-verified events"],[String(scoreData.streak_weeks ?? 0),"Current streak weeks"],[scoreData.last_updated ? new Date(scoreData.last_updated).toLocaleDateString() : "Live","Last model refresh"],[scoreData.confidence,"Confidence label"]].map(([n,l]) => <Card key={l} className="p-5"><div className="font-mono text-2xl text-kola-600">{n}</div><p className="text-sm text-ink-500">{l}</p></Card>)}
          </div>
          <div className="grid gap-6 xl:grid-cols-[1.15fr_.85fr]">
            <Card className="p-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div><h2 className="font-dm-serif text-3xl">Model Explanation</h2><p className="text-ink-500">Each bar shows how a verified signal moved Aminat's score.</p></div>
                <Badge>Explainable AI</Badge>
              </div>
              <div className="mt-8"><ShapBars factors={liveScoreFactors} /></div>
            </Card>
            <Card className="p-6">
              <h2 className="font-dm-serif text-3xl">Credit Decision</h2>
              <div className="mt-5 grid gap-4">
                {[
                  ["Eligibility", scoreData.score >= 700 ? "Approve up to N120,000" : "Manual review"],
                  ["Risk tier", scoreData.confidence],
                  ["Data source", "Squad virtual account events"],
                  ["Controls", "Webhook HMAC + API key"],
                ].map(([label, value]) => <div key={label} className="flex items-center justify-between border-b border-ink-100 pb-3 text-sm"><span className="text-ink-500">{label}</span><span className="font-semibold text-ink-800">{value}</span></div>)}
              </div>
              <Button href="/lender/query" className="mt-6" full>Open Lender Query <ArrowRight size={18} /></Button>
            </Card>
          </div>
          <Card className="p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div><h2 className="font-dm-serif text-3xl">Verified Event History</h2><p className="text-ink-500">A Squad-backed audit trail for underwriting and monitoring.</p></div>
              <div className="flex items-center gap-2 text-sm text-kola-700"><ShieldCheck size={18} /> Verified stream</div>
            </div>
            <div className="relative mt-6 border-l-2 border-kola-200 pl-6">{verifiedEvents.map((event) => <div key={event.title + event.meta} className="mb-6 grid gap-2 sm:grid-cols-[1fr_auto]"><span className="absolute -left-[9px] h-4 w-4 rounded-full bg-kola-500" /><div><h3 className="font-semibold">{event.title} · {event.amount}</h3><p className="text-sm text-ink-500">{event.meta}</p></div><Badge>{event.tone === "warning" ? "Review" : "Verified"}</Badge></div>)}</div>
          </Card>
        </div>
      </section>
    </main>
  );
}

export function LenderDashboard({ queryOnly = false }: { queryOnly?: boolean }) {
  const [queried, setQueried] = useState(false);
  const [approved, setApproved] = useState(false);
  const [query, setQuery] = useState("08012345678");
  const [queryResult, setQueryResult] = useState<KolaScore | null>(null);
  const [querying, setQuerying] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const chartData = useMemo(() => Array.from({ length: 12 }, (_, i) => ({ name: `W${i + 1}`, score: 620 + i * 8 + (i % 3) * 12 })), []);

  async function handleQueryScore() {
    setQueried(true);
    setApproved(false);
    setQuerying(true);
    setQueryError(null);
    try {
      setQueryResult(await fetchTraderScore(query));
    } catch (error) {
      setQueryError(error instanceof Error ? error.message : "Unable to query score");
    } finally {
      setQuerying(false);
    }
  }

  useEffect(() => {
    if (queryOnly && !queryResult && !querying) {
      handleQueryScore();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryOnly]);

  return (
    <main className="app-surface min-h-screen lg:grid lg:grid-cols-[280px_1fr]">
      <aside className="hidden bg-ink-950 p-6 text-white lg:block"><Logo /><p className="mt-8 text-sm text-white/60">KOLA · Lender Portal</p><div className="mt-5 rounded-xl border border-white/10 bg-white/[0.06] p-4"><div className="flex items-center gap-2 text-sm text-kola-200"><Cpu size={16} /> Model endpoint online</div><p className="mt-2 text-xs text-white/45">Queries run through the Next proxy into FastAPI.</p></div><nav className="mt-8 grid gap-2 text-white/70">{["Dashboard","Query Score","Recent Queries","API Keys","Settings"].map((n) => <Link href="/lender/dashboard" key={n} className="rounded-lg px-3 py-2 hover:bg-white/10">{n}</Link>)}</nav></aside>
      <section className="p-4 sm:p-6 lg:p-10">
        <p className="text-sm text-ink-500">Good morning, GTBank MFB.</p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{lenderStats.map(([n,l]) => <Card key={l} className="p-5"><div className="font-mono text-3xl text-kola-600">{n}</div><p className="text-sm text-ink-500">{l}</p></Card>)}</div>
        <Card className="mt-6 p-6"><h1 className="font-dm-serif text-4xl">Query a KOLA Score</h1><div className="mt-5 flex flex-col gap-3 sm:flex-row"><div className="relative flex-1"><Search className="absolute left-4 top-3.5 text-ink-400" size={18} /><input className="min-h-12 w-full rounded-md border border-ink-200 pl-11" placeholder="Trader phone number or KOLA ID" value={query} onChange={(event) => setQuery(event.target.value)} /></div><Button onClick={handleQueryScore} disabled={querying}>{querying ? <LoadingDots /> : "Query Score"}</Button></div>{queryError ? <div className="mt-4 border-l-4 border-error bg-red-50 p-4 text-sm text-error">{queryError}</div> : null}{queryOnly || queried ? <div className="mt-6 section-reveal"><ResultCard scoreData={queryResult} approved={approved} onApprove={() => setApproved(true)} /></div> : null}</Card>
        <Card className="mt-6 p-6"><h2 className="font-dm-serif text-3xl">Portfolio score trend</h2><div className="h-72"><ResponsiveContainer><AreaChart data={chartData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Area type="monotone" dataKey="score" stroke="#1f8450" fill="#c5eed8" /></AreaChart></ResponsiveContainer></div></Card>
      </section>
    </main>
  );
}

function ResultCard({ scoreData, approved, onApprove }: { scoreData: KolaScore | null; approved: boolean; onApprove: () => void }) {
  const currentScore = scoreData?.score ?? 714;
  const decision = currentScore >= 700 ? "Approve N120,000 · 90 days" : "Send to manual review";
  const signals = scoreData
    ? scoreToFactors(scoreData).filter((factor) => factor.value > 0).map((factor) => `${factor.name}: +${factor.value}`)
    : approvalSignals;

  return (
    <Card className="relative overflow-hidden p-6">
      <div className="grid gap-6 lg:grid-cols-[1fr_260px]"><div><h2 className="font-dm-serif text-3xl">Aminat Ibrahim</h2><p className="text-ink-500">+234 803 XXX XXXX · Mile 12 Tomato Traders</p><ul className="mt-5 grid gap-2">{signals.slice(0, 3).map((s) => <li key={s} className="flex gap-2 text-sm text-ink-700"><CheckCircle2 className="text-kola-500" size={18} />{s}</li>)}</ul><div className="mt-6 grid gap-3 sm:grid-cols-3"><Input label="Amount (N)" defaultValue="120,000" /><Input label="Tenor (days)" defaultValue="90" /><Input label="Interest rate (%)" defaultValue="3.5" /></div><Button className="mt-5" onClick={onApprove}>{decision}</Button></div><ScoreDisplay compact value={currentScore} confidence={scoreData?.confidence ?? "Awaiting live query"} /></div>
      {approved ? <div className="absolute inset-0 grid place-items-center bg-white/95 p-8 text-center backdrop-blur"><div><CheckCircle2 className="mx-auto h-20 w-20 text-kola-500" /><h3 className="mt-4 font-fraunces text-5xl text-kola-600">{currentScore >= 700 ? "N120,000" : "Review"}</h3><p className="mt-2 text-ink-600">Decision generated from live KOLA score · Ref: KOLA-{new Date().getFullYear()}-{currentScore}</p><div className="mt-6 flex flex-col gap-3 sm:flex-row"><Button>Download approval letter</Button><Button variant="ghost">Make another query</Button></div></div></div> : null}
    </Card>
  );
}

export function NotFoundPage() {
  return (
    <main className="hero-grid grain grid min-h-screen place-items-center px-4 text-center text-white">
      <div><div className="font-mono text-9xl text-kola-200/20">404</div><h1 className="mt-4 font-fraunces text-5xl italic">This page has no credit history.</h1><p className="mx-auto mt-5 max-w-xl text-white/65">Like Aminat before KOLA, this page is invisible to us. But she found her score, and you'll find your way back.</p><Button href="/" className="mt-8">Return to KOLA <ArrowRight size={18} /></Button></div>
    </main>
  );
}
