import { Quote } from "lucide-react";

const steps = [
  {
    title: "Upload",
    detail: "Add your answer copy and (optional) reference material.",
  },
  {
    title: "Analyze",
    detail: "Our AI evaluates your answer against UPSC standards.",
  },
  {
    title: "Get Feedback",
    detail:
      "Receive a detailed evaluation with strengths, weaknesses and suggestions for improvement.",
  },
];

export default function HowItWorks() {
  return (
    <section className="how-card">
      <h2>How it works</h2>
      <ol>
        {steps.map(({ title, detail }, index) => (
          <li key={title}>
            <span className="how-number">{index + 1}</span>
            <span>
              <strong>{title}</strong>
              <small>{detail}</small>
            </span>
          </li>
        ))}
      </ol>
      <blockquote>
        <Quote size={19} aria-hidden="true" />
        <p>
          “Consistent, honest evaluation is the bridge between where you are and
          where you want to be.”
        </p>
        <span className="quote-rule" />
      </blockquote>
    </section>
  );
}
