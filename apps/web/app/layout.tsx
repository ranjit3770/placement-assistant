import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Placement Intelligence",
  description: "Your campus placement opportunities, explained clearly.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
