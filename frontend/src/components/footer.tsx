import Link from "next/link";

const links = [
  ["About", "/about"],
  ["Privacy", "/privacy"],
  ["Terms", "/terms"],
  ["Contact", "/contact"],
];

export default function Footer() {
  return (
    <footer className="site-footer">
      <div>
        <strong>UPSC Copy Checker</strong>
        <small>Built for serious aspirants.</small>
      </div>
      <nav aria-label="Footer navigation">
        {links.map(([label, href]) => (
          <Link key={href} href={href}>
            {label}
          </Link>
        ))}
      </nav>
    </footer>
  );
}
