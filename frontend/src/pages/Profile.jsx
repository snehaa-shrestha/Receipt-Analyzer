import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { User, DollarSign, Save, Loader, Mail, Wallet, CreditCard } from 'lucide-react';

export default function Profile() {
    const { user, updateUser } = useAuth();
    const [profile, setProfile] = useState({
        username: '',
        email: '',
        full_name: '',
        monthly_budget: 0,
        currency: 'USD'
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);

    useEffect(() => {
        fetchProfile();
    }, []);

    const fetchProfile = async () => {
        try {
            const res = await api.get('/users/me');
            setProfile(res.data);
            updateUser(res.data); // Keep context in sync
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        setProfile({ ...profile, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        setMessage(null);
        try {
            await api.put('/users/me', {
                full_name: profile.full_name,
                monthly_budget: parseFloat(profile.monthly_budget),
                currency: profile.currency
            });
            updateUser({
                full_name: profile.full_name,
                monthly_budget: parseFloat(profile.monthly_budget),
                currency: profile.currency
            });
            setMessage({ type: 'success', text: 'Profile updated successfully!' });

            // Clear message after 3 seconds
            setTimeout(() => setMessage(null), 3000);
        } catch (e) {
            setMessage({ type: 'error', text: 'Failed to update profile.' });
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <Layout><div className="flex justify-center py-20"><Loader className="animate-spin text-blue-500" /></div></Layout>;

    return (
        <Layout>
            <div className="max-w-5xl mx-auto">
                <header className="mb-8">
                    <h1 className="text-3xl font-bold text-white">Account Settings</h1>
                    <p className="text-gray-400">Manage your profile and financial preferences.</p>
                </header>

                {/* Identity Card */}
                <div className="bg-gray-800 p-8 rounded-2xl border border-gray-700 shadow-lg mb-8 flex flex-col md:flex-row items-center md:items-start gap-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>

                    <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-3xl font-bold text-white shadow-xl ring-4 ring-gray-900 z-10">
                        {profile.username?.slice(0, 2).toUpperCase()}
                    </div>

                    <div className="flex-1 text-center md:text-left z-10">
                        <h2 className="text-2xl font-bold text-white mb-1">{profile.username}</h2>
                        <div className="flex items-center justify-center md:justify-start gap-2 text-gray-400 mb-4">
                            <Mail size={16} /> {profile.email}
                        </div>
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-sm border border-blue-500/20">
                            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
                            Active Member
                        </div>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-8">
                    <div className="grid md:grid-cols-2 gap-8">

                        {/* Personal Information */}
                        <div className="bg-gray-800 p-6 rounded-2xl border border-gray-700 shadow-lg">
                            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                                <User className="text-blue-400" size={24} />
                                Personal Details
                            </h3>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-gray-400 text-sm mb-2 font-medium">Full Name</label>
                                    <input
                                        type="text"
                                        name="full_name"
                                        value={profile.full_name || ''}
                                        onChange={handleChange}
                                        className="w-full bg-gray-900 text-white p-4 rounded-xl border border-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition"
                                        placeholder="e.g. John Doe"
                                    />
                                </div>
                                <div>
                                    <label className="block text-gray-400 text-sm mb-2 font-medium">Display Name (Username)</label>
                                    <input
                                        type="text"
                                        value={profile.username}
                                        disabled
                                        className="w-full bg-gray-900/50 text-gray-500 p-4 rounded-xl border border-gray-700 cursor-not-allowed"
                                    />
                                    <p className="text-xs text-gray-500 mt-1">Username cannot be changed.</p>
                                </div>
                            </div>
                        </div>

                        {/* Financial Preferences */}
                        <div className="bg-gray-800 p-6 rounded-2xl border border-gray-700 shadow-lg">
                            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                                <Wallet className="text-purple-400" size={24} />
                                Financial Goals
                            </h3>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-gray-400 text-sm mb-2 font-medium">Monthly Budget Limit</label>
                                    <div className="relative">
                                        <DollarSign size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                                        <input
                                            type="number"
                                            name="monthly_budget"
                                            value={profile.monthly_budget || 0}
                                            onChange={handleChange}
                                            className="w-full bg-gray-900 text-white p-4 pl-12 rounded-xl border border-gray-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition"
                                            placeholder="2000.00"
                                        />
                                    </div>
                                    <p className="text-xs text-gray-500 mt-1">We'll alert you if you exceed this amount.</p>
                                </div>

                                <div>
                                    <label className="block text-gray-400 text-sm mb-2 font-medium">Preferred Currency</label>
                                    <div className="relative">
                                        <CreditCard size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                                        <select
                                            name="currency"
                                            value={profile.currency || 'USD'}
                                            onChange={handleChange}
                                            className="w-full bg-gray-900 text-white p-4 pl-12 rounded-xl border border-gray-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none appearance-none transition"
                                        >
                                            <option value="USD">USD ($) - US Dollar</option>
                                            <option value="EUR">EUR (€) - Euro</option>
                                            <option value="GBP">GBP (£) - British Pound</option>
                                            <option value="JPY">JPY (¥) - Japanese Yen</option>
                                            <option value="NPR">NPR (Rs) - Nepalese Rupee</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Action Bar */}
                    <div className="flex items-center justify-between bg-gray-800 p-6 rounded-2xl border border-gray-700 shadow-lg sticky bottom-6 z-20">
                        <div>
                            {message && (
                                <span className={`text-sm font-medium ${message.type === 'success' ? 'text-green-400' : 'text-red-400'} animate-fade-in`}>
                                    {message.text}
                                </span>
                            )}
                        </div>
                        <button
                            type="submit"
                            disabled={saving}
                            className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white px-8 py-3 rounded-xl font-bold shadow-lg shadow-blue-900/40 transition transform hover:scale-105 disabled:opacity-50 disabled:transform-none"
                        >
                            {saving ? <Loader className="animate-spin" size={20} /> : <><Save size={20} /> Save Changes</>}
                        </button>
                    </div>

                </form>
            </div>
        </Layout>
    );
}
