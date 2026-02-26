import { ChevronDown, Users, User } from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';
import { useState, useRef, useEffect } from 'react';

export default function WorkspaceSelector() {
    const { workspaces, activeWorkspace, changeWorkspace, loading } = useWorkspace();
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, [dropdownRef]);

    if (loading) return null;

    return (
        <div className="relative px-4 py-2" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between bg-gray-700/50 hover:bg-gray-700 p-2 rounded-lg border border-gray-600 transition"
            >
                <div className="flex items-center gap-2 overflow-hidden">
                    {activeWorkspace ? <Users size={16} className="text-blue-400" /> : <User size={16} className="text-pink-400" />}
                    <span className="font-semibold text-sm truncate">
                        {activeWorkspace ? activeWorkspace.name : "Personal Workspace"}
                    </span>
                </div>
                <ChevronDown size={16} className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute z-50 top-full left-4 right-4 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl overflow-hidden">
                    <button
                        onClick={() => { changeWorkspace(null); setIsOpen(false); }}
                        className={`w-full flex items-center gap-2 p-3 text-sm text-left hover:bg-gray-700 transition ${!activeWorkspace ? 'bg-blue-600/10 text-blue-400' : 'text-gray-300'}`}
                    >
                        <User size={16} />
                        Personal Workspace
                    </button>

                    {workspaces.map(w => (
                        <button
                            key={w._id}
                            onClick={() => { changeWorkspace(w); setIsOpen(false); }}
                            className={`w-full flex items-center gap-2 p-3 text-sm text-left hover:bg-gray-700 transition border-t border-gray-700/50 ${activeWorkspace?._id === w._id ? 'bg-blue-600/10 text-blue-400' : 'text-gray-300'}`}
                        >
                            <Users size={16} />
                            {w.name}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
