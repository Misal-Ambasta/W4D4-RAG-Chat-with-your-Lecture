import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App';

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        {/* Add more routes here as needed */}
      </Routes>
    </BrowserRouter>
  );
}
