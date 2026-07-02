import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { Search, Trash2, Calendar, CreditCard, FileText, Filter } from 'lucide-react';
import { getCategoryColor } from '../utils/categoryColors';

const CATEGORIES = ["All", "Food", "Groceries", "Transport", "Utilities", "Entertainment", "Shopping", "Other"];

export default function Transactions() {
    const { user } = useAuth();
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('All');
    const [deleteLoading, setDeleteLoading] = useState(null);

    const currencySymbol = {
        'USD': 'Rs.', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'NPR': 'Rs.'
    }[user?.currency || 'USD'] || 'Rs.';

    useEffect(() => {
        fetchTransactions();
    }, []);

    const fetchTransactions = async () => {
        setLoading(true);
        try {
            const res = await api.get('/expenses/');
            setTransactions(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (tx) => {
        const isReceipt = tx.type === 'receipt' || tx.receipt_id;
        const endpoint = isReceipt ? `/receipts/${tx._id}` : `/expenses/${tx._id}`;
        const confirmMsg = isReceipt
            ? "Are you sure? This will delete the receipt and all associated items."
            : "Are you sure you want to delete this transaction?";

        if (!window.confirm(confirmMsg)) return;
        setDeleteLoading(tx._id);

        try {
            await api.delete(endpoint);
            setTransactions(transactions.filter(t => t._id !== tx._id));
        } catch (e) {
            console.error(e);
            alert("Failed to delete. It might already be gone.");
        } finally {
            setDeleteLoading(null);
        }
    };

    const filteredTransactions = transactions.filter(t => {
        const matchesSearch = t.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            t.category?.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesCategory = selectedCategory === "All" || t.category === selectedCategory;
        return matchesSearch && matchesCategory;
    });

    return (
        <Layout>
            <div className="max-w-7xl mx-auto space-y-8">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 p-1">
                    <div>
                        <div className="flex items-center gap-2 text-gray-400 text-sm mb-1 font-medium tracking-wide uppercase">
                            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                            Transaction History
                        </div>
                        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400">
                            All Expenses
                        </h1>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto mt-4 md:mt-0">
                        <div className="relative w-full sm:w-80 group">
                            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition duration-500 opacity-0 group-hover:opacity-100"></div>
                            <div className="relative flex items-center bg-gray-900/50 backdrop-blur-md rounded-2xl border border-gray-700/50 p-1 shadow-inner focus-within:border-blue-500/50 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
                                <Search className="text-gray-400 ml-3" size={20} />
                                <input
                                    type="text"
                                    placeholder="Search description..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full bg-transparent text-white placeholder-gray-500 px-4 py-2.5 outline-none font-medium"
                                />
                            </div>
                        </div>

                        <div className="relative w-full sm:w-48 group">
                            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition duration-500 opacity-0 group-hover:opacity-100"></div>
                            <div className="relative flex items-center bg-gray-900/50 backdrop-blur-md rounded-2xl border border-gray-700/50 p-1 shadow-inner focus-within:border-blue-500/50 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
                                <Filter className="text-gray-400 ml-3 pointer-events-none" size={20} />
                                <select
                                    value={selectedCategory}
                                    onChange={(e) => setSelectedCategory(e.target.value)}
                                    className="w-full bg-transparent text-white px-4 py-2.5 outline-none font-medium appearance-none cursor-pointer"
                                >
                                    {CATEGORIES.map(cat => (
                                        <option key={cat} value={cat} className="bg-gray-800 text-white">{cat}</option>
                                    ))}
                                </select>
                                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-400 w-0 h-0"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="bg-gray-800/40 backdrop-blur-xl rounded-3xl border border-gray-700/50 p-6 md:p-8 shadow-2xl min-h-[50vh]">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4"></div>
                            <p className="text-gray-400 font-medium tracking-wide">Fetching transactions...</p>
                        </div>
                    ) : filteredTransactions.length > 0 ? (
                        <div className="space-y-4">
                            {filteredTransactions.map((tx) => (
                                <div
                                    key={tx._id}
                                    className="group flex flex-col md:flex-row items-start md:items-center justify-between p-5 rounded-2xl bg-gray-900/40 hover:bg-gray-800/60 border border-gray-800 hover:border-gray-600 transition duration-300 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.3)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.5)] gap-4 relative overflow-hidden"
                                >
                                    <div className="absolute inset-0 translate-x-[-100%] group-hover:translate-x-[100%] bg-gradient-to-r from-transparent via-white/5 to-transparent transition-transform duration-1000 ease-in-out pointer-events-none"></div>

                                    <div className="flex items-center gap-5 w-full md:w-auto relative z-10">
                                        <div
                                            className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-inner flex-shrink-0 ${tx.receipt_id
                                                ? "bg-gradient-to-br from-blue-500/20 to-cyan-500/20 text-blue-400 border border-blue-500/20"
                                                : "bg-gradient-to-br from-purple-500/20 to-pink-500/20 text-purple-400 border border-purple-500/20"
                                                }`}
                                        >
                                            {tx.receipt_id ? <FileText size={24} /> : <Calendar size={24} />}
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <h4 className="text-lg font-bold text-gray-200 group-hover:text-white transition truncate">
                                                {tx.description}
                                            </h4>
                                            <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500 mt-1 font-medium">
                                                <span className={`px-2.5 py-1 rounded-md shadow-inner inline-flex items-center border ${getCategoryColor(tx.category).badgeClasses}`}>
                                                    {tx.category || "Uncategorized"}
                                                </span>
                                                <span className="opacity-50">•</span>
                                                <span className="whitespace-nowrap">{new Date(tx.date).toLocaleDateString("en-US", { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between w-full md:w-auto gap-6 mt-2 md:mt-0 pt-4 md:pt-0 border-t border-gray-800 md:border-none relative z-10">
                                        <div className="text-left md:text-right flex-1">
                                            <span className="block font-extrabold text-white text-xl tracking-tight">
                                                {currencySymbol}{(tx.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                            </span>
                                            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                                                {tx.receipt_id ? "Receipt Source" : "Manual Entry"}
                                            </span>
                                        </div>

                                        <button
                                            onClick={() => handleDelete(tx)}
                                            disabled={deleteLoading === tx._id}
                                            title="Delete transaction"
                                            className="opacity-100 md:opacity-0 group-hover:opacity-100 p-3 rounded-xl bg-red-500/10 hover:bg-red-500/25 text-red-500 hover:text-red-400 border border-red-500/0 hover:border-red-500/30 transition-all duration-300 shadow-inner disabled:opacity-50 flex-shrink-0"
                                        >
                                            {deleteLoading === tx._id ? (
                                                <div className="w-5 h-5 border-2 border-red-500/30 border-t-red-500 rounded-full animate-spin"></div>
                                            ) : (
                                                <Trash2 size={20} />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-20 text-center scale-95 animate-in fade-in duration-500">
                            <div className="w-24 h-24 bg-gray-900/50 rounded-full flex items-center justify-center mb-6 text-gray-600 shadow-inner border border-gray-800">
                                <Search size={40} className="opacity-50" />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-2">No transactions found</h3>
                            <p className="text-gray-500 max-w-sm mx-auto">
                                {searchTerm ? "Try adjusting your search terms to find what you're looking for." : "You haven't added any expenses yet."}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
}
