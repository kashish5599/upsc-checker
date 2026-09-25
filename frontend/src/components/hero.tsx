import { BarChart3, BookOpen, Target } from "lucide-react";
import HeroIllustration from "./hero-illustration";

const benefits = [
  { label: "Structured Feedback", Icon: BarChart3 },
  { label: "UPSC-Focused Insights", Icon: BookOpen },
  { label: "Improve with Every Attempt", Icon: Target },
];

export default function Hero() {
  return (
    <section className="hero-section">
      <div className="hero-inner">
        <div className="hero-copy">
          <h1>
            Get expert-like feedback
            <br className="desktop-break" /> on your UPSC answers
          </h1>
          <p>
            Upload your handwritten answer copy, add reference material
            (optional), and get a detailed, structured evaluation powered by AI
            — tailored for UPSC standards.
          </p>
          <div className="hero-benefits">
            {benefits.map(({ label, Icon }) => (
              <div className="benefit" key={label}>
                <span>
                  <Icon size={18} strokeWidth={1.7} />
                </span>
                {label}
              </div>
            ))}
          </div>
        </div>
        <HeroIllustration />
      </div>
    </section>
  );
}
