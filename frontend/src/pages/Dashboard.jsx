import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { useEffect, useState } from 'react';
import api from '../api/axios';
import {
    TrendingUp, Wallet, ArrowUpRight, TrendingDown, AlertTriangle,
    FileText, Plus, Download, CreditCard, Calendar, ArrowRight,
    PieChart as PieChartIcon, Activity, DollarSign, Flame, Sparkles
} from 'lucide-react';
import {
    RadialBarChart, RadialBar, ResponsiveContainer, Tooltip as RechartsTooltip,
    Legend, Cell, PieChart, Pie
} from 'recharts';
import { Link } from 'react-router-dom';

export default function Dashboard() {
    const { user, logout } = useAuth();
    const [stats, setStats] = useState({ spent: 0, budget: 0, points: 0, forecast: 0, streak: 0 });
    const [budgets, setBudgets] = useState([]);
    const [chartData, setChartData] = useState([]);
    const [recentTx, setRecentTx] = useState([]);
    const [showAddModal, setShowAddModal] = useState(false);
    const [loading, setLoading] = useState(true);
    const [showAIModal, setShowAIModal] = useState(false);

    // Month/Year selector state
    const now = new Date();
    const [selectedYear, setSelectedYear] = useState(now.getFullYear());
    const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1); // 1-12

    const currencySymbol = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'NPR': 'Rs'
    }[user?.currency || 'USD'] || '$';

    const COLORS = ['#8B5CF6', '#EC4899', '#3B82F6', '#10B981', '#F59E0B'];

    const fetchData = async (year = selectedYear, month = selectedMonth) => {
        try {
            const [gameRes, budgetRes, expenseRes, forecastRes, summaryRes] = await Promise.all([
                api.get('/game/progress'),
                api.get('/budgets/status'),
                api.get(`/expenses/recent-transactions?year=${year}&month=${month}`),
                api.get('/expenses/forecast'),
                api.get(`/expenses/summary?period=month&year=${year}&month=${month}`)
            ]);

            const totalSpent = summaryRes.data.reduce((acc, curr) => acc + curr.total, 0);
            const globalBudget = user?.monthly_budget || 0;
            const categoryBudgetTotal = budgetRes.data.reduce((acc, curr) => acc + curr.limit, 0);
            const totalLimit = globalBudget > 0 ? globalBudget : categoryBudgetTotal;

            setStats({
                spent: totalSpent,
                budget: totalLimit,
                points: gameRes.data.points,
                forecast: forecastRes.data.predicted_amount || 0,
                streak: gameRes.data.streak_count || 0
            });

            setBudgets(budgetRes.data);
            setChartData(summaryRes.data.map(item => ({ name: item._id, value: item.total })));
            setRecentTx(expenseRes.data.slice(0, 5));

        } catch (e) {
            console.error(e);
            if (e.response?.status === 401) logout();
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (user) fetchData();
    }, [user, logout]);

    // Refetch when month/year changes
    useEffect(() => {
        if (user) fetchData(selectedYear, selectedMonth);
    }, [selectedYear, selectedMonth]);

    const handleExport = async () => {
        try {
            const response = await api.get('/expenses/export', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'expenses_report.csv');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (e) { alert("Export failed"); }
    }

    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return "Good Morning";
        if (hour < 18) return "Good Afternoon";
        return "Good Evening";
    };

    const remaining = stats.budget - stats.spent;
    const progress = Math.min((stats.spent / (stats.budget || 1)) * 100, 100);

    const handleAIAdvice = () => {
        setShowAIModal(true);
    };

    return (
        <Layout>
            <div className="max-w-7xl mx-auto space-y-8">
                {/* Header Section */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 p-1">
                    <div>
                        <div className="flex items-center gap-2 text-gray-400 text-sm mb-1 font-medium tracking-wide uppercase">
                            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                            Financial Overview
                        </div>
                        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400">
                            {getGreeting()}, {user?.username}
                        </h1>
                    </div>
                    <div className="flex gap-3">
                        <button onClick={handleExport} className="group bg-gray-900/50 hover:bg-gray-800 text-gray-300 border border-gray-700/50 px-5 py-2.5 rounded-xl font-medium transition flex items-center gap-2 backdrop-blur-md">
                            <Download size={18} className="group-hover:-translate-y-0.5 transition-transform" />
                            <span>Export</span>
                        </button>
                        <button onClick={handleAIAdvice} className="group bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 px-5 py-2.5 rounded-xl font-medium transition flex items-center gap-2 backdrop-blur-md">
                            <Sparkles size={18} className="group-hover:scale-110 transition-transform" />
                            <span>AI Insights</span>
                        </button>
                        <button onClick={() => setShowAddModal(true)} className="group bg-white hover:bg-gray-100 text-black px-5 py-2.5 rounded-xl font-bold transition flex items-center gap-2 shadow-[0_0_20px_rgba(255,255,255,0.15)]">
                            <Plus size={18} className="group-hover:rotate-90 transition-transform duration-300" />
                            <span>New Expense</span>
                        </button>
                    </div>
                </div>

                {/* Hero Stats Section */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Main Balance Card */}
                    <div className="lg:col-span-2 relative overflow-hidden bg-gradient-to-br from-indigo-600 to-violet-700 rounded-3xl p-8 shadow-2xl text-white">
                        <div className="absolute top-0 right-0 p-32 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"></div>
                        <div className="absolute bottom-0 left-0 p-24 bg-black/10 rounded-full blur-2xl -ml-16 -mb-16 pointer-events-none"></div>

                        <div className="relative z-10 flex flex-col h-full justify-between">
                            {stats.budget === 0 ? (
                                <div className="text-center py-8">
                                    <p className="text-indigo-200 mb-4">No monthly budget set</p>
                                    <Link to="/profile" className="inline-block bg-white text-indigo-600 px-6 py-3 rounded-xl font-bold hover:bg-indigo-50 transition">
                                        Set Your Budget
                                    </Link>
                                </div>
                            ) : (
                                <>
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="text-indigo-200 font-medium mb-1 flex items-center gap-2">
                                                <Wallet size={16} /> Monthly Budget
                                            </p>
                                            <h2 className="text-5xl font-bold tracking-tight">{currencySymbol}{stats.budget.toLocaleString()}</h2>
                                            <p className="text-indigo-300 text-sm mt-1 font-medium">
                                                {new Date(selectedYear, selectedMonth - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                                            </p>
                                        </div>
                                        <div className="text-right">
                                            <p className={`font-medium mb-1 ${remaining < 0 ? 'text-red-200' : 'text-indigo-200'}`}>
                                                {remaining < 0 ? 'Overspent' : 'Remaining'}
                                            </p>
                                            <h3 className={`text-3xl font-bold flex items-center justify-end gap-2 ${remaining < 0 ? 'text-red-300' : 'text-emerald-300'}`}>
                                                {remaining < 0 ? <TrendingDown size={28} /> : <TrendingUp size={28} />}
                                                {currencySymbol}{Math.abs(remaining).toLocaleString()}
                                            </h3>
                                        </div>
                                    </div>

                                    <div className="mt-8">
                                        <div className="flex justify-between text-sm font-medium mb-2 text-indigo-100">
                                            <span>{progress.toFixed(0)}% Utilized</span>
                                            <span>{currencySymbol}{stats.spent.toLocaleString()} Spent</span>
                                        </div>
                                        <div className="h-4 bg-black/20 rounded-full overflow-hidden backdrop-blur-sm">
                                            <div
                                                className={`h-full rounded-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(255,255,255,0.3)] ${progress > 100 ? 'bg-red-400' : 'bg-white'}`}
                                                style={{ width: `${progress}%` }}
                                            ></div>
                                        </div>
                                    </div>

                                    {/* Month/Year Selector */}
                                    <div className="mt-6 pt-6 border-t border-white/20">
                                        <p className="text-indigo-200 text-sm mb-3 font-medium">View by Month</p>
                                        <div className="flex gap-3">
                                            <select
                                                value={selectedMonth}
                                                onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                                                className="flex-1 bg-gray-900/30 text-white border border-white/20 rounded-xl px-4 py-2.5 font-medium focus:outline-none focus:ring-2 focus:ring-white/30 backdrop-blur-sm"
                                            >
                                                <option value="1">January</option>
                                                <option value="2">February</option>
                                                <option value="3">March</option>
                                                <option value="4">April</option>
                                                <option value="5">May</option>
                                                <option value="6">June</option>
                                                <option value="7">July</option>
                                                <option value="8">August</option>
                                                <option value="9">September</option>
                                                <option value="10">October</option>
                                                <option value="11">November</option>
                                                <option value="12">December</option>
                                            </select>
                                            <select
                                                value={selectedYear}
                                                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                                                className="bg-gray-900/30 text-white border border-white/20 rounded-xl px-4 py-2.5 font-medium focus:outline-none focus:ring-2 focus:ring-white/30 backdrop-blur-sm"
                                            >
                                                {[...Array(5)].map((_, i) => {
                                                    const year = new Date().getFullYear() - i;
                                                    return <option key={year} value={year}>{year}</option>;
                                                })}
                                            </select>
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Quick Stats Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-6">
                        <div className="bg-gray-800/60 backdrop-blur-xl p-6 rounded-3xl border border-gray-700/50 hover:border-gray-600 transition group">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-pink-500/10 rounded-2xl text-pink-400 group-hover:scale-110 transition-transform">
                                    <Activity size={24} />
                                </div>
                                <span className="text-xs font-medium text-gray-500 bg-gray-900/50 px-2 py-1 rounded-lg">AI Forecast</span>
                            </div>
                            <h3 className="text-3xl font-bold text-white mb-1">
                                {stats.forecast > 0 ? `${currencySymbol}${stats.forecast.toLocaleString()}` : <span className="text-xl text-gray-400">Gathering Data...</span>}
                            </h3>
                            <p className="text-gray-400 text-sm">Projected spend next month</p>
                        </div>

                        <div className="bg-gray-800/60 backdrop-blur-xl p-6 rounded-3xl border border-gray-700/50 hover:border-gray-600 transition group">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-blue-500/10 rounded-2xl text-blue-400 group-hover:scale-110 transition-transform">
                                    <PieChartIcon size={24} />
                                </div>
                                <span className="text-xs font-medium text-gray-500 bg-gray-900/50 px-2 py-1 rounded-lg">Top Category</span>
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-1 truncate">
                                {chartData.length > 0 ? chartData.sort((a, b) => b.value - a.value)[0].name : 'N/A'}
                            </h3>
                            <p className="text-gray-400 text-sm">Most expense this month</p>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Recent Transactions List */}
                    <div className="lg:col-span-2 bg-gray-800/40 backdrop-blur-md rounded-3xl border border-gray-700/50 p-6 shadow-xl">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                <CreditCard size={20} className="text-gray-400" /> Recent Activity
                            </h3>
                            <Link to="/transactions" className="text-sm font-medium text-blue-400 hover:text-blue-300 flex items-center gap-1 transition">
                                View All <ArrowRight size={14} />
                            </Link>
                        </div>

                        <div className="space-y-3">
                            {recentTx.length > 0 ? recentTx.map((tx, idx) => (
                                <div key={idx} className="group flex items-center justify-between p-4 rounded-2xl bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 hover:border-gray-600 transition duration-300">
                                    <div className="flex items-center gap-4">
                                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-lg shadow-inner ${tx.receipt_id ? 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20 text-blue-400' : 'bg-gradient-to-br from-purple-500/20 to-pink-500/20 text-purple-400'}`}>
                                            {tx.receipt_id ? <FileText size={20} /> : <CreditCard size={20} />}
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-gray-200 group-hover:text-white transition">{tx.description}</h4>
                                            <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                                                <span className="bg-gray-900 px-2 py-0.5 rounded text-gray-400">{tx.category || "Uncategorized"}</span>
                                                <span>•</span>
                                                <span>{new Date(tx.date).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <span className="block font-bold text-white text-lg">{currencySymbol}{(tx.amount || 0).toFixed(2)}</span>
                                        <span className="text-xs text-gray-500">{tx.receipt_id ? 'Receipt' : 'Manual'}</span>
                                    </div>
                                </div>
                            )) : (
                                <div className="text-center py-10 text-gray-500 italic">No recent transactions found</div>
                            )}
                        </div>
                    </div>

                    {/* Right Column: Breakdown & Budgets */}
                    <div className="space-y-6">
                        {/* Spending Breakdown Donut */}
                        <div className="bg-gray-800/40 backdrop-blur-md rounded-3xl border border-gray-700/50 p-6 shadow-xl flex flex-col">
                            <h3 className="text-lg font-bold text-white mb-4">Spending Breakdown</h3>
                            <div className="h-64 flex-1 relative">
                                {chartData.length > 0 ? (
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={chartData}
                                                cx="50%" cy="50%"
                                                innerRadius={60}
                                                outerRadius={80}
                                                paddingAngle={5}
                                                dataKey="value"
                                            >
                                                {chartData.map((entry, index) => (
                                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <RechartsTooltip
                                                contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', color: '#F3F4F6', borderRadius: '0.75rem' }}
                                                formatter={(val) => `${currencySymbol}${val.toLocaleString()}`}
                                            />
                                            <Legend
                                                verticalAlign="middle"
                                                align="right"
                                                layout="vertical"
                                                iconType="circle"
                                            />
                                        </PieChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <div className="h-full flex flex-col items-center justify-center text-gray-500 text-sm">
                                        <PieChartIcon size={32} className="mb-2 opacity-50" />
                                        <span>No data yet</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Mini Budgets List */}
                        <div className="bg-gray-800/40 backdrop-blur-md rounded-3xl border border-gray-700/50 p-6 shadow-xl">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-lg font-bold text-white">Budgets</h3>
                                <Link to="/profile" className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition">
                                    <ArrowUpRight size={16} className="text-gray-400" />
                                </Link>
                            </div>
                            <div className="space-y-4 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
                                {budgets.map((b, idx) => (
                                    <div key={idx} className="group">
                                        <div className="flex justify-between items-end mb-1">
                                            <span className="text-sm font-medium text-gray-300">{b.category}</span>
                                            <span className={`text-xs font-bold ${b.alert ? 'text-red-400' : 'text-gray-400'}`}>
                                                {currencySymbol}{b.spent.toFixed(0)} / {currencySymbol}{b.limit}
                                            </span>
                                        </div>
                                        <div className="h-1.5 w-full bg-gray-700 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full rounded-full transition-all duration-500 ${b.alert ? 'bg-red-500' : 'bg-indigo-500 group-hover:bg-indigo-400'}`}
                                                style={{ width: `${Math.min((b.spent / b.limit) * 100, 100)}%` }}
                                            ></div>
                                        </div>
                                    </div>
                                ))}
                                {budgets.length === 0 && <p className="text-gray-500 text-xs text-center py-4">No specific budgets set</p>}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Add Expense Modal */}
            {showAddModal && <AddExpenseModal onClose={() => setShowAddModal(false)} refresh={fetchData} currencySymbol={currencySymbol} />}

            {/* AI Advisor Modal */}
            {showAIModal && (
                <AIAdvisorModal
                    onClose={() => setShowAIModal(false)}
                    year={selectedYear}
                    setYear={setSelectedYear}
                    month={selectedMonth}
                    setMonth={setSelectedMonth}
                />
            )}
        </Layout>
    );
}

function AIAdvisorModal({ onClose, year, setYear, month, setMonth }) {
    const [loading, setLoading] = useState(false);
    const [advice, setAdvice] = useState(null);

    useEffect(() => {
        const fetchAdvice = async () => {
            setLoading(true);
            setAdvice(null);
            try {
                const res = await api.get(`/ai/advice?year=${year}&month=${month}`);
                setAdvice(res.data);
            } catch (e) {
                console.error(e);
                setAdvice({ raw_advice: "Failed to load advice. Please try again." });
            } finally {
                setLoading(false);
            }
        };
        fetchAdvice();
    }, [year, month]);

    const periodName = `${new Date(year, month - 1).toLocaleString('default', { month: 'long' })} ${year}`;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-gray-900 w-full max-w-2xl rounded-3xl border border-gray-700 shadow-2xl p-8 scale-100 animate-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto custom-scrollbar">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400">
                            <Sparkles size={24} />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white">AI Financial Advisor</h2>
                            {/* Interactive Date Selectors */}
                            <div className="flex items-center gap-2 mt-1">
                                <select
                                    value={month}
                                    onChange={(e) => setMonth(parseInt(e.target.value))}
                                    className="bg-gray-800 text-indigo-400 text-sm font-medium border-none rounded focus:ring-0 cursor-pointer py-0 pl-0 pr-6"
                                >
                                    {[...Array(12)].map((_, i) => (
                                        <option key={i + 1} value={i + 1}>{new Date(0, i).toLocaleString('default', { month: 'long' })}</option>
                                    ))}
                                </select>
                                <select
                                    value={year}
                                    onChange={(e) => setYear(parseInt(e.target.value))}
                                    className="bg-gray-800 text-indigo-400 text-sm font-medium border-none rounded focus:ring-0 cursor-pointer py-0 pl-0 pr-6"
                                >
                                    {[...Array(5)].map((_, i) => {
                                        const y = new Date().getFullYear() - i;
                                        return <option key={y} value={y}>{y}</option>;
                                    })}
                                </select>
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold rounded-lg transition border border-gray-700/50 hover:border-gray-600 self-start md:self-center"
                    >
                        Close
                    </button>
                </div>

                {loading ? (
                    <div className="py-12 text-center space-y-4">
                        <div className="animate-spin w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto"></div>
                        <p className="text-indigo-300 font-medium">Analyzing data for {periodName}...</p>
                    </div>
                ) : (
                    <div className="space-y-6 text-gray-300 font-medium font-mono text-sm leading-7">
                        {advice?.raw_advice ? (
                            <div className="whitespace-pre-wrap">
                                {advice.raw_advice}
                            </div>
                        ) : (
                            <div className="text-center py-8 text-gray-500 bg-gray-800/50 rounded-2xl">
                                <p>No advice available.</p>
                            </div>
                        )}

                        {advice?.mock && (
                            <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-200 p-4 rounded-xl text-sm flex items-start gap-3 font-sans">
                                <AlertTriangle size={18} className="shrink-0 mt-0.5" />
                                <div>
                                    <span className="font-bold block mb-1">Using Mock Data</span>
                                    <span>Please configure Gemini API Key for real insights.</span>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div >
    );
}

function AddExpenseModal({ onClose, refresh, currencySymbol }) {
    const [formData, setFormData] = useState({ description: '', amount: '', category: '' });
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post('/expenses/', {
                description: formData.description,
                amount: parseFloat(formData.amount),
                category: formData.category || 'Uncategorized',
                date: new Date().toISOString()
            });
            refresh();
            onClose();
        } catch (e) { alert("Failed to add expense"); }
        finally { setLoading(false); }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-gray-900 w-full max-w-md rounded-3xl border border-gray-700 shadow-2xl p-8 scale-100 animate-in zoom-in-95 duration-200">
                <div className="flex justify-between items-center mb-8">
                    <h2 className="text-2xl font-bold text-white">Add Transaction</h2>
                    <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-full transition text-gray-400">✕</button>
                </div>
                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Description</label>
                        <input
                            type="text" required
                            className="w-full bg-gray-800/50 text-white rounded-xl p-4 border border-gray-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition font-medium"
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                            placeholder="e.g. Starbucks Chat"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Amount ({currencySymbol})</label>
                            <div className="relative">
                                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold">{currencySymbol}</span>
                                <input
                                    type="number" required step="0.01"
                                    className="w-full bg-gray-800/50 text-white rounded-xl p-4 pl-8 border border-gray-700 focus:border-indigo-500 outline-none transition font-bold"
                                    value={formData.amount}
                                    onChange={e => setFormData({ ...formData, amount: e.target.value })}
                                    placeholder="0.00"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Category</label>
                            <input
                                type="text"
                                className="w-full bg-gray-800/50 text-white rounded-xl p-4 border border-gray-700 focus:border-indigo-500 outline-none transition font-medium"
                                value={formData.category}
                                onChange={e => setFormData({ ...formData, category: e.target.value })}
                                placeholder="Food"
                            />
                        </div>
                    </div>

                    <button type="submit" disabled={loading} className="w-full py-4 rounded-xl bg-indigo-600 text-white font-bold text-lg hover:bg-indigo-500 transition shadow-lg shadow-indigo-500/20 mt-4">
                        {loading ? 'Adding...' : 'Save Transaction'}
                    </button>
                </form>
            </div>
        </div>
    );
}
