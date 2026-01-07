import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { Search, FileText, Trash2, Calendar } from 'lucide-react';

export default function ReceiptGallery() {
    const { user } = useAuth();
    const [receipts, setReceipts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [deleteLoading, setDeleteLoading] = useState(null);

    const currencySymbol = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'NPR': 'Rs'
    }[user?.currency || 'USD'] || '$';

    useEffect(() => {
        fetchReceipts();
    }, []);

    const fetchReceipts = async (search = '') => {
        setLoading(true);
        try {
            const res = await api.get(`/receipts?amount=50&search=${search}`);
            setReceipts(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (e) => {
        setSearchTerm(e.target.value);
        // Debounce could be added here, currently searching on explicit fetch or logic update
        // For now let's just search on effect or manual trigger if we had a button, 
        // but simpler: just filter locally or re-fetch. 
        // The previous code passed searchTerm to fetchReceipts. 
        // Let's call fetchReceipts with the new value.
        fetchReceipts(e.target.value);
    };

    // Better search experience: use a separate effect or just trigger on change
    // Using onChange directly in input to trigger fetch might be too aggressive without debounce.
    // Let's stick to the previous pattern or simple local filter if data is small?
    // The previous pattern called fetchReceipts(searchTerm) in handleSearch (which was on form submit).
    // Let's make it real-time with debounce or just simple input change for now.

    const onSearchChange = (e) => {
        const val = e.target.value;
        setSearchTerm(val);
        // Simple debounce manually or just fetch
        fetchReceipts(val);
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

                <div className="relative w-full md:w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search merchant or items..."
                        value={searchTerm}
                        onChange={onSearchChange}
                        className="w-full bg-gray-800 text-white pl-10 pr-4 py-3 rounded-xl border border-gray-700 focus:border-blue-500 outline-none"
                    />
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
                                    <span className="text-white font-bold text-lg drop-shadow-md">{receipt.merchant_name}</span>
                                    <span className="text-green-400 font-mono font-bold bg-green-900/80 px-2 py-1 rounded backdrop-blur-sm">
                                        {currencySymbol}{receipt.total_amount.toFixed(2)}
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
