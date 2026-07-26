import type { Metadata } from 'next'
import './globals.css'
import Nav from '@/components/Nav'

export const metadata: Metadata = {
  title: 'UFC Edge — ML Betting Intelligence',
  description: 'Walk-forward XGBoost model tracking UFC fight predictions since 2021. 13.8% ROI over 506 bets.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#f4ead6] text-[#0a0a0c] antialiased">
        <Nav />
        <main>{children}</main>
      </body>
    </html>
  )
}
