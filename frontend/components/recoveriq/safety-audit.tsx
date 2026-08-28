"use client";

import { CheckCircle2, Database, Fingerprint, LockKeyhole, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DashboardData } from "@/components/recoveriq/dashboard-types";

export function SafetyAudit({ data }: { data: DashboardData }) {
  const safety = data.safety;
  return (
    <div className="space-y-6">
      <section className="safety-banner panel p-5 sm:p-7">
        <div className="relative z-10 flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4"><div className="grid size-14 place-items-center rounded-2xl border border-emerald-300/20 bg-emerald-300/10 text-emerald-300"><ShieldCheck className="size-7" /></div><div><p className="eyebrow">Persisted Safety Gauntlet</p><h2 className="mt-2 text-2xl font-semibold tracking-[-.03em] text-white">All critical paths held.</h2><p className="mt-1 text-sm text-slate-400">Zero real network calls · one controlled fake execution</p></div></div>
          <div className="flex items-baseline gap-2"><strong className="text-5xl font-semibold tracking-[-.06em] text-emerald-300">{safety.passed}/{safety.total}</strong><span className="text-sm text-slate-500">passed</span></div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{safety.scenarios.map((scenario, index) => <article key={scenario.name} className={`gauntlet-card ${index === safety.scenarios.length - 1 ? "xl:col-span-2" : ""}`}><div className="flex items-start justify-between"><span className="grid size-7 place-items-center rounded-lg bg-emerald-400/10 text-emerald-300"><CheckCircle2 className="size-4" /></span><Badge variant="outline" className="border-emerald-400/15 text-emerald-300">{scenario.result}</Badge></div><h3 className="mt-5 text-sm font-medium text-slate-100">{scenario.name}</h3><p className="mt-2 text-xs leading-5 text-slate-500">{scenario.detail}</p></article>)}</section>

      <section className="grid gap-4 xl:grid-cols-[.7fr_1.6fr]">
        <article className="panel p-5 sm:p-6"><div className="flex items-center gap-3"><span className="grid size-9 place-items-center rounded-xl bg-cyan-300/10 text-cyan-300"><Database className="size-4" /></span><div><p className="eyebrow">SQLite ledger</p><h3 className="mt-1 text-lg font-semibold text-white">Persisted evidence</h3></div></div><div className="mt-6 grid grid-cols-2 gap-3">{Object.entries(safety.persistence_counts).map(([label, value]) => <div key={label} className="ledger-count"><span>{label}</span><strong>{value}</strong></div>)}</div><div className="mt-5 flex items-center gap-2 rounded-xl border border-white/8 bg-white/[0.02] p-3 text-[11px] leading-4 text-slate-500"><LockKeyhole className="size-4 shrink-0 text-cyan-300" />BEGIN IMMEDIATE transactions, foreign keys, WAL and database uniqueness.</div></article>

        <article className="panel overflow-hidden"><div className="flex items-center justify-between px-5 py-5 sm:px-6"><div><p className="eyebrow">Immutable decision trace</p><h3 className="mt-2 text-lg font-semibold text-white">Exactly-once execution audit</h3></div><Fingerprint className="size-5 text-indigo-300" /></div><Table><TableHeader><TableRow className="border-white/8 hover:bg-transparent"><TableHead className="pl-5 text-slate-500 sm:pl-6">#</TableHead><TableHead className="text-slate-500">Event</TableHead><TableHead className="text-slate-500">Evidence</TableHead><TableHead className="pr-5 text-right text-slate-500 sm:pr-6">State</TableHead></TableRow></TableHeader><TableBody>{safety.audit.map((entry) => <TableRow key={entry.sequence} className="border-white/8 hover:bg-white/[0.025]"><TableCell className="pl-5 font-mono text-xs text-slate-600 sm:pl-6">{String(entry.sequence).padStart(2, "0")}</TableCell><TableCell className="font-mono text-[11px] font-medium text-cyan-200">{entry.event}</TableCell><TableCell className="max-w-sm whitespace-normal text-xs leading-5 text-slate-400">{entry.detail}</TableCell><TableCell className="pr-5 text-right sm:pr-6"><Badge variant="outline" className="border-white/10 text-slate-300">{entry.status}</Badge></TableCell></TableRow>)}</TableBody></Table></article>
      </section>
    </div>
  );
}
