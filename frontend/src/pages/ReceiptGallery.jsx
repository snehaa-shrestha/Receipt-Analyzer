import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { Search, FileText, Trash2, Calendar, Filter } from 'lucide-react';
import { getCategoryColor } from '../utils/categoryColors';

const CATEGORIES = ["All", "Food", "Groceries", "Transport", "Utilities", "Entertainment", "Shopping", "Other"];

export default function ReceiptGallery() {
    const { user } = useAuth();
    const [receipts, setReceipts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('All');
    const [deleteLoading, setDeleteLoading] = useState(null);

    const currencySymbol = {
        'USD': 'Rs.',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'NPR': 'Rs.'
    }[user?.currency || 'USD'] || 'Rs.';

    useEffect(() => {
        fetchReceipts(searchTerm, selectedCategory);
    }, []);

    const fetchReceipts = async (search = '', category = 'All') => {
        setLoading(true);
        try {
            let url = `/receipts?amount=50`;
            if (search) url += `&search=${search}`;
            if (category && category !== 'All') url += `&category=${category}`;
            const res = await api.get(url);
            setReceipts(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (e) => {
        const val = e.target.value;
        setSearchTerm(val);
        fetchReceipts(val, selectedCategory);
    };

    const onSearchChange = (e) => {
        const val = e.target.value;
        setSearchTerm(val);
        fetchReceipts(val, selectedCategory);
    };

    const onCategoryChange = (e) => {
        const val = e.target.value;
        setSelectedCategory(val);
        fetchReceipts(searchTerm, val);
    };

    const handleDelete = async (id) => {
        if (!confirm("Are you sure you want to delete this receipt? This will also remove associated expenses.")) return;
        setDeleteLoading(id);
        try {
            await api.delete(`/receipts/${id}`);
            setReceipts(receipts.filter(r => r._id !== id));
        } catch (e) {
            console.error(e);
            alert("Failed to delete receipt");
        } finally {
            setDeleteLoading(null);
        }
    };

    return (
        <Layout>
            <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
                <header>
                    <h1 className="text-3xl font-bold text-white">Receipt Gallery</h1>
                    <p className="text-gray-400">Search and manage your digitized receipts.</p>
                </header>

                <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
                    <div className="relative w-full sm:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search merchant or items..."
                            value={searchTerm}
                            onChange={onSearchChange}
                            className="w-full bg-gray-800 text-white pl-10 pr-4 py-3 rounded-xl border border-gray-700 focus:border-blue-500 outline-none"
                        />
                    </div>

                    <div className="relative w-full sm:w-48">
                        <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={18} />
                        <select
                            value={selectedCategory}
                            onChange={onCategoryChange}
                            className="w-full bg-gray-800 text-white pl-10 pr-4 py-3 rounded-xl border border-gray-700 focus:border-blue-500 outline-none appearance-none cursor-pointer"
                        >
                            {CATEGORIES.map(cat => (
                                <option key={cat} value={cat}>{cat}</option>
                            ))}
                        </select>
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-400 w-0 h-0"></div>
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="text-center text-gray-400 py-20">Loading receipts...</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {receipts.map((receipt) => (
                        <div key={receipt._id} className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden shadow-lg group hover:border-blue-500/50 transition relative">
                            <div className="h-48 bg-gray-900 relative overflow-hidden">
                                {receipt.image_url ? (
                                    <img
                                        src={`http://localhost:8000/static/${receipt.image_url.split(/[/\\]/).pop()}`}
                                        alt="Receipt"
                                        className="w-full h-full object-cover transition duration-500 group-hover:scale-110"
                                    />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-gray-700">
                                        <FileText size={48} />
                                    </div>
                                )}
                                <div className="absolute inset-0 bg-gradient-to-t from-gray-900 to-transparent opacity-60"></div>
                                <div className="absolute bottom-3 left-3 right-3 flex justify-between items-end">
                                    <div className="flex flex-col gap-1.5">
                                        <span className="text-white font-bold text-lg drop-shadow-md leading-none">{receipt.merchant_name}</span>
                                        <span className={`text-xs font-bold px-2 py-0.5 rounded backdrop-blur-md border ${getCategoryColor(receipt.category).badgeClasses} w-fit`}>
                                            {receipt.category || 'Uncategorized'}
                                        </span>
                                    </div>
                                    <span className="text-green-400 font-mono font-bold bg-green-900/80 px-2 py-1 rounded backdrop-blur-sm">
                                        {currencySymbol}{(receipt.total_amount || 0).toFixed(2)}
                                    </span>
                                </div>
                            </div>

                            <div className="p-4">
                                <div className="flex justify-between items-center text-sm text-gray-400 mb-4">
                                    <div className="flex items-center gap-2">
                                        <Calendar size={14} />
                                        <span>{new Date(receipt.date_extracted || receipt.uploaded_at).toLocaleDateString()}</span>
                                    </div>
                                    <span>{receipt.items?.length || 0} items</span>
                                </div>

                                <button
                                    onClick={() => handleDelete(receipt._id)}
                                    disabled={deleteLoading === receipt._id}
                                    className="w-full py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition flex items-center justify-center gap-2 text-sm font-medium"
                                >
                                    {deleteLoading === receipt._id ? "Deleting..." : <><Trash2 size={16} /> Delete Receipt</>}
                                </button>
                            </div>
                        </div>
                    ))}

                    {receipts.length === 0 && (
                        <div className="col-span-full text-center py-20 text-gray-500">
                            No receipts found.
                        </div>
                    )}
                </div>
            )}
        </Layout>
    );
}
