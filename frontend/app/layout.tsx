import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Diasift",
  description: "Type 2 Diabetes guideline assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
