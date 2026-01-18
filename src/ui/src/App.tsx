import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { DashboardLayout } from '@/layouts/DashboardLayout';
import Dashboard from '@/pages/Dashboard';
import AgentView from '@/pages/AgentView';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="agents" element={<Dashboard />} />
          <Route path="agents/:agentId" element={<AgentView />} />
          <Route path="settings" element={<div className="text-gray-500">Settings coming soon...</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
