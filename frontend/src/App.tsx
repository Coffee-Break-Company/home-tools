import { Routes, Route } from 'react-router-dom'
import { Home } from '@/pages/Home'
import { Bills } from '@/pages/Bills'
import { NotFound } from '@/pages/NotFound'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/contas" element={<Bills />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default App
