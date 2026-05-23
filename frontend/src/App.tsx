import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import IndexPage from '@/pages/IndexPage'
import FlightDetailPage from '@/pages/FlightDetailPage'
import AirportsPage from '@/pages/AirportsPage'
import AlertsPage from '@/pages/AlertsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<IndexPage />} />
        <Route path="/flight/:ident" element={<FlightDetailPage />} />
        <Route path="/airports" element={<AirportsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
      </Route>
    </Routes>
  )
}
