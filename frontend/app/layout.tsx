import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AutoCare AI — Virtual Mechanic",
  description: "AI-assisted car troubleshooting and mechanic booking"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
