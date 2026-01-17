import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Stock Drop Forensic Analysis',
  description: 'Prepare, Don\'t Predict - A forensic tool for understanding stock price movements',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
