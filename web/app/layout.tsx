import type { Metadata } from "next";
import "./globals.css";
import { BootIntro } from "./components/fx/BootIntro";
import { IntelField } from "./components/fx/IntelField";

export const metadata: Metadata = {
  title: "tradecraft — field dossier",
  description:
    "OSINT dossier for cybersecurity interview prep. Recon your future employer.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Special+Elite&family=JetBrains+Mono:wght@400;600&family=IBM+Plex+Serif:wght@400;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <IntelField />
        {children}
        <BootIntro />
      </body>
    </html>
  );
}
