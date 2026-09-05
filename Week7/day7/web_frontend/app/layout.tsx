import type { Metadata } from "next";
import "./globals.css";
import { SessionProvider } from "@/components/SessionProvider";
import { Shell } from "@/components/Shell";

export const metadata: Metadata = { title: "Sara Real Estate", description: "Verified real-estate discovery" };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body><SessionProvider><Shell>{children}</Shell></SessionProvider></body></html>; }
