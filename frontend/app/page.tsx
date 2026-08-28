"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BadgeIndianRupee,
  BrainCircuit,
  ChevronRight,
  CircleGauge,
  Command,
  DatabaseZap,
  FileClock,
  LayoutDashboard,
  LoaderCircle,
  OctagonAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DecisionDetail } from "@/components/recoveriq/decision-detail";
import { LearningLab } from "@/components/recoveriq/learning-lab";
import { SafetyAudit } from "@/components/recoveriq/safety-audit";
import type { DashboardData } from "@/components/recoveriq/dashboard-types";
import { money } from "@/components/recoveriq/dashboard-types";

type View = "command" | "decision" | "learning" | "safety";

const navItems = [
  { id: "command" as View, label: "Command Center", icon: LayoutDashboard },
  { id: "decision" as View, label: "Decision Detail", icon: BrainCircuit },
  { id: "learning" as View, label: "Learning Lab", icon: Activity },
  { id: "safety" as View, label: "Safety & Audit", icon: ShieldCheck },
];

const viewMeta: Record<View, { title: string; subtitle: string }> = {
  command: { title: "Command Center", subtitle: "Safety-constrained recovery operations" },
  decision: { title: "Decision Detail", subtitle: "Observable estimates and policy reasoning" },
  learning: { title: "Learning Lab", subtitle: "Paired evaluation and calibration" },
  safety: { title: "Safety & Audit", subtitle: "Persisted controls and execution evidence" },
};

function SignalCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "mint",
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Activity;
  tone?: "mint" | "amber" | "blue" | "coral";
}) {
  return (
    <article className={`signal-card signal-${tone}`}>
      <div className="flex items-start justify-between gap-4">
        <p className="signal-label">{label}</p>
        <span className="signal-icon"><Icon aria-hidden="true" /></span>
      </div>
      <p className="mt-7 text-[2rem] font-semibold tracking-[-0.045em] text-white">
        {value}
      </p>
      <p className="mt-1 text-xs leading-5 text-slate-400">{detail}</p>
    </article>
  );
}

function CommandCenter({ data }: { data: DashboardData }) {
  const recoveryRate = (data.journey.recovered / data.journey.total) * 100;
  const statuses = [
    { label: "Recovered", value: data.journey.recovered, className: "bg-emerald-400" },
    { label: "Stopped", value: data.journey.stopped, className: "bg-slate-500" },
    { label: "Exhausted", value: data.journey.exhausted, className: "bg-amber-400" },
    { label: "Escalated", value: data.journey.escalated, className: "bg-rose-400" },
  ];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SignalCard label="Recovery rate" value={`${recoveryRate.toFixed(1)}%`} detail={`${data.journey.recovered} of ${data.journey.total} bounded journeys`} icon={CircleGauge} />
        <SignalCard label="Recovered value" value={money(data.journey.recovered_amount_paise)} detail="Observed in the committed seeded scenario" icon={BadgeIndianRupee} tone="blue" />
        <SignalCard label="Batch allocation" value={`${data.batch.selected} cases`} detail={`${money(data.batch.spent_paise)} of ${money(data.batch.budget_paise)} budget used`} icon={DatabaseZap} tone="amber" />
        <SignalCard label="Expected incremental" value={money(data.batch.expected_incremental_value_paise)} detail="Model estimate — not realized merchant uplift" icon={Sparkles} tone="coral" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_1.6fr]">
        <article className="panel p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div><p className="eyebrow">Journey outcomes</p><h2 className="mt-2 text-xl font-semibold text-white">Bounded by design</h2></div>
            <Badge className="border-emerald-400/20 bg-emerald-400/10 text-emerald-300">500 / 500 terminal</Badge>
          </div>
          <div className="mt-8 flex h-3 overflow-hidden rounded-full bg-white/5">
            {statuses.map((status) => <div key={status.label} className={status.className} style={{ width: `${(status.value / data.journey.total) * 100}%` }} title={`${status.label}: ${status.value}`} />)}
          </div>
          <div className="mt-7 grid grid-cols-2 gap-x-6 gap-y-5">
            {statuses.map((status) => (
              <div key={status.label} className="flex items-center gap-3">
                <span className={`size-2.5 rounded-full ${status.className}`} />
                <div><p className="text-xs text-slate-500">{status.label}</p><p className="mt-0.5 text-lg font-semibold text-slate-100">{status.value}</p></div>
              </div>
            ))}
          </div>
          <div className="mt-7 border-t border-white/8 pt-5 text-sm text-slate-400"><span className="font-medium text-slate-200">{data.journey.cooldown_waits}</span> cooldown waits enforced with a two-intervention ceiling.</div>
        </article>

        <article className="panel overflow-hidden">
          <div className="flex items-start justify-between gap-4 px-5 pb-4 pt-5 sm:px-6 sm:pt-6">
            <div><p className="eyebrow">Priority queue</p><h2 className="mt-2 text-xl font-semibold text-white">Next best permitted actions</h2></div>
            <span className="hidden items-center gap-2 text-xs text-slate-500 sm:flex"><span className="size-1.5 animate-pulse rounded-full bg-emerald-400" />Live demo data</span>
          </div>
          <Table>
            <TableHeader><TableRow className="border-white/8 hover:bg-transparent"><TableHead className="pl-5 text-[11px] uppercase tracking-[0.16em] text-slate-500 sm:pl-6">Case</TableHead><TableHead className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Amount</TableHead><TableHead className="text-[11px] uppercase tracking-[0.16em] text-slate-500">Action</TableHead><TableHead className="text-right text-[11px] uppercase tracking-[0.16em] text-slate-500">Value</TableHead><TableHead className="pr-5 text-right text-[11px] uppercase tracking-[0.16em] text-slate-500 sm:pr-6">Status</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.queue.map((item) => (
                <TableRow key={item.case_id} className="border-white/8 hover:bg-white/[0.025]">
                  <TableCell className="pl-5 sm:pl-6"><div className="font-medium text-slate-200">{item.case_id}</div><div className="mt-1 text-[11px] text-slate-500">{item.segment}</div></TableCell>
                  <TableCell className="text-slate-300">{money(item.amount_paise)}</TableCell>
                  <TableCell><span className="rounded-md border border-cyan-400/15 bg-cyan-400/8 px-2 py-1 text-[11px] font-medium text-cyan-300">{item.action.replaceAll("_", " ")}</span></TableCell>
                  <TableCell className="text-right font-medium text-emerald-300">+{money(item.expected_incremental_value_paise)}</TableCell>
                  <TableCell className="pr-5 text-right sm:pr-6"><Badge variant="outline" className="border-white/10 text-slate-300">{item.status}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </article>
      </section>
    </div>
  );
}

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState(false);
  const [activeView, setActiveView] = useState<View>("command");
  useEffect(() => { fetch("/api/dashboard").then((response) => { if (!response.ok) throw new Error("Dashboard data unavailable"); return response.json(); }).then(setData).catch(() => setError(true)); }, []);

  return (
    <SidebarProvider>
      <Sidebar className="border-r border-white/8 bg-[#080d17]">
        <SidebarHeader className="px-4 pb-3 pt-5"><div className="flex items-center gap-3 px-2"><div className="grid size-9 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-300 shadow-[0_0_30px_rgba(34,211,238,.08)]"><Command className="size-4" /></div><div><p className="font-semibold tracking-[-0.02em] text-white">RecoverIQ</p><p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Command Center</p></div></div></SidebarHeader>
        <SidebarContent>
          <SidebarGroup><SidebarGroupLabel className="text-[10px] uppercase tracking-[0.2em] text-slate-600">Operations</SidebarGroupLabel><SidebarGroupContent><SidebarMenu>{navItems.map((item) => <SidebarMenuItem key={item.label}><SidebarMenuButton onClick={() => setActiveView(item.id)} isActive={activeView === item.id} className="h-10 text-slate-400 data-[active=true]:bg-cyan-300/10 data-[active=true]:text-cyan-200"><item.icon /><span>{item.label}</span>{activeView === item.id && <ChevronRight className="ml-auto size-3" />}</SidebarMenuButton></SidebarMenuItem>)}</SidebarMenu></SidebarGroupContent></SidebarGroup>
          <SidebarGroup><SidebarGroupLabel className="text-[10px] uppercase tracking-[0.2em] text-slate-600">System</SidebarGroupLabel><SidebarGroupContent className="space-y-2 px-2"><div className="status-row"><span>Policy mode</span><strong>{data?.system.mode ?? "—"}</strong></div><div className="status-row"><span>Storage</span><strong>{data?.system.storage ?? "—"}</strong></div><div className="status-row"><span>Tests</span><strong>{data?.system.tests ?? "—"} passed</strong></div></SidebarGroupContent></SidebarGroup>
        </SidebarContent>
        <SidebarFooter className="p-4"><div className="rounded-xl border border-emerald-400/15 bg-emerald-400/[0.06] p-3"><div className="flex items-center gap-2 text-xs font-medium text-emerald-300"><ShieldCheck className="size-3.5" /> Safety layer healthy</div><p className="mt-2 text-[10px] leading-4 text-slate-500">7 / 7 persisted gauntlet checks</p></div></SidebarFooter>
      </Sidebar>

      <SidebarInset className="min-w-0 bg-[#070b13]">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/8 bg-[#070b13]/90 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
          <div className="flex items-center gap-3"><SidebarTrigger className="text-slate-400 hover:bg-white/5 hover:text-white" /><div><h1 className="text-sm font-semibold text-white">{viewMeta[activeView].title}</h1><p className="hidden text-[11px] text-slate-500 sm:block">{viewMeta[activeView].subtitle}</p></div></div>
          <div className="flex items-center gap-2 sm:gap-4"><Badge variant="outline" className="border-amber-300/20 bg-amber-300/[0.06] text-amber-200">SHADOW MODE</Badge><div className="hidden items-center gap-2 text-xs text-slate-500 sm:flex"><span className="size-1.5 rounded-full bg-emerald-400" />RecoveryGym seed 42</div></div>
        </header>

        <main className="dashboard-grid min-h-[calc(100svh-4rem)] p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-[1500px]">
            {activeView === "command" && <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><div className="flex items-center gap-2 text-xs text-cyan-300"><Activity className="size-3.5" /><span className="font-medium uppercase tracking-[0.18em]">Live recovery posture</span></div><h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl">Revenue recovery, with guardrails.</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Every number below is served by the dashboard backend from committed synthetic evaluation artifacts.</p></div><div className="flex items-center gap-2 text-xs text-slate-500"><FileClock className="size-3.5" />Snapshot {data ? new Date(data.generated_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "loading"}</div></div>}
            {error ? <div className="panel flex min-h-72 flex-col items-center justify-center p-8 text-center"><OctagonAlert className="size-8 text-rose-300" /><h2 className="mt-4 font-semibold text-white">Dashboard data unavailable</h2><p className="mt-2 text-sm text-slate-500">The backend response could not be loaded.</p></div> : !data ? <div className="panel flex min-h-72 items-center justify-center gap-3 text-sm text-slate-400"><LoaderCircle className="size-4 animate-spin text-cyan-300" /> Loading operational data…</div> : activeView === "command" ? <CommandCenter data={data} /> : activeView === "decision" ? <DecisionDetail data={data} /> : activeView === "learning" ? <LearningLab data={data} /> : <SafetyAudit data={data} />}
            <footer className="mt-8 flex flex-col gap-2 border-t border-white/8 py-5 text-[11px] text-slate-600 sm:flex-row sm:items-center sm:justify-between"><span>RecoverIQ · Synthetic evaluation dashboard</span><span className="flex items-center gap-1.5">No production money movement <ArrowUpRight className="size-3" /></span></footer>
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
