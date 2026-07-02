import { useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Upload, Check, AlertCircle, Loader, FileImage, Receipt, Tag } from 'lucide-react';
import { getCategoryColor } from '../utils/categoryColors';

export default function UploadReceipt() {
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [manualCategory, setManualCategory] = useState('');

    const CATEGORIES = ["Food", "Transport", "Shopping", "Entertainment", "Utilities", "Health", "Other"];

    const handleFileChange = (e) => {
        const selected = e.target.files[0];
        if (selected) {
            setFile(selected);
            setPreview(URL.createObjectURL(selected));
            setResult(null);
            setError('');
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setLoading(true);
        setError('');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const queryParams = new URLSearchParams();
            if (manualCategory) queryParams.append('manual_category', manualCategory);

            const res = await api.post(`/receipts/upload?${queryParams.toString()}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setResult(res.data);
        } catch (e) {
            console.error(e);
            setError(e.response?.data?.detail || 'Upload failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
                <div className="p-1">
                    <div className="flex items-center gap-2 text-gray-400 text-sm mb-1 font-medium tracking-wide uppercase">
                        <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                        AI Powered Extraction
                    </div>
                    <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">
                        Scan Receipt
                    </h1>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-start">
                    <div className="bg-gray-800/40 backdrop-blur-xl rounded-3xl border border-gray-700/50 p-6 md:p-8 shadow-2xl relative overflow-hidden group/card">
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
                                        <div className="mt-6 flex items-center justify-center gap-4 text-xs font-semibold tracking-wider text-gray-500 uppercase">
                                            <span className="flex items-center gap-1"><FileImage size={14} /> JPG</span>
                                            <span className="flex items-center gap-1"><FileImage size={14} /> PNG</span>
                                        </div>
                                    </div>
                                )}
                                <input
                                    type="file"
                                    accept="image/*"
                                    onChange={handleFileChange}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="flex items-center justify-between text-sm font-bold text-gray-300 uppercase tracking-wider">
                                    <span className="flex items-center gap-2"><Tag size={16} className="text-blue-400" /> Primary Category</span>
                                    <span className="text-xs text-blue-400/80 font-medium normal-case bg-blue-500/10 px-2.5 py-1 rounded-full">Required</span>
                                </label>
                                <div className="relative">
                                    <select
                                        value={manualCategory}
                                        onChange={(e) => setManualCategory(e.target.value)}
                                        className="w-full bg-gray-900/60 backdrop-blur-sm text-white rounded-xl p-4 border border-gray-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none appearance-none font-medium shadow-inner transition-all duration-200 cursor-pointer"
                                        disabled={loading}
                                    >
                                        <option value="" disabled className="text-gray-500">Select a category for this receipt...</option>
                                        {CATEGORIES.map(c => <option key={c} value={c} className="bg-gray-800">{c}</option>)}
                                    </select>
                                    <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none text-gray-400">
                                        ▼
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={handleUpload}
                                disabled={!file || !manualCategory || loading}
                                className="w-full relative group overflow-hidden bg-gradient-to-r from-blue-600 to-indigo-600 disabled:from-gray-700 disabled:to-gray-800 disabled:text-gray-400 text-white p-4 rounded-xl font-bold text-lg shadow-[0_0_20px_rgba(37,99,235,0.3)] disabled:shadow-none hover:shadow-[0_0_30px_rgba(79,70,229,0.5)] transition-all duration-300 flex items-center justify-center gap-3"
                            >
                                <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-[100%] group-hover:translate-x-[100%] transition-transform duration-1000 ease-in-out"></div>
                                {loading ? (
                                    <>
                                        <Loader className="animate-spin" size={24} />
                                        <span>Analyzing Receipt...</span>
                                    </>
                                ) : (
                                    <>
                                        <Receipt size={0} />
                                        <span>Analyze & Extract</span>
                                    </>
                                )}
                            </button>

                            {error && (
                                <div className="p-4 bg-red-500/10 text-red-400 border border-red-500/20 rounded-xl flex items-start gap-3 animate-in slide-in-from-bottom-2">
                                    <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
                                    <span className="font-medium">{error}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {result ? (
                        <div className="bg-gradient-to-b from-gray-800/60 to-gray-900/60 backdrop-blur-xl rounded-3xl border border-gray-700/50 p-8 shadow-2xl animate-in slide-in-from-right-8 duration-500 relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-green-400 to-emerald-500"></div>

                            <div className="flex flex-col items-center text-center border-b border-gray-700/50 pb-8 mb-8">
                                <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-emerald-600 rounded-full flex items-center justify-center text-white shadow-[0_0_30px_rgba(52,211,153,0.3)] mb-4 ring-4 ring-green-500/20">
                                    <Check size={32} strokeWidth={3} />
                                </div>
                                <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">Success!</h2>
                                <p className="text-emerald-400 font-medium tracking-wide">Receipt analyzed and saved to your account</p>
                            </div>

                            <div className="space-y-6">
                                <div className="bg-gray-900/50 rounded-2xl p-6 border border-gray-700/50 shadow-inner flex justify-between items-center">
                                    <div>
                                        <label className="text-gray-500 text-sm font-bold uppercase tracking-wider block mb-2">Merchant Name</label>
                                        <p className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400">
                                            {result.parsed_data.merchant_name || 'Unknown Merchant'}
                                        </p>
                                    </div>
                                    {/* <div className="text-right">
                                        <label className="text-gray-500 text-sm font-bold uppercase tracking-wider block mb-2">Category</label>
                                        <span className={`px-3 py-1.5 rounded-lg border font-bold text-sm ${getCategoryColor(result.parsed_data.category).badgeClasses}`}>
                                            {result.parsed_data.category || 'Uncategorized'}
                                        </span>
                                    </div> */}
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-gray-900/50 rounded-2xl p-6 border border-gray-700/50 shadow-inner">
                                        <label className="text-gray-500 text-sm font-bold uppercase tracking-wider block mb-2">Total Amount</label>
                                        <p className="text-3xl font-bold text-white tracking-tight">
                                            <span className="text-gray-500 mr-1">Rs.</span>
                                            {result.parsed_data.total_amount?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                                        </p>
                                    </div>
                                    <div className="bg-gray-900/50 rounded-2xl p-6 border border-gray-700/50 shadow-inner">
                                        <label className="text-gray-500 text-sm font-bold uppercase tracking-wider block mb-2">Date Filtered</label>
                                        <p className="text-xl font-bold text-gray-200 mt-2">
                                            {result.parsed_data.date_extracted
                                                ? new Date(result.parsed_data.date_extracted).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
                                                : 'Today'}
                                        </p>
                                    </div>
                                </div>

                                <button
                                    onClick={() => {
                                        setFile(null);
                                        setPreview(null);
                                        setResult(null);
                                        setManualCategory('');
                                    }}
                                    className="w-full text-center py-4 text-gray-400 hover:text-white font-semibold transition-colors mt-4"
                                >
                                    Scan Another Receipt
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="hidden lg:flex flex-col items-center justify-center h-full min-h-[500px] border-2 border-dashed border-gray-800 rounded-3xl opacity-50">
                            <Receipt size={0} className="text-gray-700 mb-6" />
                            <p className="text-gray-500 font-medium text-lg max-w-xs text-center">
                                Your analysis results will appear here
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
}
