"use client";

import {
  ArrowRight,
  Check,
  Clock3,
  Gauge,
  IndianRupee,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { DashboardData } from "@/components/recoveriq/dashboard-types";
import { money } from "@/components/recoveriq/dashboard-types";

export function DecisionDetail({ data }: { data: DashboardData }) {
  const decision = data.decision;
  const probabilities = [
    { label: "Natural recovery", value: decision.natural_recovery_probability, color: "[&>div]:bg-slate-500" },
    { label: "Selected action", value: decision.selected_action_probability, color: "[&>div]:bg-cyan-300" },
  ];

  return (
    <div className="space-y-6">
      <section className="panel overflow-hidden">
        <div className="decision-hero p-5 sm:p-7">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-200">{decision.case_id}</Badge>
                <Badge variant="outline" className="border-white/10 text-slate-400">{decision.segment}</Badge>
                <Badge variant="outline" className="border-white/10 text-slate-400">{decision.failure_reason}</Badge>
              </div>
              <p className="mt-7 eyebrow">Recommended intervention</p>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <h2 className="text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl">{decision.selected_action.replaceAll("_", " ")}</h2>
                <ArrowRight className="size-5 text-slate-600" />
                <Badge className="border-emerald-400/20 bg-emerald-400/10 text-emerald-300"><ShieldCheck /> {decision.policy_decision}</Badge>
              </div>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Selected because it has the highest positive expected incremental value among currently permitted actions.</p>
            </div>
            <div className="grid min-w-64 grid-cols-2 gap-3">
              <div className="decision-stat"><IndianRupee /><span>Payment at risk</span><strong>{money(decision.amount_paise)}</strong></div>
              <div className="decision-stat"><Sparkles /><span>Expected value</span><strong className="text-emerald-300">+{money(decision.expected_incremental_value_paise)}</strong></div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.55fr_.85fr]">
        <Tabs defaultValue="explanation" className="panel overflow-hidden">
          <div className="flex flex-col gap-4 border-b border-white/8 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div><p className="eyebrow">Decision intelligence</p><h3 className="mt-2 text-xl font-semibold text-white">Why this action?</h3></div>
            <TabsList className="bg-white/[0.04]"><TabsTrigger value="explanation">Explanation</TabsTrigger><TabsTrigger value="alternatives">Alternatives</TabsTrigger></TabsList>
          </div>
          <TabsContent value="explanation" className="p-5 sm:p-6">
            <div className="grid gap-6 md:grid-cols-[1fr_.9fr]">
              <div className="space-y-6">
                {probabilities.map((item) => (
                  <div key={item.label}>
                    <div className="mb-2 flex items-center justify-between text-sm"><span className="text-slate-400">{item.label}</span><strong className="text-slate-100">{(item.value * 100).toFixed(1)}%</strong></div>
                    <Progress value={item.value * 100} className={`h-2 bg-white/5 ${item.color}`} />
                  </div>
                ))}
                <div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.05] p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-cyan-200"><Gauge className="size-4" /> {(decision.probability_uplift * 100).toFixed(1)} percentage-point uplift</div>
                  <p className="mt-2 text-xs leading-5 text-slate-500">Action probability minus the observable no-action estimate. Hidden simulator probabilities are not inputs.</p>
                </div>
              </div>
              <div className="value-equation">
                <p className="eyebrow">Value equation</p>
                <div className="mt-5 space-y-4 text-sm">
                  <div className="flex justify-between"><span>Recovery probability</span><strong>{(decision.selected_action_probability * 100).toFixed(1)}%</strong></div>
                  <div className="flex justify-between"><span>Payment amount</span><strong>{money(decision.amount_paise)}</strong></div>
                  <div className="flex justify-between"><span>Intervention cost</span><strong>−{money(decision.intervention_cost_paise)}</strong></div>
                  <div className="border-t border-white/8 pt-4"><div className="flex justify-between text-slate-200"><span>Incremental value</span><strong className="text-emerald-300">+{money(decision.expected_incremental_value_paise)}</strong></div></div>
                </div>
              </div>
            </div>
          </TabsContent>
          <TabsContent value="alternatives">
            <Table>
              <TableHeader><TableRow className="border-white/8 hover:bg-transparent"><TableHead className="pl-5 text-slate-500 sm:pl-6">Action</TableHead><TableHead className="text-slate-500">Recovery</TableHead><TableHead className="text-slate-500">Uplift</TableHead><TableHead className="text-right text-slate-500">Incremental value</TableHead><TableHead className="pr-5 text-right text-slate-500 sm:pr-6">Gate</TableHead></TableRow></TableHeader>
              <TableBody>{decision.alternatives.map((item) => <TableRow key={item.action} className="border-white/8 hover:bg-white/[0.025]"><TableCell className="pl-5 font-medium text-slate-200 sm:pl-6">{item.action.replaceAll("_", " ")}</TableCell><TableCell className="text-slate-400">{(item.probability * 100).toFixed(1)}%</TableCell><TableCell className="text-slate-400">{(item.uplift * 100).toFixed(1)} pp</TableCell><TableCell className="text-right text-emerald-300">{item.incremental_value_paise > 0 ? "+" : ""}{money(item.incremental_value_paise)}</TableCell><TableCell className="pr-5 text-right sm:pr-6"><Badge variant="outline" className={item.permitted ? "border-emerald-400/15 text-emerald-300" : "border-rose-400/15 text-rose-300"}>{item.permitted ? "PERMITTED" : "REVIEW"}</Badge></TableCell></TableRow>)}</TableBody>
            </Table>
          </TabsContent>
        </Tabs>

        <article className="panel p-5 sm:p-6">
          <div className="flex items-center justify-between"><div><p className="eyebrow">Policy gate</p><h3 className="mt-2 text-xl font-semibold text-white">Guardrail check</h3></div><LockKeyhole className="size-5 text-emerald-300" /></div>
          <div className="mt-6 space-y-3">{decision.guardrails.map((guardrail) => <div key={guardrail.label} className="guardrail-row"><span className="grid size-6 place-items-center rounded-full bg-emerald-400/10 text-emerald-300"><Check className="size-3.5" /></span><div><p className="text-xs font-medium text-slate-200">{guardrail.label}</p><p className="mt-0.5 text-[11px] text-slate-500">{guardrail.value}</p></div></div>)}</div>
          <div className="mt-6 rounded-xl border border-emerald-400/15 bg-emerald-400/[0.05] p-4 text-xs leading-5 text-slate-400"><strong className="text-emerald-300">{decision.policy_reason}</strong><br />The model proposed; the deterministic safety layer disposed.</div>
        </article>
      </section>

      <section className="panel p-5 sm:p-6">
        <div className="flex items-center gap-2"><Clock3 className="size-4 text-cyan-300" /><div><p className="eyebrow">Decision trace</p><h3 className="mt-1 text-lg font-semibold text-white">Four auditable transitions</h3></div></div>
        <div className="mt-6 grid gap-3 lg:grid-cols-4">{decision.timeline.map((item, index) => <div key={item.time} className="timeline-card"><div className="flex items-center justify-between"><span className={`timeline-dot timeline-${item.tone}`} /><span className="font-mono text-[10px] text-slate-600">{item.time}</span></div><p className="mt-5 text-sm font-medium text-slate-200">{item.title}</p><p className="mt-2 text-xs leading-5 text-slate-500">{item.detail}</p><span className="absolute right-3 top-1/2 text-5xl font-semibold text-white/[0.025]">{index + 1}</span></div>)}</div>
      </section>
    </div>
  );
}
