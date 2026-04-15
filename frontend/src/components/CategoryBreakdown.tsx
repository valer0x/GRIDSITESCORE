import type { CategoryBreakdown as Category } from "../api/types";
import { CategoryIcon } from "./Icons";

function scoreColor(score: number): string {
  if (score >= 75) return "#10b981";
  if (score >= 50) return "#f59e0b";
  if (score >= 25) return "#f97316";
  return "#ef4444";
}

function prettyName(n: string): string {
  return n.replace("_", " ");
}

export default function CategoryBreakdown({ category }: { category: Category }) {
  const pct = Math.round(category.score_0_100);
  const color = scoreColor(pct);
  const Icon = CategoryIcon[category.name];

  return (
    <details className="category">
      <summary>
        <div className="category-head">
          <div className="category-title">
            <span className="category-icon" style={{ color }}>
              {Icon ? <Icon size={16} /> : null}
            </span>
            <span className="category-name">{prettyName(category.name)}</span>
            <span className="category-weight">{(category.weight * 100).toFixed(0)}%</span>
          </div>
          <div className="category-score-wrap">
            <span className="category-score" style={{ color }}>
              {pct}
            </span>
            <span className="category-score-suffix">/100</span>
          </div>
        </div>
        <div className="bar">
          <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
        </div>
      </summary>
      <ul className="rule-list">
        {category.rules.map((r) => {
          const rulePct = Math.round(r.normalized_score * 100);
          const ruleColor = scoreColor(rulePct);
          return (
            <li key={r.name} className="rule">
              <div className="rule-label">
                <span className="rule-label-text">{r.label}</span>
                <span className="rule-score" style={{ color: ruleColor }}>
                  {rulePct}
                </span>
              </div>
              <div className="rule-bar">
                <div
                  className="rule-bar-fill"
                  style={{ width: `${rulePct}%`, background: ruleColor }}
                />
              </div>
              <div className="rule-reason">{r.reason}</div>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
