import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { WorkspaceProvider } from './context/WorkspaceContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import UploadReceipt from './pages/UploadReceipt';
import ReceiptGallery from './pages/ReceiptGallery';
import Analytics from './pages/Analytics';
import Game from './pages/Game';
import Profile from './pages/Profile';
import Transactions from './pages/Transactions';
import Network from './pages/Network';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <WorkspaceProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              <Route element={<ProtectedRoute />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/upload" element={<UploadReceipt />} />
                <Route path="/gallery" element={<ReceiptGallery />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/game" element={<Game />} />
                <Route path="/network" element={<Network />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/transactions" element={<Transactions />} />
                <Route path="*" element={<Navigate to="/" />} />
              </Route>
            </Routes>
          </Router>
        </WorkspaceProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
