export type DashboardData = {
  generated_at: string;
  source: { label: string; seed: number; synthetic: boolean };
  system: { mode: string; model: string; storage: string; tests: number };
  journey: {
    total: number;
    recovered: number;
    stopped: number;
    exhausted: number;
    escalated: number;
    cooldown_waits: number;
    recovered_amount_paise: number;
  };
  batch: {
    selected: number;
    candidates: number;
    budget_paise: number;
    spent_paise: number;
    expected_incremental_value_paise: number;
  };
  queue: Array<{
    case_id: string;
    segment: string;
    amount_paise: number;
    action: string;
    expected_incremental_value_paise: number;
    status: string;
  }>;
  decision: {
    case_id: string;
    segment: string;
    amount_paise: number;
    failure_reason: string;
    selected_action: string;
    policy_decision: string;
    policy_reason: string;
    natural_recovery_probability: number;
    selected_action_probability: number;
    probability_uplift: number;
    intervention_cost_paise: number;
    expected_incremental_value_paise: number;
    alternatives: Array<{
      action: string;
      probability: number;
      uplift: number;
      incremental_value_paise: number;
      permitted: boolean;
    }>;
    guardrails: Array<{ label: string; value: string; passed: boolean }>;
    timeline: Array<{ time: string; title: string; detail: string; tone: string }>;
  };
  learning: {
    evaluation_cases: number;
    paired_seeds: number;
    mean_additional_revenue_rupees: number;
    relative_gain_pct: number;
    relative_gain_ci95: { lower: number; upper: number };
    seed_wins: number;
    selected_probability_mae_pct: number;
    natural_probability_mae_pct: number;
    selected_brier_score: number;
    observations_per_action: number;
    actions: string[];
  };
  safety: {
    passed: number;
    total: number;
    scenarios: Array<{ name: string; result: string; detail: string }>;
    persistence_counts: Record<string, number>;
    audit: Array<{
      sequence: number;
      event: string;
      detail: string;
      status: string;
    }>;
  };
};

export const money = (paise: number, decimals = 0) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: decimals,
  }).format(paise / 100);
