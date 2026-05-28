import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import IntakeFlow from './pages/IntakeFlow'
import ThankYou from './pages/ThankYou'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/get-started" element={<IntakeFlow />} />
      <Route path="/thank-you" element={<ThankYou />} />
    </Routes>
  )
}
