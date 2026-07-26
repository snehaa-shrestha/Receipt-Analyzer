import { useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Upload, Check, AlertCircle, Loader, FileImage, Receipt, Tag, Edit3, Trash2, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function UploadReceipt() {
    const navigate = useNavigate();
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [manualCategory, setManualCategory] = useState('');

    const [filename, setFilename] = useState('');
    const [reviewData, setReviewData] = useState(null);
    const [confirming, setConfirming] = useState(false);

    const CATEGORIES = ["Food", "Groceries", "Transport", "Shopping", "Entertainment", "Utilities", "Health", "Other"];

    const handleFileChange = (e) => {
        const selected = e.target.files[0];
        if (selected) {
            setFile(selected);
            setPreview(URL.createObjectURL(selected));
            setReviewData(null);
            setFilename('');
            setError('');
        }
    };

    const handleAnalyze = async () => {
        if (!file) return;

        setLoading(true);
        setError('');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await api.post(`/receipts/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setFilename(res.data.filename);
            const pd = res.data.parsed_data || {};
            
            let dateStr = '';
            if (pd.date_extracted) {
                try { dateStr = new Date(pd.date_extracted).toISOString().split('T')[0]; } catch(e){}
            }
            if(!dateStr) dateStr = new Date().toISOString().split('T')[0];
            
            // Auto-set category from Gemini's suggestion
            if (pd.suggested_category) {
                setManualCategory(pd.suggested_category);
            }

            setReviewData({
                merchant_name: pd.merchant_name || 'Unknown',
                total_amount: pd.total_amount || 0,
                date_extracted: dateStr,
                suggested_category: pd.suggested_category || null,
                items: pd.items || []
            });
        } catch (e) {
            console.error(e);
            setError(e.response?.data?.detail || 'Analysis failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleConfirm = async () => {
        if (!manualCategory) {
            setError("Please select a primary category before saving.");
            return;
        }
        setConfirming(true);
        setError('');
        try {
            const payload = {
                filename: filename,
                merchant_name: reviewData.merchant_name,
                total_amount: parseFloat(reviewData.total_amount) || 0,
                date_extracted: new Date(reviewData.date_extracted).toISOString(),
                category: manualCategory,
                items: reviewData.items.map(i => ({
                    description: i.item_name || i.description || 'Unknown',
                    amount: parseFloat(i.price || i.amount || 0)
                }))
            };
            const res = await api.post('/receipts/confirm', payload);
            navigate('/receipts');
        } catch (e) {
            console.error(e);
            setError(e.response?.data?.detail || 'Confirmation failed.');
        } finally {
            setConfirming(false);
        }
    };

    const updateItem = (index, field, value) => {
        const newItems = [...reviewData.items];
        newItems[index][field] = value;
        setReviewData({ ...reviewData, items: newItems });
    };

    const removeItem = (index) => {
        const newItems = reviewData.items.filter((_, i) => i !== index);
        setReviewData({ ...reviewData, items: newItems });
    };

    const addItem = () => {
        setReviewData({ ...reviewData, items: [...reviewData.items, { item_name: '', price: 0 }] });
    };

    return (
        <Layout>
            <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
                <div className="p-1">
                    <div className="flex items-center gap-2 text-gray-400 text-sm mb-1 font-medium tracking-wide uppercase">
                        <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                        AI Powered Extraction
                    </div>
                    <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">
                        Scan & Review Receipt
                    </h1>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-start">
                    {/* Left Panel: Upload & Preview */}
                    <div className="bg-gray-800/40 backdrop-blur-xl rounded-3xl border border-gray-700/50 p-6 shadow-2xl relative overflow-hidden group/card sticky top-6">
                        <div className="absolute top-0 right-0 p-32 bg-blue-500/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"></div>

                        <div className="relative z-10 space-y-6">
                            <div className="relative group cursor-pointer border-2 border-dashed border-gray-600 hover:border-blue-500 rounded-2xl flex flex-col items-center justify-center min-h-[320px] bg-gray-900/40 hover:bg-gray-800/40 transition-all duration-300 overflow-hidden shadow-inner">
                                {preview ? (
                                    <div className="absolute inset-0 p-4 flex items-center justify-center bg-black/40 backdrop-blur-sm group-hover:bg-black/20 transition duration-300">
                                        <img src={preview} alt="Receipt Preview" className="max-h-full max-w-full object-contain rounded-xl shadow-2xl ring-1 ring-white/10 group-hover:scale-[1.02] transition-transform duration-500" />
                                    </div>
                                ) : (
                                    <div className="text-center p-8 transform group-hover:-translate-y-2 transition-transform duration-300">
                                        <div className="w-20 h-20 bg-gradient-to-b from-gray-700 to-gray-800 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner ring-1 ring-white/5 group-hover:ring-blue-500/50 transition-all duration-300">
                                            <Upload size={36} className="text-blue-400 group-hover:text-blue-300 group-hover:scale-110 transition-all duration-300" />
                                        </div>
                                        <h3 className="text-xl font-bold text-white mb-2">Drag & Drop Receipt</h3>
                                        <p className="text-gray-400 font-medium">Or click to browse your files</p>
                                    </div>
                                )}
                                <input
                                    type="file"
                                    accept="image/*"
                                    onChange={handleFileChange}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                                    title="Click to replace image"
                                />
                            </div>

                            {!reviewData && (
                                <button
                                    onClick={handleAnalyze}
                                    disabled={!file || loading}
                                    className="w-full relative group overflow-hidden bg-gradient-to-r from-blue-600 to-indigo-600 disabled:from-gray-700 disabled:to-gray-800 disabled:text-gray-400 text-white p-4 rounded-xl font-bold text-lg shadow-[0_0_20px_rgba(37,99,235,0.3)] disabled:shadow-none hover:shadow-[0_0_30px_rgba(79,70,229,0.5)] transition-all duration-300 flex items-center justify-center gap-3"
                                >
                                    {loading ? (
                                        <><Loader className="animate-spin" size={24} /><span>Analyzing with AI...</span></>
                                    ) : (
                                        <><Receipt size={24} /><span>Analyze Receipt</span></>
                                    )}
                                </button>
                            )}

                            {error && !reviewData && (
                                <div className="p-4 bg-red-500/10 text-red-400 border border-red-500/20 rounded-xl flex items-start gap-3">
                                    <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
                                    <span className="font-medium">{error}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right Panel: Review Form */}
                    {reviewData ? (
                        <div className="bg-gradient-to-b from-gray-800/60 to-gray-900/60 backdrop-blur-xl rounded-3xl border border-gray-700/50 p-6 md:p-8 shadow-2xl animate-in slide-in-from-right-8 duration-500">
                            <div className="flex items-center gap-3 mb-6 pb-6 border-b border-gray-700/50">
                                <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center text-blue-400">
                                    <Edit3 size={24} />
                                </div>
                                <div>
                                    <h2 className="text-2xl font-bold text-white">Review & Edit</h2>
                                    <p className="text-gray-400 text-sm">Please verify the extracted information below.</p>
                                </div>
                            </div>

                            <div className="space-y-5">
                                {/* Basic Fields */}
                                <div>
                                    <label className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1 block">Merchant Name</label>
                                    <input
                                        type="text"
                                        value={reviewData.merchant_name}
                                        readOnly
                                        className="w-full bg-gray-900/60 text-white p-3 rounded-xl border border-gray-700 outline-none cursor-not-allowed opacity-80"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1 block">Date</label>
                                        <input
                                            type="date"
                                            value={reviewData.date_extracted}
                                            readOnly
                                            className="w-full bg-gray-900/60 text-white p-3 rounded-xl border border-gray-700 outline-none cursor-not-allowed opacity-80 [color-scheme:dark]"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-gray-400 text-xs font-bold uppercase tracking-wider mb-1 block">Total Amount (Rs.)</label>
                                        <input
                                            type="text"
                                            value={reviewData.total_amount}
                                            readOnly
                                            className="w-full bg-gray-900/60 text-white p-3 rounded-xl border border-gray-700 outline-none cursor-not-allowed opacity-80"
                                        />
                                    </div>
                                </div>

                                <div>
                                    {/* <div className="flex items-center justify-between mb-1">
                                        <label className="text-gray-400 text-xs font-bold uppercase tracking-wider">Primary Category</label>
                                        {reviewData.suggested_category && (
                                            <span className="text-xs font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                                                 AI Suggested: {reviewData.suggested_category}
                                            </span>
                                        )}
                                    </div> */}
                                    <select
                                        value={manualCategory}
                                        onChange={e => setManualCategory(e.target.value)}
                                        className="w-full bg-gray-900/60 text-white p-3 rounded-xl border border-indigo-500/50 outline-none font-medium appearance-none cursor-pointer hover:border-indigo-400 transition-colors"
                                    >
                                        <option value="" disabled>Select category...</option>
                                        {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                                    </select>
                                </div>

                                {/* Items Table */}
                                <div>
                                    <div className="flex justify-between items-center mb-3">
                                        <label className="text-gray-400 text-xs font-bold uppercase tracking-wider">
                                            Receipt Items <span className="text-indigo-400 ml-1">({reviewData.items.length})</span>
                                        </label>
                                    </div>

                                    {/* Table header */}
                                    <div className="grid grid-cols-12 gap-2 px-3 py-1.5 mb-1 text-gray-500 text-xs font-bold uppercase tracking-wider">
                                        <span className="col-span-1">#</span>
                                        <span className="col-span-7">Item Name</span>
                                        <span className="col-span-3 text-right">Price (Rs.)</span>
                                        <span className="col-span-1"></span>
                                    </div>

                                    <div className="space-y-1.5 max-h-72 overflow-y-auto custom-scrollbar">
                                        {reviewData.items.map((item, idx) => (
                                            <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-gray-800/40 hover:bg-gray-800/60 px-3 py-2 rounded-xl border border-gray-700/40 transition group">
                                                <span className="col-span-1 text-gray-500 text-xs font-bold">{idx + 1}</span>
                                                <input
                                                    type="text"
                                                    value={item.item_name || item.description || ''}
                                                    readOnly
                                                    className="col-span-7 bg-transparent text-gray-200 outline-none text-sm cursor-default"
                                                />
                                                <input
                                                    type="text"
                                                    value={item.price || item.amount || 0}
                                                    readOnly
                                                    className="col-span-3 bg-gray-900/50 text-white text-right px-2 py-1 rounded-lg border border-gray-700 outline-none text-sm font-mono cursor-default"
                                                />
                                                <div className="col-span-1"></div>
                                            </div>
                                        ))}
                                        {reviewData.items.length === 0 && (
                                            <div className="text-center text-gray-600 text-sm py-6 border border-dashed border-gray-800 rounded-xl">
                                                No items detected from the receipt.
                                            </div>
                                        )}
                                    </div>

                                    {/* Subtotal row */}
                                    {reviewData.items.length > 0 && (
                                        <div className="flex justify-between items-center mt-3 px-3 py-2.5 bg-gray-900/60 rounded-xl border border-gray-700/50">
                                            <span className="text-gray-400 text-sm font-bold">Items Subtotal</span>
                                            <span className="text-white font-mono font-bold">
                                                Rs. {reviewData.items.reduce((sum, i) => sum + parseFloat(i.price || i.amount || 0), 0).toFixed(2)}
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {error && (
                                    <div className="p-3 bg-red-500/10 text-red-400 border border-red-500/20 rounded-xl text-sm flex gap-2 items-center">
                                        <AlertCircle size={16} /> {error}
                                    </div>
                                )}

                                <div className="pt-4 flex gap-4">
                                    <button
                                        onClick={() => setReviewData(null)}
                                        className="px-6 py-3 rounded-xl font-bold text-gray-300 hover:bg-gray-800 transition"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleConfirm}
                                        disabled={confirming}
                                        className="flex-1 bg-green-500 hover:bg-green-400 text-black px-6 py-3 rounded-xl font-bold transition flex justify-center items-center gap-2"
                                    >
                                        {confirming ? <Loader className="animate-spin" size={20} /> : <Check size={20} />}
                                        {confirming ? 'Saving...' : 'Confirm & Save'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="hidden lg:flex flex-col items-center justify-center h-full min-h-[500px] border-2 border-dashed border-gray-800 rounded-3xl opacity-50">
                            <Receipt size={48} className="text-gray-700 mb-6" />
                            <p className="text-gray-500 font-medium text-lg max-w-xs text-center">
                                Upload a receipt to review the extracted data here
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
}
