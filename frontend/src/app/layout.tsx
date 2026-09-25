import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UPSC Copy Checker | Practice Smarter. Write Better.",
  description:
    "Get structured, UPSC-focused feedback on your handwritten answer copies.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
