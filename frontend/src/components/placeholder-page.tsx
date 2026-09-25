import Navbar from "./navbar";
import Footer from "./footer";

export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <>
      <Navbar />
      <main className="placeholder-main">
        <span className="eyebrow">UPSC COPY CHECKER</span>
        <h1>{title}</h1>
        <p>Coming soon.</p>
      </main>
      <Footer />
    </>
  );
}
