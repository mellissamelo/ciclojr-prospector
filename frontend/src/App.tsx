import { BrowserRouter, Route, Routes } from "react-router-dom"
import HomePage from "@/pages/HomePage"
import SetoresPage from "@/pages/SetoresPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/setores" element={<SetoresPage />} />
      </Routes>
    </BrowserRouter>
  )
}
