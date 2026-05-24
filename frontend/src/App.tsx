import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import LandingPage from '@/pages/LandingPage'
import IndexPage from '@/pages/IndexPage'
import FlightDetailPage from '@/pages/FlightDetailPage'
import AirportsPage from '@/pages/AirportsPage'
import AlertsPage from '@/pages/AlertsPage'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import WatchlistPage from '@/pages/WatchlistPage'

export default function App() {
  return (
    <Routes>
      {/* Marketing landing page — standalone, no shared layout */}
      <Route path="/" element={<LandingPage />} />

      {/* Auth pages — full-screen, no shared layout */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* App pages — shared layout */}
      <Route element={<Layout />}>
        <Route path="/live" element={<IndexPage />} />
        <Route path="/flight/:ident" element={<FlightDetailPage />} />
        <Route path="/airports" element={<AirportsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
      </Route>
    </Routes>
  )
}
