"use client";

import Link from "next/link";
import { useState } from "react";
import { Landmark, Menu, Sprout, X } from "lucide-react";

const links = [
  ["About", "/about"],
  ["How It Works", "/how-it-works"],
  ["FAQs", "/faqs"],
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="site-header">
      <div className="nav-inner">
        <Link className="brand" href="/" aria-label="UPSC Copy Checker home">
          <span className="brand-mark">
            <Landmark size={37} strokeWidth={1.3} />
          </span>
          <span className="brand-copy">
            <strong>UPSC Copy Checker</strong>
            <small>Practice Smarter. Write Better. Go Further.</small>
          </span>
        </Link>
        <button
          className="mobile-menu-button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? <X size={21} /> : <Menu size={21} />}
        </button>
        <nav
          className={open ? "main-nav is-open" : "main-nav"}
          aria-label="Main navigation"
        >
          {links.map(([label, href]) => (
            <Link key={href} href={href} onClick={() => setOpen(false)}>
              {label}
            </Link>
          ))}
          <Link
            className="nav-cta"
            href="/#upload"
            onClick={() => setOpen(false)}
          >
            <Sprout size={20} strokeWidth={1.5} /> For a Stronger You
          </Link>
        </nav>
      </div>
    </header>
  );
}
