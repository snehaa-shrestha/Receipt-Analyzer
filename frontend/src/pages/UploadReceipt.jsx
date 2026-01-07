import { useState } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Upload, Check, AlertCircle, Loader } from 'lucide-react';

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
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Send only category, date will be auto-detected by OCR
            const queryParams = new URLSearchParams();
            if (manualCategory) queryParams.append('manual_category', manualCategory);

            const res = await api.post(`/receipts/upload?${queryParams.toString()}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setResult(res.data);
        } catch (e) {
            setError('Upload failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-white">Upload Receipt</h1>
                <p className="text-gray-400">Scan and analyze your expenses automatically.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Upload Section */}
                <div className="bg-gray-800 p-8 rounded-2xl border border-gray-700 shadow-lg">
                    <div className="border-2 border-dashed border-gray-600 rounded-xl p-8 flex flex-col items-center justify-center min-h-[300px] hover:border-blue-500 transition-colors relative">
                        {preview ? (
                            <img src={preview} alt="Preview" className="max-h-64 rounded shadow-lg mb-4" />
                        ) : (
                            <div className="text-center">
                                <div className="bg-gray-700 p-4 rounded-full inline-block mb-4">
                                    <Upload size={32} className="text-blue-400" />
                                </div>
                                <p className="text-gray-300 font-medium">Click to selecting receipt image</p>
                                <p className="text-gray-500 text-sm mt-2">JPG, PNG supported</p>
                            </div>
                        )}
                        <input
                            type="file"
                            accept="image/*"
                            onChange={handleFileChange}
                            className="absolute inset-0 opacity-0 cursor-pointer"
                        />
                    </div>

                    <div className="mt-6">
                        <div>
                            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Category <span className="text-red-500">*</span></label>
                            <select
                                value={manualCategory}
                                onChange={(e) => setManualCategory(e.target.value)}
                                className="w-full bg-gray-700 text-white rounded-lg p-3 border border-gray-600 focus:border-blue-500 outline-none"
                            >
                                <option value="">Choose Category</option>
                                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                            <p className="text-xs text-gray-400 mt-1">Date will be automatically detected from receipt</p>
                        </div>
                    </div>

                    <button
                        onClick={handleUpload}
                        disabled={!file || !manualCategory || loading}
                        className="w-full mt-6 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white py-3 rounded-xl font-semibold transition flex items-center justify-center gap-2"
                    >
                        {loading ? <Loader className="animate-spin" /> : <Upload size={20} />}
                        {loading ? 'Analyze Receipt' : 'Analyze Receipt'}
                    </button>

                    {error && (
                        <div className="mt-4 p-4 bg-red-500/10 text-red-500 rounded-xl flex items-center gap-2">
                            <AlertCircle size={20} />
                            {error}
                        </div>
                    )}
                </div>

                {/* Results Section */}
                {result && (
                    <div className="bg-gray-800 p-8 rounded-2xl border border-gray-700 shadow-lg animate-fade-in">
                        <div className="flex items-center gap-2 mb-6 text-green-400">
                            <div className="bg-green-400/20 p-2 rounded-full"><Check size={20} /></div>
                            <h2 className="text-xl font-bold">Analysis Complete</h2>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <label className="text-gray-500 text-sm">Merchant</label>
                                <p className="text-2xl font-bold text-white">{result.parsed_data.merchant_name}</p>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 bg-gray-700/50 rounded-xl">
                                    <label className="text-gray-500 text-sm">Total Amount</label>
                                    <p className="text-xl font-bold text-white">${result.parsed_data.total_amount?.toFixed(2)}</p>
                                </div>
                                <div className="p-4 bg-gray-700/50 rounded-xl">
                                    <label className="text-gray-500 text-sm">Date</label>
                                    <p className="text-xl font-bold text-white">
                                        {result.parsed_data.date_extracted ? new Date(result.parsed_data.date_extracted).toLocaleDateString() : 'N/A'}
                                    </p>
                                </div>
                            </div>


                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
}
