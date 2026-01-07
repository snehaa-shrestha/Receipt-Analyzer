import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { Search, Trash2, Calendar, CreditCard, ArrowDown, ArrowUp } from 'lucide-react';

export default function Transactions() {
    const { user } = useAuth();
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [deleteLoading, setDeleteLoading] = useState(null);

    const currencySymbol = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'NPR': 'Rs'
    }[user?.currency || 'USD'] || '$';

    useEffect(() => {
        fetchTransactions();
    }, []);

    const fetchTransactions = async () => {
        setLoading(true);
        try {
            // Re-using the get expenses endpoint which returns top 100
            const res = await api.get('/expenses/');
            setTransactions(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (tx) => {
        const isReceipt = tx.type === 'receipt' || tx.receipt_id; // Handle both simplified and original objects if needed
        const endpoint = isReceipt ? `/receipts/${tx._id}` : `/expenses/${tx._id}`;
        const confirmMsg = isReceipt
            ? "Are you sure? This will delete the receipt and all associated items."
            : "Are you sure you want to delete this transaction?";

        if (!confirm(confirmMsg)) return;
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

    const filteredTransactions = transactions.filter(t =>
        t.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        t.category?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <Layout>
            <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
                <header>
                    <h1 className="text-3xl font-bold text-white">All Transactions</h1>
                    <p className="text-gray-400">Manage your manual expenses and receipt items.</p>
                </header>

                <div className="relative w-full md:w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-gray-800 text-white pl-10 pr-4 py-3 rounded-xl border border-gray-700 focus:border-blue-500 outline-none"
                    />
                </div>
            </div>

            {loading ? (
                <div className="text-center text-gray-400 py-20">Loading transactions...</div>
            ) : (
                <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden shadow-xl">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead className="bg-gray-900/50 text-gray-400 text-sm uppercase font-bold">
                                <tr>
                                    <th className="p-6">Description</th>
                                    <th className="p-6">Category</th>
                                    <th className="p-6">Date</th>
                                    <th className="p-6 text-right">Amount</th>
                                    <th className="p-6 text-center">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-700">
                                {filteredTransactions.map((tx) => (
                                    <tr key={tx._id} className="hover:bg-gray-700/30 transition">
                                        <td className="p-6 font-medium text-white flex items-center gap-3">
                                            <div className={`p-2 rounded-lg ${tx.receipt_id ? 'bg-blue-500/10 text-blue-400' : 'bg-purple-500/10 text-purple-400'}`}>
                                                {tx.receipt_id ? <CreditCard size={18} /> : <Calendar size={18} />}
                                            </div>
                                            {tx.description}
                                        </td>
                                        <td className="p-6 text-gray-400">
                                            <span className="bg-gray-900 px-2 py-1 rounded text-xs">{tx.category}</span>
                                        </td>
                                        <td className="p-6 text-gray-400 text-sm">
                                            {new Date(tx.date).toLocaleDateString()}
                                        </td>
                                        <td className="p-6 text-right font-bold text-white">
                                            {currencySymbol}{(tx.amount || 0).toFixed(2)}
                                        </td>
                                        <td className="p-6 text-center">
                                            <button
                                                onClick={() => handleDelete(tx)}
                                                disabled={deleteLoading === tx._id}
                                                className="p-2 hover:bg-red-500/20 text-gray-500 hover:text-red-400 rounded-lg transition"
                                                title="Delete"
                                            >
                                                {deleteLoading === tx._id ? '...' : <Trash2 size={18} />}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {filteredTransactions.length === 0 && (
                        <div className="text-center py-12 text-gray-500">
                            No transactions found.
                        </div>
                    )}
                </div>
            )}
        </Layout>
    );
}
