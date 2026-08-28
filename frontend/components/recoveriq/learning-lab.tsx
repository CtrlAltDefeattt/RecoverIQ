"use client";

import { Activity, ArrowUp, BrainCircuit, CheckCircle2, Database, Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { DashboardData } from "@/components/recoveriq/dashboard-types";

export function LearningLab({ data }: { data: DashboardData }) {
  const learning = data.learning;
  const intervalWidth = learning.relative_gain_ci95.upper - learning.relative_gain_ci95.lower;
  const intervalLeft = (learning.relative_gain_ci95.lower / 15) * 100;
  const visualWidth = (intervalWidth / 15) * 100;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article className="signal-card signal-mint"><p className="signal-label">Mean gain vs rules</p><p className="mt-7 text-4xl font-semibold tracking-[-.05em] text-emerald-300">+{learning.relative_gain_pct}%</p><p className="mt-2 text-xs text-slate-500">Paired recovered revenue</p></article>
        <article className="signal-card signal-blue"><p className="signal-label">Additional simulated</p><p className="mt-7 text-4xl font-semibold tracking-[-.05em] text-white">₹{(learning.mean_additional_revenue_rupees / 100_000).toFixed(2)}L</p><p className="mt-2 text-xs text-slate-500">Mean across {learning.paired_seeds} paired seeds</p></article>
        <article className="signal-card signal-amber"><p className="signal-label">Seed win rate</p><p className="mt-7 text-4xl font-semibold tracking-[-.05em] text-white">{learning.seed_wins}/{learning.paired_seeds}</p><p className="mt-2 text-xs text-slate-500">No hidden negative seed</p></article>
        <article className="signal-card signal-coral"><p className="signal-label">Selected-action MAE</p><p className="mt-7 text-4xl font-semibold tracking-[-.05em] text-white">{learning.selected_probability_mae_pct}%</p><p className="mt-2 text-xs text-slate-500">Against evaluator-only truth</p></article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.3fr_.8fr]">
        <article className="panel p-5 sm:p-7">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="eyebrow">Paired evaluation</p><h2 className="mt-2 text-xl font-semibold text-white">Confidence, not a cherry-picked seed</h2></div><Badge className="border-emerald-400/20 bg-emerald-400/10 text-emerald-300"><ArrowUp /> INCREMENTAL VALUE AHEAD</Badge></div>
          <div className="mt-10">
            <div className="relative h-16">
              <div className="absolute inset-x-0 top-7 h-px bg-white/10" />
              {[0, 3, 6, 9, 12, 15].map((tick) => <div key={tick} className="absolute top-5" style={{ left: `${(tick / 15) * 100}%` }}><span className="block h-5 w-px bg-white/10" /><span className="mt-2 block -translate-x-1/2 text-[10px] text-slate-600">{tick}%</span></div>)}
              <div className="absolute top-[21px] h-3 rounded-full bg-cyan-300/25" style={{ left: `${intervalLeft}%`, width: `${visualWidth}%` }} />
              <div className="absolute top-[18px] h-5 w-1 rounded-full bg-cyan-300 shadow-[0_0_18px_rgba(103,232,249,.5)]" style={{ left: `${(learning.relative_gain_pct / 15) * 100}%` }} />
            </div>
            <div className="mt-8 grid gap-3 sm:grid-cols-3"><div className="metric-box"><span>95% lower</span><strong>{learning.relative_gain_ci95.lower}%</strong></div><div className="metric-box metric-highlight"><span>Mean gain</span><strong>{learning.relative_gain_pct}%</strong></div><div className="metric-box"><span>95% upper</span><strong>{learning.relative_gain_ci95.upper}%</strong></div></div>
          </div>
          <div className="mt-8 border-t border-white/8 pt-6"><p className="text-xs text-slate-500">Paired seed wins</p><div className="mt-3 grid grid-cols-10 gap-2">{Array.from({ length: learning.paired_seeds }, (_, index) => <div key={index} className="grid aspect-square place-items-center rounded-lg border border-emerald-400/15 bg-emerald-400/[0.06] text-emerald-300"><CheckCircle2 className="size-3.5" /></div>)}</div></div>
        </article>

        <article className="panel p-5 sm:p-7">
          <div className="flex items-center justify-between"><div><p className="eyebrow">Calibration</p><h2 className="mt-2 text-xl font-semibold text-white">Prediction quality</h2></div><Target className="size-5 text-cyan-300" /></div>
          <div className="mt-7 space-y-6"><div><div className="mb-2 flex justify-between text-xs"><span className="text-slate-400">Selected-action MAE</span><strong className="text-slate-200">{learning.selected_probability_mae_pct}%</strong></div><Progress value={learning.selected_probability_mae_pct * 5} className="h-2 bg-white/5 [&>div]:bg-cyan-300" /></div><div><div className="mb-2 flex justify-between text-xs"><span className="text-slate-400">Natural recovery MAE</span><strong className="text-slate-200">{learning.natural_probability_mae_pct}%</strong></div><Progress value={learning.natural_probability_mae_pct * 5} className="h-2 bg-white/5 [&>div]:bg-indigo-300" /></div></div>
          <div className="mt-7 rounded-xl border border-white/8 bg-white/[0.025] p-4"><div className="flex items-center gap-2 text-xs text-slate-400"><Activity className="size-4 text-rose-300" />Selected-outcome Brier score</div><p className="mt-3 text-3xl font-semibold tracking-[-.04em] text-white">{learning.selected_brier_score}</p></div>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <article className="panel p-5 sm:p-7"><div className="flex items-center gap-3"><span className="grid size-9 place-items-center rounded-xl bg-indigo-400/10 text-indigo-300"><BrainCircuit className="size-4" /></span><div><p className="eyebrow">Observable T-learner</p><h3 className="mt-1 text-lg font-semibold text-white">Six response models</h3></div></div><div className="mt-6 grid gap-2 sm:grid-cols-2">{learning.actions.map((action) => <div key={action} className="model-row"><span>{action}</span><strong>{learning.observations_per_action.toLocaleString("en-IN")} obs.</strong></div>)}</div></article>
        <article className="panel p-5 sm:p-7"><div className="flex items-center gap-3"><span className="grid size-9 place-items-center rounded-xl bg-emerald-400/10 text-emerald-300"><Database className="size-4" /></span><div><p className="eyebrow">Learning boundary</p><h3 className="mt-1 text-lg font-semibold text-white">Only what was observed</h3></div></div><div className="mt-6 space-y-3">{["26 observable context features", "One logged action and outcome per case", "Only the executed action model updates online", "No hidden simulator probabilities", "No unselected potential outcomes for training"].map((item) => <div key={item} className="flex items-center gap-3 rounded-xl border border-white/7 bg-white/[0.02] px-4 py-3 text-xs text-slate-300"><CheckCircle2 className="size-4 shrink-0 text-emerald-300" />{item}</div>)}</div></article>
      </section>

      <p className="text-xs leading-5 text-slate-600">Results cover {learning.evaluation_cases.toLocaleString("en-IN")} synthetic evaluation cases. They are engineering evidence, not measured causal uplift for Razorpay merchants.</p>
    </div>
  );
}
