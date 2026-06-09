import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import IntakeFlow from './pages/IntakeFlow'
import ThankYou from './pages/ThankYou'
import RatesPage from './pages/RatesPage'
import Listings from './pages/Listings'
import DpaHub from './pages/DpaHub'
import Learn from './pages/Learn'
import ProductDetail from './pages/learn/ProductDetail'
import RealtorPartner from './pages/RealtorPartner'
import CampaignPage from './pages/CampaignPage'

export default function App() {
  return (
    <Routes>
      <Route path="/"                  element={<Home />} />
      <Route path="/get-started"       element={<IntakeFlow />} />
      <Route path="/thank-you"         element={<ThankYou />} />
      <Route path="/rates"             element={<RatesPage />} />
      <Route path="/homes"             element={<Listings />} />
      <Route path="/dpa"               element={<DpaHub />} />
      <Route path="/learn"             element={<Learn />} />
      <Route path="/learn/:slug"       element={<ProductDetail />} />
      <Route path="/realtors"          element={<RealtorPartner />} />
      <Route path="/campaign/:slug"    element={<CampaignPage />} />
    </Routes>
  )
}
