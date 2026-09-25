import Navbar from "../components/navbar";
import Hero from "../components/hero";
import UploadEvaluate from "../components/upload-evaluate";
import EvaluationCriteria from "../components/evaluation-criteria";
import HowItWorks from "../components/how-it-works";
import Footer from "../components/footer";

export default function Home() {
  return (
    <>
      <Navbar />
      <Hero />
      <main className="evaluation-layout" id="upload">
        <UploadEvaluate />
        <aside className="evaluation-sidebar">
          <EvaluationCriteria />
          <HowItWorks />
        </aside>
      </main>
      <Footer />
    </>
  );
}
