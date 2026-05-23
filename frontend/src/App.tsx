import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import IndexPage from '@/pages/IndexPage'
import FlightDetailPage from '@/pages/FlightDetailPage'
import AirportsPage from '@/pages/AirportsPage'
import AlertsPage from '@/pages/AlertsPage'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'

export default function App() {
  return (
    <Routes>
      {/* Auth pages — full-screen, no shared layout */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* App pages — shared layout */}
      <Route element={<Layout />}>
        <Route path="/" element={<IndexPage />} />
        <Route path="/flight/:ident" element={<FlightDetailPage />} />
        <Route path="/airports" element={<AirportsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
      </Route>
    </Routes>
  )
}
