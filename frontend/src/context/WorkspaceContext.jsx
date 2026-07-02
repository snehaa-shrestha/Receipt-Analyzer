import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/axios';
import { useAuth } from './AuthContext';

const WorkspaceContext = createContext();

export const useWorkspace = () => useContext(WorkspaceContext);

export const WorkspaceProvider = ({ children }) => {
    const { user } = useAuth();
    const [workspaces, setWorkspaces] = useState([]);
    const [activeWorkspace, setActiveWorkspace] = useState(null); // null means personal
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            fetchWorkspaces();
        } else {
            setWorkspaces([]);
            setActiveWorkspace(null);
            setLoading(false);
            localStorage.removeItem('activeWorkspace');
        }
    }, [user]);

    const fetchWorkspaces = async () => {
        try {
            const res = await api.get('/workspaces/');
            setWorkspaces(res.data);

            const saved = localStorage.getItem('activeWorkspace');
            const found = res.data.find(w => w._id === saved);
            if (saved && found) {
                setActiveWorkspace(found);
            } else {
                setActiveWorkspace(null);
                localStorage.removeItem('activeWorkspace');
            }
        } catch (error) {
            console.error("Error fetching workspaces", error);
        } finally {
            setLoading(false);
        }
    };

    const changeWorkspace = (workspace) => {
        setActiveWorkspace(workspace);
        if (workspace) {
            localStorage.setItem('activeWorkspace', workspace._id);
        } else {
            localStorage.removeItem('activeWorkspace');
        }
        window.location.reload();
    };

    return (
        <WorkspaceContext.Provider value={{ workspaces, activeWorkspace, changeWorkspace, fetchWorkspaces, loading }}>
            {children}
        </WorkspaceContext.Provider>
    );
};
