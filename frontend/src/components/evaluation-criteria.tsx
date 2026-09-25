import {
  BarChart3,
  FileText,
  Layers3,
  Network,
  Star,
  Target,
} from "lucide-react";

//Replace with "How is it different from a normal AI evaluation"
const criteria = [
  {
    title: "Question Understanding",
    detail: "How well you address the demand and context.",
    Icon: Target,
    color: "blue",
  },
  {
    title: "Content and Dimensions",
    detail: "Coverage of relevant points and their depth.",
    Icon: Layers3,
    color: "green",
  },
  {
    title: "Facts, Data and Examples",
    detail: "Use of accurate and relevant facts, data, and examples.",
    Icon: BarChart3,
    color: "gold",
  },
  {
    title: "Structure and Presentation",
    detail: "Logical flow, coherence and readability.",
    Icon: Network,
    color: "violet",
  },
  {
    title: "Introduction and Conclusion",
    detail: "Quality and relevance of your introduction and conclusion.",
    Icon: FileText,
    color: "pink",
  },
  {
    title: "Overall Score",
    detail: "A holistic evaluation with actionable suggestions.",
    Icon: Star,
    color: "teal",
  },
];

export default function EvaluationCriteria() {
  return (
    <section className="criteria-card">
      <h2>What will be evaluated?</h2>
      <ul>
        {criteria.map(({ title, detail, Icon, color }) => (
          <li key={title}>
            <span className={`criteria-icon ${color}`}>
              <Icon size={19} strokeWidth={1.8} />
            </span>
            <span className="criteria-copy">
              <strong>{title}</strong>
              <small>{detail}</small>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
