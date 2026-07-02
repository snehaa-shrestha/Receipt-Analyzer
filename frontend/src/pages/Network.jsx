import { useState, useEffect, useRef } from 'react';
import api from '../api/axios';
import { useWorkspace } from '../context/WorkspaceContext';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import {
    Search, UserPlus, Check, Users, Plus, MessageSquare, Send,
    Wallet, Receipt, Trash2, X, Settings, ArrowLeft, Upload,
    CheckCircle, Clock, UserCheck, AlertTriangle, ChevronRight, FileImage, Bell, UserX
} from 'lucide-react';


function StatBadge({ label, value, color }) {
    const colors = {
        blue: 'from-blue-500/10 to-blue-500/5 text-blue-400 border-blue-500/20 shadow-[inset_0_0_15px_rgba(59,130,246,0.1)]',
        green: 'from-green-500/10 to-green-500/5 text-green-400 border-green-500/20 shadow-[inset_0_0_15px_rgba(34,197,94,0.1)]',
        purple: 'from-purple-500/10 to-purple-500/5 text-purple-400 border-purple-500/20 shadow-[inset_0_0_15px_rgba(168,85,247,0.1)]',
        red: 'from-red-500/10 to-red-500/5 text-red-400 border-red-500/20 shadow-[inset_0_0_15px_rgba(239,68,68,0.1)]',
    };
    return (
        <div className={`px-4 py-3 rounded-2xl border bg-gradient-to-br text-center transition-all hover:scale-105 duration-300 ${colors[color]}`}>
            <p className="text-[10px] font-bold uppercase tracking-wider opacity-70 mb-1">{label}</p>
            <p className="font-extrabold text-lg">{value}</p>
        </div>
    );
}

function WorkspacePanel({ workspace, onClose, connections, onRefresh, currentUser }) {
    const [tab, setTab] = useState('chat');
    const [messages, setMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const ws = useRef(null);
    const messagesEndRef = useRef(null);

    const [budget, setBudget] = useState(workspace.budget || 0);
    const [editBudget, setEditBudget] = useState(false);
    const [budgetInput, setBudgetInput] = useState(workspace.budget || 0);

    const [expenses, setExpenses] = useState([]);
    const [expForm, setExpForm] = useState({ description: '', amount: '', category: '' });
    const [loadingExp, setLoadingExp] = useState(false);

    const [uploadFile, setUploadFile] = useState(null);
    const [uploading, setUploading] = useState(false);

    const [inviteQuery, setInviteQuery] = useState('');
    const [trueTotalSpent, setTrueTotalSpent] = useState(0);

    useEffect(() => {
        fetchMessages();
        fetchExpenses();
        fetchSummary();
        connectWS();
        return () => ws.current?.close();
    }, [workspace._id]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const connectWS = () => {
        const token = localStorage.getItem('token');
        if (!token) return;
        if (ws.current) ws.current.close();
        const url = `ws://localhost:8000/api/chat/ws/${workspace._id}?token=${token}`;
        ws.current = new WebSocket(url);
        ws.current.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'chat') {
                setMessages(prev => [...prev, data]);
            } else if (data.type === 'budget_update') {
                setBudget(data.budget);
                setBudgetInput(data.budget);
            } else if (data.type === 'expense_update') {
                fetchExpenses();
                fetchSummary();
            }
        };
    };

    const fetchMessages = async () => {
        try {
            const res = await api.get(`/chat/history/${workspace._id}`);
            setMessages(res.data);
        } catch (e) { console.error(e); }
    };

    const fetchExpenses = async () => {
        try {
            const res = await api.get(`/expenses/?workspace_id=${workspace._id}`);
            setExpenses(res.data.slice(0, 20));
        } catch (e) { console.error(e); }
    };

    const fetchSummary = async () => {
        try {
            const res = await api.get(`/expenses/summary?period=all&workspace_id=${workspace._id}`);
            const total = res.data.reduce((sum, cat) => sum + cat.total, 0);
            setTrueTotalSpent(total);
        } catch (e) { console.error(e); }
    };

    const sendMsg = (e) => {
        e.preventDefault();
        if (!newMessage.trim() || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;
        ws.current.send(newMessage);
        setNewMessage('');
    };

    const saveBudget = async () => {
        try {
            await api.put(`/workspaces/${workspace._id}/budget`, { budget: parseFloat(budgetInput) });
            setBudget(parseFloat(budgetInput));
            setEditBudget(false);
            onRefresh();
        } catch (e) { alert(e.response?.data?.detail || 'Error saving budget'); }
    };

    const addExpense = async (e) => {
        e.preventDefault();
        setLoadingExp(true);
        try {
            await api.post(`/expenses/?workspace_id=${workspace._id}`, {
                description: expForm.description,
                amount: parseFloat(expForm.amount),
                category: expForm.category || 'General',
                date: new Date().toISOString(),
                workspace_id: workspace._id,
            });
            setExpForm({ description: '', amount: '', category: '' });
            fetchExpenses();
            fetchSummary();
        } catch (e) { alert('Error adding expense'); }
        setLoadingExp(false);
    };

    const uploadReceipt = async (e) => {
        e.preventDefault();
        if (!uploadFile) return;
        setUploading(true);
        const fd = new FormData();
        fd.append('file', uploadFile);
        try {
            await api.post(`/receipts/upload?workspace_id=${workspace._id}`, fd, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setUploadFile(null);
            fetchExpenses();
            fetchSummary();
            alert('Receipt uploaded successfully!');
        } catch (e) { alert('Upload failed'); }
        setUploading(false);
    };

    const inviteFriend = async () => {
        const friend = connections.find(c =>
            c.username?.toLowerCase() === inviteQuery.toLowerCase() ||
            c.email?.toLowerCase() === inviteQuery.toLowerCase()
        );
        if (!friend) { alert('No connected friend with that name/email.'); return; }
        try {
            await api.post(`/workspaces/${workspace._id}/invite`, { user_to_invite: friend.id });
            setInviteQuery('');
            onRefresh();
            alert('Invited successfully!');
        } catch (e) { alert(e.response?.data?.detail || 'Error inviting'); }
    };

    const totalSpent = trueTotalSpent;
    const budgetPct = budget > 0 ? Math.min((totalSpent / budget) * 100, 100) : 0;
    const isOverBudget = totalSpent > budget && budget > 0;

    const tabs = [
        { id: 'chat', label: 'Chat Area', icon: MessageSquare },
        { id: 'budget', label: 'Budget Tracker', icon: Wallet },
        { id: 'receipts', label: 'AI Receipt', icon: Receipt },
        { id: 'members', label: 'Network', icon: Users },
    ];

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
            <div className="bg-gray-900/90 w-full max-w-4xl h-[90vh] rounded-[2rem] border border-gray-700/50 shadow-[0_0_50px_rgba(0,0,0,0.5)] flex flex-col overflow-hidden relative">
                <div className="absolute top-0 left-1/4 right-1/4 h-32 bg-blue-500/20 blur-[100px] pointer-events-none"></div>
                <div className="absolute bottom-0 left-0 right-0 h-32 bg-purple-500/10 blur-[100px] pointer-events-none"></div>

                <div className="relative bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 p-6 flex items-center justify-between border-b border-gray-800 flex-shrink-0 z-10">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg ring-2 ring-purple-500/20">
                            <Users size={24} className="text-white" />
                        </div>
                        <div>
                            <h2 className="font-extrabold text-2xl text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-300 tracking-tight">{workspace.name}</h2>
                            <p className="text-sm text-gray-400 font-medium flex items-center gap-1.5 mt-0.5">
                                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                {workspace.members?.length || 1} Active Participants
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="w-10 h-10 flex items-center justify-center rounded-xl bg-gray-800/50 hover:bg-red-500/20 text-gray-400 hover:text-red-400 border border-gray-700 hover:border-red-500/30 transition-all">
                        <X size={20} />
                    </button>
                </div>

                {budget > 0 && (
                    <div className={`px-8 py-4 flex-shrink-0 relative z-10 shadow-inner ${isOverBudget ? 'bg-red-950/30' : 'bg-gray-900/50'}`}>
                        <div className="flex justify-between items-end mb-2">
                            <span className="text-xs font-bold uppercase tracking-widest text-gray-500">Shared Budget Utilization</span>
                            <span className={`font-extrabold text-lg tracking-tight ${isOverBudget ? 'text-red-400' : 'text-gray-200'}`}>
                                <span className="text-sm font-medium mr-1 text-gray-500">Rs. </span>{totalSpent.toLocaleString()}
                                <span className="text-sm font-medium text-gray-500 mx-1">/</span>
                                <span className="text-sm font-medium opacity-70">Rs. {budget.toLocaleString()}</span>
                            </span>
                        </div>
                        <div className="h-2 bg-gray-950 rounded-full overflow-hidden border border-gray-800 shadow-inner">
                            <div
                                className={`h-full rounded-full transition-all duration-1000 ease-out ${isOverBudget ? 'bg-gradient-to-r from-red-500 to-rose-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' : 'bg-gradient-to-r from-blue-500 to-purple-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]'}`}
                                style={{ width: `${budgetPct}%` }}
                            />
                        </div>
                    </div>
                )}

                <div className="flex px-4 pt-4 border-b border-gray-800 flex-shrink-0 bg-gray-900/30 relative z-10">
                    {tabs.map(t => {
                        const Icon = t.icon;
                        const isActive = tab === t.id;
                        return (
                            <button
                                key={t.id}
                                onClick={() => setTab(t.id)}
                                className={`flex-1 flex items-center justify-center gap-2 pb-4 pt-2 text-sm font-bold transition-all border-b-2 relative ${isActive
                                    ? 'border-transparent text-white'
                                    : 'border-transparent text-gray-500 hover:text-gray-300'
                                    }`}
                            >
                                <Icon size={16} className={isActive ? 'text-blue-400' : ''} /> {t.label}
                                {isActive && (
                                    <div className="absolute bottom-[-2px] left-0 right-0 h-[2px] bg-gradient-to-r from-blue-500 to-purple-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]"></div>
                                )}
                            </button>
                        );
                    })}
                </div>

                <div className="flex-1 overflow-hidden flex flex-col relative z-10">

                    {tab === 'chat' && (
                        <div className="flex-1 flex flex-col h-full bg-gray-900/40">
                            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
                                {messages.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-gray-500">
                                        <div className="w-20 h-20 bg-gray-800 rounded-full flex items-center justify-center mb-4 shadow-inner">
                                            <MessageSquare size={32} className="opacity-50" />
                                        </div>
                                        <p className="font-medium tracking-wide">Start the conversation!</p>
                                    </div>
                                ) : messages.map((msg, i) => {
                                    const isMe = msg.sender_id === currentUser?.user_id || msg.sender_id === currentUser?.id || msg.sender_id === currentUser?._id;
                                    return (
                                        <div key={i} className={`flex ${isMe ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2`}>
                                            <div className={`max-w-[80%] ${isMe ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                                                {!isMe && <span className="text-[11px] font-bold text-gray-500 ml-2 uppercase tracking-wider">{msg.sender_name}</span>}
                                                <div className={`px-5 py-3 rounded-2xl text-sm break-words shadow-md ${isMe
                                                    ? 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-br-sm'
                                                    : 'bg-gray-800 text-gray-200 rounded-bl-sm border border-gray-700/50'}`}>
                                                    {msg.text}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                                <div ref={messagesEndRef} />
                            </div>
                            <form onSubmit={sendMsg} className="p-4 bg-gray-900/90 border-t border-gray-800 flex gap-3 flex-shrink-0 backdrop-blur-xl">
                                <input
                                    value={newMessage}
                                    onChange={e => setNewMessage(e.target.value)}
                                    placeholder="Type your message..."
                                    className="flex-1 bg-gray-950/50 backdrop-blur-sm border border-gray-800 rounded-2xl px-5 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 transition-all font-medium shadow-inner"
                                />
                                <button type="submit" disabled={!newMessage.trim()}
                                    className="bg-gradient-to-r from-indigo-500 to-purple-600 disabled:from-gray-800 disabled:to-gray-800 disabled:text-gray-500 text-white px-6 py-3.5 rounded-2xl transition-all shadow-lg hover:shadow-indigo-500/25 flex items-center gap-2 font-bold disabled:shadow-none hover:scale-105 active:scale-95">
                                    <Send size={18} /> Send
                                </button>
                            </form>
                        </div>
                    )}

                    {tab === 'budget' && (
                        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-900/40 custom-scrollbar">
                            <div className="bg-gray-800/40 backdrop-blur-xl rounded-2xl p-6 border border-gray-700/50 shadow-xl">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 flex items-center gap-2 text-lg">
                                        <Settings size={20} className="text-purple-400" /> Active Budget config
                                    </h3>
                                    {!editBudget && workspace.members?.find(m => String(m.user_id) === String(currentUser?._id || currentUser?.id || currentUser?.user_id))?.role === 'admin' && (
                                        <button onClick={() => setEditBudget(true)}
                                            className="text-xs font-bold text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 border border-gray-600 px-4 py-2 rounded-xl transition-all shadow-sm">
                                            Revise Budget
                                        </button>
                                    )}
                                </div>
                                {editBudget ? (
                                    <div className="flex flex-col sm:flex-row gap-3">
                                        <div className="relative flex-1">
                                            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-bold">Rs.</span>
                                            <input type="number" value={budgetInput} onChange={e => setBudgetInput(e.target.value)}
                                                className="w-full bg-gray-950/50 border border-gray-700 rounded-xl pl-10 pr-4 py-3 text-white font-bold focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 transition-all"
                                                placeholder="0.00" min="0" step="0.01" />
                                        </div>
                                        <button onClick={saveBudget} className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-8 py-3 rounded-xl font-bold hover:shadow-[0_0_15px_rgba(168,85,247,0.4)] transition-all">Apply</button>
                                        <button onClick={() => setEditBudget(false)} className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-6 py-3 rounded-xl font-bold transition-all border border-gray-700">Cancel</button>
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                        <StatBadge label="Allocated Budget" value={`Rs. ${budget.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} color="purple" />
                                        <StatBadge label="Cumulative Spent" value={`Rs. ${totalSpent.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} color={isOverBudget ? 'red' : 'blue'} />
                                        <StatBadge label="Funds Remaining" value={`Rs. ${Math.max(budget - totalSpent, 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`} color="green" />
                                    </div>
                                )}
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                                <div className="lg:col-span-2 bg-gray-800/40 backdrop-blur-xl rounded-2xl p-6 border border-gray-700/50 shadow-xl h-fit">
                                    <h3 className="font-extrabold text-white mb-5 flex items-center gap-2 text-lg">
                                        <Plus size={20} className="text-blue-400" /> Log Expense
                                    </h3>
                                    <form onSubmit={addExpense} className="space-y-4">
                                        <input
                                            value={expForm.description} required
                                            onChange={e => setExpForm({ ...expForm, description: e.target.value })}
                                            placeholder="Description (e.g. Flight tickets)"
                                            className="w-full bg-gray-950/50 border border-gray-700 rounded-xl px-4 py-3 text-sm font-medium text-white focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 transition-all shadow-inner"
                                        />
                                        <div className="relative">
                                            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-bold">Rs.</span>
                                            <input type="number" value={expForm.amount} required min="0" step="0.01"
                                                onChange={e => setExpForm({ ...expForm, amount: e.target.value })}
                                                placeholder="Amount"
                                                className="w-full bg-gray-950/50 border border-gray-700 rounded-xl pl-10 pr-4 py-3 text-sm font-medium text-white focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 transition-all shadow-inner"
                                            />
                                        </div>
                                        <input
                                            value={expForm.category}
                                            onChange={e => setExpForm({ ...expForm, category: e.target.value })}
                                            placeholder="Category (e.g. Travel)"
                                            className="w-full bg-gray-950/50 border border-gray-700 rounded-xl px-4 py-3 text-sm font-medium text-white focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 transition-all shadow-inner"
                                        />
                                        <button type="submit" disabled={loadingExp}
                                            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 disabled:opacity-50 text-white font-bold py-3.5 rounded-xl transition-all shadow-lg hover:shadow-blue-500/25 mt-2">
                                            {loadingExp ? (
                                                <div className="flex items-center justify-center gap-2"><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Pending...</div>
                                            ) : 'Add to Ledger'}
                                        </button>
                                    </form>
                                </div>

                                <div className="lg:col-span-3 bg-gray-800/40 backdrop-blur-xl rounded-2xl p-6 border border-gray-700/50 shadow-xl overflow-hidden flex flex-col h-[400px]">
                                    <h3 className="font-extrabold text-white mb-4 flex items-center justify-between">
                                        Recent Incurred Costs
                                        <span className="text-xs font-bold text-gray-400 bg-gray-800 px-3 py-1 rounded-full uppercase tracking-wider">{expenses.length} Entries</span>
                                    </h3>
                                    <div className="space-y-3 overflow-y-auto pr-2 custom-scrollbar flex-1">
                                        {expenses.length === 0 ? (
                                            <div className="h-full flex flex-col items-center justify-center text-gray-500">
                                                <Receipt size={40} className="mb-3 opacity-20" />
                                                <p className="text-sm font-medium">No ledger entries recorded.</p>
                                            </div>
                                        ) : expenses.map((exp, i) => (
                                            <div key={i} className="flex items-center justify-between p-4 bg-gray-900/60 rounded-xl border border-gray-800 hover:border-gray-600 transition-all shadow-sm group">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 border border-blue-500/20 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform">
                                                        <Receipt size={18} className="text-blue-400" />
                                                    </div>
                                                    <div>
                                                        <p className="font-bold text-white tracking-wide">{exp.description}</p>
                                                        <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-md shadow-inner">{exp.category}</span>
                                                    </div>
                                                </div>
                                                <span className="font-extrabold text-white text-lg tracking-tight">Rs. {(exp.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {tab === 'receipts' && (
                        <div className="flex-1 overflow-y-auto p-6 bg-gray-900/40">
                            <div className="bg-gray-800/40 backdrop-blur-xl rounded-3xl p-8 border border-gray-700/50 shadow-2xl max-w-2xl mx-auto relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-32 bg-green-500/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"></div>
                                <h3 className="text-2xl font-extrabold mb-2 flex items-center gap-3 text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-500">
                                    Group AI Upload
                                </h3>
                                <p className="text-sm font-medium text-gray-400 mb-8 border-l-2 border-emerald-500/50 pl-3">Proprietary AI engine extracts and synchronizes ledger expenses instantly.</p>

                                <form onSubmit={uploadReceipt} className="space-y-6 relative z-10">
                                    <label className="block w-full cursor-pointer group/dropzone">
                                        <div className={`border-2 border-dashed rounded-3xl p-10 flex flex-col items-center justify-center min-h-[250px] transition-all bg-gray-900/40 shadow-inner ${uploadFile ? 'border-green-500/50 bg-green-950/20 shadow-[inset_0_0_20px_rgba(34,197,94,0.1)]' : 'border-gray-700 hover:border-emerald-500/50 hover:bg-emerald-950/10'}`}>
                                            {uploadFile ? (
                                                <div className="flex flex-col items-center gap-3 animate-in zoom-in-95 duration-300">
                                                    <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center border border-green-500/30">
                                                        <CheckCircle size={32} className="text-green-400" />
                                                    </div>
                                                    <p className="text-lg font-bold text-white">{uploadFile.name}</p>
                                                    <p className="text-xs font-bold uppercase tracking-widest text-gray-500">{(uploadFile.size / 1024).toFixed(1)} KB PAYLOAD</p>
                                                </div>
                                            ) : (
                                                <div className="flex flex-col items-center gap-4 text-center transform group-hover/dropzone:-translate-y-2 transition-transform duration-300">
                                                    <div className="w-20 h-20 bg-gradient-to-b from-gray-800 to-gray-900 rounded-full flex items-center justify-center shadow-inner border border-gray-700 group-hover/dropzone:border-emerald-500/30">
                                                        <Upload size={32} className="text-emerald-400 group-hover/dropzone:scale-110 transition-transform" />
                                                    </div>
                                                    <div>
                                                        <p className="text-lg font-bold text-white mb-1">Select Receipt Document</p>
                                                        <div className="flex items-center justify-center gap-3 text-xs font-bold uppercase tracking-wider text-gray-500">
                                                            <span className="flex items-center gap-1"><FileImage size={14} /> JPG</span>
                                                            <span className="flex items-center gap-1"><FileImage size={14} /> PNG</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                            <input type="file" accept="image/*" className="hidden"
                                                onChange={e => setUploadFile(e.target.files[0])} />
                                        </div>
                                    </label>

                                    {uploadFile && (
                                        <div className="flex gap-4 animate-in slide-in-from-bottom-4 duration-300">
                                            <button type="submit" disabled={uploading}
                                                className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 disabled:opacity-50 text-white font-bold py-4 rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_25px_rgba(16,185,129,0.5)] transition-all flex items-center justify-center gap-2">
                                                {uploading ? (
                                                    <><div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Analzying Document...</>
                                                ) : (
                                                    <><Upload size={20} /> Execute AI Extraction</>
                                                )}
                                            </button>
                                            <button type="button" onClick={() => setUploadFile(null)}
                                                className="w-14 items-center justify-center flex bg-gray-800 hover:bg-red-500/20 border border-gray-700 hover:border-red-500/30 text-gray-400 hover:text-red-400 rounded-xl transition-all shadow-inner">
                                                <X size={20} />
                                            </button>
                                        </div>
                                    )}
                                </form>
                            </div>
                        </div>
                    )}

                    {tab === 'members' && (
                        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-900/40 custom-scrollbar">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="bg-gray-800/40 backdrop-blur-xl rounded-2xl p-6 border border-gray-700/50 shadow-xl self-start h-fit">
                                    <h3 className="font-extrabold text-white mb-5 flex items-center gap-2 text-lg">
                                        <UserPlus size={20} className="text-blue-400" /> Send Invite Request
                                    </h3>
                                    <div className="flex flex-col gap-3">
                                        <input value={inviteQuery} onChange={e => setInviteQuery(e.target.value)}
                                            placeholder="Connection username or email..."
                                            className="w-full bg-gray-950/50 border border-gray-700 rounded-xl px-4 py-3 text-sm font-medium text-white focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 transition-all shadow-inner"
                                        />
                                        <button onClick={inviteFriend}
                                            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:to-indigo-500 shadow-lg hover:shadow-blue-500/30 text-white py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2">
                                            Send Invitation
                                        </button>
                                    </div>
                                    <div className="mt-4 flex items-start gap-2 text-xs font-semibold text-gray-500 bg-gray-900/50 border border-gray-800 p-3 rounded-xl">
                                        <AlertTriangle size={14} className="text-yellow-500/70 mt-0.5 flex-shrink-0" />
                                        <p>Trust constraints limit invitations strictly to already established network connections.</p>
                                    </div>
                                </div>

                                <div className="bg-gray-800/40 backdrop-blur-xl rounded-2xl p-6 border border-gray-700/50 shadow-xl overflow-hidden flex flex-col max-h-[400px]">
                                    <h3 className="font-extrabold text-white mb-4 flex items-center justify-between">
                                        Network Roster
                                        <span className="text-xs font-bold text-gray-400 bg-gray-800 px-3 py-1 rounded-full uppercase tracking-wider">{workspace.members?.length || 1} Total</span>
                                    </h3>
                                    <div className="space-y-3 overflow-y-auto pr-1 flex-1 custom-scrollbar">
                                        {(workspace.members || []).map((m, i) => (
                                            <div key={i} className="flex items-center justify-between p-3 bg-gray-900/60 rounded-xl border border-gray-800/50 hover:border-gray-600 transition-colors shadow-sm">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 p-[1px] shadow-md">
                                                        <div className="w-full h-full bg-gray-900 rounded-xl flex items-center justify-center font-bold text-white">
                                                            {(m.username || 'U')[0].toUpperCase()}
                                                        </div>
                                                    </div>
                                                    <span className="text-sm font-bold text-white tracking-wide">{m.username || m.user_id}</span>
                                                </div>
                                                <span className={`text-[10px] uppercase font-black tracking-widest px-3 py-1.5 rounded-lg border shadow-inner ${m.role === 'admin' ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' : 'bg-gray-800 text-gray-400 border-gray-700'}`}>
                                                    {m.role}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function Network() {
    const { user } = useAuth();
    const { workspaces, fetchWorkspaces } = useWorkspace();

    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [connections, setConnections] = useState([]);
    const [newWorkspaceName, setNewWorkspaceName] = useState('');
    const [selectedWorkspace, setSelectedWorkspace] = useState(null);
    const [activeSection, setActiveSection] = useState('friends');

    const [pendingRequests, setPendingRequests] = useState([]);
    const pollRef = useRef(null);

    const fetchPending = async () => {
        try {
            const res = await api.get(`/social/pending?t=${Date.now()}`);
            const mapped = res.data.map(req => ({
                id: req.id,
                username: req.username,
                email: req.email,
                connection_status: 'pending',
                is_sender: false
            }));
            setPendingRequests(mapped);
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        fetchConnections();
        fetchPending();
        pollRef.current = setInterval(fetchPending, 3000);
        return () => clearInterval(pollRef.current);
    }, []);

    const fetchConnections = async () => {
        try {
            const res = await api.get('/social/connections');
            setConnections(res.data);
        } catch (e) { console.error(e); }
    };

    const handleUnfriend = async (friendId, username) => {
        if (!window.confirm(`Remove ${username} from your connections?`)) return;
        try {
            await api.delete(`/social/connections/${friendId}`);
            await fetchConnections();
            if (searchResults.length > 0) handleSearch({ preventDefault: () => {} });
        } catch (e) { alert(e.response?.data?.detail || 'Error removing connection'); }
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        if (searchQuery.length < 2) return;
        try {
            const res = await api.get(`/social/search?query=${searchQuery}`);
            setSearchResults(res.data);
        } catch (e) { console.error(e); }
    };

    const sendRequest = async (id) => {
        try {
            await api.post(`/social/connect/${id}`);
            handleSearch({ preventDefault: () => { } });
        } catch (e) { alert(e.response?.data?.detail || 'Error connecting'); }
    };

    const acceptRequest = async (id) => {
        try {
            await api.put(`/social/connect/${id}/accept`);
            fetchConnections();
            fetchPending();
            if (searchQuery.length >= 2) handleSearch({ preventDefault: () => { } });
        } catch (e) { alert(e.response?.data?.detail || 'Error accepting'); }
    };

    const cancelRequest = async (id) => {
        try {
            await api.delete(`/social/connect/${id}`);
            fetchPending();
            if (searchQuery.length >= 2) handleSearch({ preventDefault: () => { } });
        } catch (e) { alert(e.response?.data?.detail || 'Error cancelling'); }
    };

    const handleCreateWorkspace = async (e) => {
        e.preventDefault();
        try {
            await api.post('/workspaces/', { name: newWorkspaceName, type: 'group' });
            setNewWorkspaceName('');
            fetchWorkspaces();
        } catch (e) { console.error(e); }
    };

    const handleDeleteWorkspace = async (workspaceId, e) => {
        e.stopPropagation(); // Prevent opening the workspace panel
        if (!window.confirm("Are you sure you want to delete this workspace and ALL its associated expenses, receipts, and chat history? This action is permanent.")) {
            return;
        }
        try {
            await api.delete(`/workspaces/${workspaceId}`);

            const activeWorkspaceId = localStorage.getItem('activeWorkspace');
            if (activeWorkspaceId === workspaceId) {
                localStorage.removeItem('activeWorkspace');
                window.dispatchEvent(new Event('storage')); // Trigger update across app
            }

            fetchWorkspaces();
        } catch (error) {
            alert(error.response?.data?.detail || 'Error deleting workspace');
        }
    };

    return (
        <Layout>
            <div className="max-w-7xl mx-auto space-y-8 animate-fade-in relative">

                <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 p-1 relative z-10">
                    <div>

                        <div className="flex items-center gap-2 text-gray-400 text-sm mb-1 font-medium tracking-wide uppercase">
                            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shadow-[0_0_10px_rgba(59,130,246,0.8)]"></span>
                            Social & Collaboration
                        </div>
                        <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 tracking-tight">
                            Network Hub
                        </h1> <br />
                    </div>

                    <div className="flex bg-gray-900/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl p-1.5 shadow-inner">
                        <button
                            onClick={() => setActiveSection('friends')}
                            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2 duration-300 ${activeSection === 'friends' ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-[0_4px_12px_rgba(37,99,235,0.3)]' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}>
                            <UserPlus size={16} /> Connections
                        </button>
                        <button
                            onClick={() => setActiveSection('workspaces')}
                            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2 duration-300 ${activeSection === 'workspaces' ? 'bg-gradient-to-r from-purple-600 to-pink-500 text-white shadow-[0_4px_12px_rgba(147,51,234,0.3)]' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}>
                            <Users size={16} /> Workspaces
                        </button>
                    </div>
                </div>

                {activeSection === 'friends' && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 relative z-10 animate-in slide-in-from-bottom-4 duration-500">
                        <div className="bg-gray-800/40 backdrop-blur-xl p-8 rounded-[2rem] border border-gray-700/50 shadow-2xl relative overflow-hidden group/panel">
                            <div className="absolute top-0 right-0 p-32 bg-blue-500/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none transition-all duration-700 group-hover/panel:bg-blue-500/20"></div>
                            <h2 className="text-xl font-black flex items-center gap-3 mb-6 relative z-10 text-white tracking-wide">
                                <div className="p-2.5 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 text-blue-400 rounded-xl shadow-inner border border-blue-500/20"><Search size={22} /></div>
                                Discover Users
                            </h2>

                            <div className="relative group z-10 font-medium mb-8">
                                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl transition duration-500 opacity-0 group-focus-within:opacity-100 pointer-events-none"></div>
                                <form onSubmit={handleSearch} className="relative flex items-center bg-gray-900/60 backdrop-blur-sm rounded-2xl border border-gray-700/50 p-1.5 shadow-inner focus-within:border-blue-500/50 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
                                    <input type="text" placeholder="Lookup by alias or email context..."
                                        value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                                        className="flex-1 bg-transparent border-none px-5 py-3.5 text-white placeholder-gray-500 focus:outline-none font-bold tracking-wide"
                                    />
                                    <button type="submit" className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:to-indigo-500 text-white p-3.5 rounded-xl transition shadow-[0_0_15px_rgba(37,99,235,0.3)] hover:shadow-[0_0_20px_rgba(79,70,229,0.5)] active:scale-95">
                                        <Search size={20} />
                                    </button>
                                </form>
                            </div>

                            <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 relative z-10 custom-scrollbar">
                                {searchQuery.length < 2 && pendingRequests.length > 0 && (
                                    <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 px-2 flex items-center gap-2">
                                        <Bell size={14} className="text-red-400" /> Pending Requests
                                    </p>
                                )}
                                {searchQuery.length < 2 && pendingRequests.length === 0 && (
                                    <p className="text-gray-500 font-medium text-center py-10 opacity-70">Search for users to connect with.</p>
                                )}
                                {searchQuery.length >= 2 && searchResults.length === 0 && (
                                    <p className="text-gray-500 font-medium text-center py-10 opacity-70">No users found for "{searchQuery}".</p>
                                )}
                                {(searchQuery.length < 2 ? pendingRequests : searchResults).map(u => (
                                    <div key={u.id} className="flex flex-col sm:flex-row items-center justify-between p-4 bg-gray-900/40 hover:bg-gray-800/80 rounded-2xl border border-gray-800 hover:border-blue-500/30 transition-all shadow-sm gap-4">
                                        <div className="flex items-center gap-4 w-full sm:w-auto">
                                            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 p-[1px] shadow-lg flex-shrink-0">
                                                <div className="w-full h-full bg-gray-900 rounded-2xl flex items-center justify-center font-bold text-xl text-white">
                                                    {u.username?.[0]?.toUpperCase()}
                                                </div>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="font-extrabold text-white text-lg tracking-tight truncate">{u.username}</p>
                                                <p className="text-xs text-blue-400 font-semibold truncate bg-blue-500/10 inline-block px-2 py-0.5 rounded-md mt-1 border border-blue-500/20">{u.email}</p>
                                            </div>
                                        </div>

                                        <div className="w-full sm:w-auto flex justify-end">
                                            {u.connection_status === 'none' && (
                                                <button onClick={() => sendRequest(u.id)} className="w-full sm:w-auto text-xs font-black tracking-widest uppercase bg-blue-600/10 hover:bg-blue-600 border border-blue-500/20 hover:border-transparent text-blue-400 hover:text-white px-5 py-3 rounded-xl transition-all shadow-inner hover:shadow-[0_0_15px_rgba(37,99,235,0.5)]">
                                                    Connect
                                                </button>
                                            )}
                                            {u.connection_status === 'pending' && u.is_sender && (
                                                <div className="flex gap-2">
                                                    <span className="text-xs text-gray-400 flex items-center gap-2 font-bold uppercase tracking-wider bg-gray-800 border border-gray-700 px-4 py-2.5 rounded-xl shadow-inner"><Clock size={16} /> Pending</span>
                                                    <button onClick={() => cancelRequest(u.id)} title="Cancel request" className="text-xs font-black bg-red-500/10 hover:bg-red-500 border border-red-500/20 hover:border-transparent text-red-400 hover:text-white px-3 py-2.5 rounded-xl flex items-center gap-1.5 transition-all shadow-inner">
                                                        <X size={14} /> Cancel
                                                    </button>
                                                </div>
                                            )}
                                            {u.connection_status === 'pending' && !u.is_sender && (
                                                <div className="flex gap-2">
                                                    <button onClick={() => acceptRequest(u.id)} className="text-xs font-black tracking-widest uppercase bg-emerald-500/10 hover:bg-emerald-500 border border-emerald-500/20 hover:border-transparent text-emerald-400 hover:text-white px-4 py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-inner hover:shadow-[0_0_15px_rgba(16,185,129,0.5)]">
                                                        <Check size={16} /> Accept
                                                    </button>
                                                    <button onClick={() => cancelRequest(u.id)} title="Reject" className="text-xs font-black bg-red-500/10 hover:bg-red-500 border border-red-500/20 hover:border-transparent text-red-400 hover:text-white px-3 py-3 rounded-xl flex items-center gap-1.5 transition-all shadow-inner">
                                                        <X size={14} />
                                                    </button>
                                                </div>
                                            )}
                                            {u.connection_status === 'accepted' && (
                                                <span className="text-xs text-emerald-400 flex items-center gap-2 font-bold uppercase tracking-wider bg-emerald-500/10 border border-emerald-500/20 px-4 py-2.5 rounded-xl shadow-inner"><CheckCircle size={16} /> Verified</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="bg-gray-800/40 backdrop-blur-xl p-8 rounded-[2rem] border border-gray-700/50 shadow-2xl relative overflow-hidden group/panel">
                            <div className="absolute bottom-0 left-0 p-32 bg-green-500/10 rounded-full blur-3xl -ml-20 -mb-20 pointer-events-none transition-all duration-700 group-hover/panel:bg-green-500/20"></div>
                            <h2 className="text-xl font-black flex items-center gap-3 mb-8 relative z-10 text-white tracking-wide">
                                <div className="p-2.5 bg-gradient-to-br from-green-500/20 to-emerald-500/20 text-green-400 rounded-xl shadow-inner border border-green-500/20"><UserCheck size={22} /></div>
                                Active Connections
                                <span className="ml-auto text-sm font-black text-white bg-gradient-to-br from-green-500 to-emerald-600 px-3 py-1 rounded-xl shadow-[0_0_10px_rgba(16,185,129,0.4)]">{connections.length}</span>
                            </h2>

                            <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2 relative z-10 custom-scrollbar">
                                {connections.length === 0 ? (
                                    <div className="text-center py-20 text-gray-500">
                                        <div className="w-24 h-24 bg-gray-800/80 border border-gray-700 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner relative">
                                            <div className="absolute inset-0 rounded-full border border-green-500/20 animate-ping opacity-20"></div>
                                            <UserCheck size={40} className="opacity-50 text-green-500/50" />
                                        </div>
                                        <p className="font-bold tracking-wide">Establish connections to populate UI.</p>
                                    </div>
                                ) : connections.map(c => (
                                    <div key={c.id} className="flex items-center gap-5 p-4 bg-gray-900/40 hover:bg-gray-800/80 rounded-2xl border border-gray-800 shadow-sm transition-all group hover:border-green-500/30">
                                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-400 p-[1px] shadow-lg flex-shrink-0 group-hover:shadow-[0_0_15px_rgba(16,185,129,0.4)] transition-all">
                                            <div className="w-full h-full bg-gray-900 rounded-2xl flex items-center justify-center font-bold text-xl text-white">
                                                {c.username?.[0]?.toUpperCase()}
                                            </div>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="font-extrabold text-white text-lg truncate tracking-tight">{c.username}</p>
                                            <p className="text-xs text-gray-400 truncate font-semibold">{c.email}</p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="hidden sm:inline-flex text-[10px] uppercase font-black tracking-widest text-green-400 bg-green-500/10 border border-green-500/20 px-3 py-1.5 rounded-lg shadow-inner group-hover:hidden">Connected</span>
                                            <button
                                                onClick={() => handleUnfriend(c.id, c.username)}
                                                className="hidden group-hover:inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-red-400 bg-red-500/10 hover:bg-red-500 border border-red-500/20 hover:border-transparent hover:text-white px-3 py-1.5 rounded-lg transition-all shadow-inner hover:shadow-[0_0_12px_rgba(239,68,68,0.4)]"
                                            >
                                                <UserX size={13} /> Unfriend
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {activeSection === 'workspaces' && (
                    <div className="space-y-8 relative z-10 animate-in slide-in-from-bottom-4 duration-500">
                        <div className="bg-gray-800/40 backdrop-blur-xl p-8 rounded-[2rem] border border-gray-700/50 shadow-2xl relative overflow-hidden group">
                            <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 to-pink-500/5 transition duration-700 group-hover:from-purple-500/10 group-hover:to-pink-500/10 pointer-events-none"></div>
                            <form onSubmit={handleCreateWorkspace} className="flex flex-col md:flex-row gap-4 relative z-10 w-full max-w-4xl mx-auto">
                                <div className="relative flex-1">
                                    <div className="absolute inset-0 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-2xl blur-xl transition duration-500 opacity-0 group-focus-within:opacity-100 pointer-events-none"></div>
                                    <input type="text" placeholder="Generate Collaborative Space (e.g. Vacation Funds)..."
                                        value={newWorkspaceName} onChange={e => setNewWorkspaceName(e.target.value)} required
                                        className="w-full relative bg-gray-900/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl px-6 py-4.5 text-white font-bold tracking-wide focus:outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/20 shadow-inner transition-all h-[60px]"
                                    />
                                </div>
                                <button type="submit" disabled={!newWorkspaceName.trim()} className="relative overflow-hidden bg-gradient-to-r from-purple-600 to-pink-600 disabled:opacity-50 disabled:grayscale font-black uppercase tracking-wider text-xs text-white px-8 h-[60px] rounded-2xl shadow-[0_0_20px_rgba(168,85,247,0.3)] hover:shadow-[0_0_30px_rgba(236,72,153,0.5)] transition-all flex items-center justify-center gap-2 group/btn">
                                    <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-[100%] group-hover/btn:translate-x-[100%] transition-transform duration-1000 ease-in-out"></div>
                                    <Plus size={18} strokeWidth={3} /> INITIALIZE
                                </button>
                            </form>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {workspaces.length === 0 ? (
                                <div className="col-span-full text-center py-24 bg-gray-800/20 backdrop-blur-sm rounded-[2rem] border-2 border-dashed border-gray-700/50 group hover:border-purple-500/30 transition-all duration-300">
                                    <div className="w-24 h-24 bg-gray-900/50 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-inner border border-gray-800 rotate-3 group-hover:-rotate-3 transition-all duration-300">
                                        <Users size={40} className="text-gray-600 group-hover:text-purple-400 group-hover:scale-110 transition-all duration-300" />
                                    </div>
                                    <h3 className="text-2xl font-black text-white mb-2 tracking-tight">No Active Domains</h3>
                                    <p className="text-gray-500 font-bold">Initialize a new space above to enable shared ledgers.</p>
                                </div>
                            ) : workspaces.map(w => {
                                const spent = w.total_spent || 0;
                                const budgetPct = w.budget > 0 ? Math.min((spent / w.budget) * 100, 100) : 0;
                                return (
                                    <button
                                        key={w._id}
                                        onClick={() => setSelectedWorkspace(w)}
                                        className="text-left bg-gray-800/40 backdrop-blur-xl p-6 rounded-[2rem] border border-gray-700/50 hover:border-purple-500/40 hover:bg-gray-800/80 shadow-xl hover:shadow-[0_10px_40px_-10px_rgba(168,85,247,0.3)] transition-all duration-300 group relative overflow-hidden flex flex-col h-full"
                                        style={{ transform: "translateZ(0)" }}
                                    >
                                        <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>

                                        <div className="flex items-start justify-between mb-8 relative z-10 w-full">
                                            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-purple-500/30 flex items-center justify-center shadow-inner group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300 flex-shrink-0">
                                                <Users size={28} className="text-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.5)]" />
                                            </div>
                                            <div className="flex gap-2">
                                                {w.members?.find(m => String(m.user_id) === String(user?._id || user?.id || user?.user_id))?.role === 'admin' && (
                                                    <button
                                                        onClick={(e) => handleDeleteWorkspace(w._id, e)}
                                                        className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center shadow-inner hover:bg-red-500 hover:text-white text-red-400 transition-all duration-300 opacity-0 group-hover:opacity-100"
                                                        title="Delete Workspace"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                )}
                                                <div className="w-10 h-10 rounded-full bg-gray-900/50 border border-gray-700/50 flex items-center justify-center shadow-inner group-hover:bg-purple-600 group-hover:border-purple-500 group-hover:text-white text-gray-500 transition-all duration-300 translate-x-2 opacity-0 group-hover:opacity-100 group-hover:translate-x-0">
                                                    <ChevronRight size={20} className="ml-0.5" />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex-1 z-10 w-full mb-8">
                                            <h3 className="font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-300 group-hover:to-white text-2xl mb-3 transition-all duration-300 truncate">
                                                {w.name}
                                            </h3>
                                            <p className="text-[11px] font-black uppercase tracking-widest text-purple-400 bg-purple-500/10 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-purple-500/20 shadow-inner">
                                                <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse"></span>
                                                {w.members?.length || 1} USER{(w.members?.length || 1) !== 1 ? 'S' : ''} DETECTED
                                            </p>
                                        </div>

                                        <div className="w-full relative z-10 mt-auto border-t border-gray-800/60 pt-6">
                                            {w.budget > 0 ? (
                                                <div className="mb-5 bg-gray-900/50 p-3 rounded-xl border border-gray-800 shadow-inner">
                                                    <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest mb-2">
                                                        <span className="text-gray-500">Capital Limit</span>
                                                        <span className="text-purple-400">${w.budget?.toLocaleString()}</span>
                                                    </div>
                                                    <div className="h-1.5 bg-gray-950 rounded-full overflow-hidden border border-gray-800/50">
                                                        <div className="h-full bg-gradient-to-r from-blue-500 to-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.8)]"
                                                            style={{ width: `${budgetPct}%` }} />
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="mb-5 flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-gray-500 bg-gray-900/30 rounded-xl p-3 border border-dashed border-gray-800">
                                                    <span>Unrestricted Cap</span>
                                                    <Wallet size={14} className="opacity-40" />
                                                </div>
                                            )}
                                            <div className="flex gap-2 flex-wrap">
                                                <span className="text-[10px] font-bold uppercase tracking-widest bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-3 py-1.5 rounded-xl shadow-inner flex items-center gap-1.5">
                                                    <MessageSquare size={12} /> Sync
                                                </span>
                                                <span className="text-[10px] font-bold uppercase tracking-widest bg-pink-500/10 text-pink-400 border border-pink-500/20 px-3 py-1.5 rounded-xl shadow-inner flex items-center gap-1.5">
                                                    <Receipt size={12} /> Ledger
                                                </span>
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}

                {selectedWorkspace && (
                    <WorkspacePanel
                        workspace={selectedWorkspace}
                        onClose={() => setSelectedWorkspace(null)}
                        connections={connections}
                        onRefresh={fetchWorkspaces}
                        currentUser={user}
                    />
                )}
            </div>
        </Layout>
    );
}
