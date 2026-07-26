import { useState, useEffect, useMemo } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
    PieChart, Pie, Cell, Legend, LineChart, Line, AreaChart, Area, RadarChart,
    PolarGrid, PolarAngleAxis, Radar
} from 'recharts';
import {
    TrendingUp, TrendingDown, Activity, PieChart as PieChartIcon,
    ShoppingBag, Calendar, ArrowUpRight, ArrowDownRight, Zap,
    Target, Award, Clock, DollarSign, BarChart2, Layers, RefreshCw, Download
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getCategoryColor } from '../utils/categoryColors';

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const COLORS = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'];

const CustomTooltip = ({ active, payload, label, symbol }) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-3 shadow-2xl text-sm">
                <p className="text-gray-400 mb-1 font-medium">{label}</p>
                {payload.map((p, i) => (
                    <p key={i} style={{ color: p.color }} className="font-bold">
                        {p.name}: {symbol}{Number(p.value).toFixed(2)}
                    </p>
                ))}
            </div>
        );
    }
    return null;
};

const KPICard = ({ title, value, subtitle, icon: Icon, trend, trendLabel, color, symbol }) => {
    const isPositiveTrend = trend > 0;
    return (
        <div className={`relative bg-gray-900 rounded-2xl border border-gray-800 p-5 overflow-hidden group hover:border-${color}-500/50 transition-all duration-300`}>
            <div className={`absolute -top-4 -right-4 w-24 h-24 bg-${color}-500/10 rounded-full blur-2xl group-hover:bg-${color}-500/20 transition-all duration-500`} />
            <div className="flex items-start justify-between mb-4">
                <div className={`p-2.5 bg-${color}-500/10 rounded-xl border border-${color}-500/20`}>
                    <Icon size={20} className={`text-${color}-400`} />
                </div>
                {trend !== undefined && (
                    <div className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full ${isPositiveTrend ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'}`}>
                        {isPositiveTrend ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                        {Math.abs(trend).toFixed(1)}%
                    </div>
                )}
            </div>
            <p className="text-gray-500 text-xs font-bold uppercase tracking-wider mb-1">{title}</p>
            <p className="text-white text-2xl font-extrabold tracking-tight">{symbol}{value}</p>
            {subtitle && <p className="text-gray-500 text-xs mt-1">{subtitle}</p>}
            {trendLabel && <p className="text-gray-600 text-xs mt-1">{trendLabel}</p>}
        </div>
    );
};

export default function Analytics() {
    const { user } = useAuth();
    const [allExpenses, setAllExpenses] = useState([]);
    const [summary, setSummary] = useState([]);
    const [forecast, setForecast] = useState(null);
    const [forecastCategory, setForecastCategory] = useState('All');
    const [period, setPeriod] = useState('all');
    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');

    const sym = { 'USD': 'Rs.', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'NPR': 'Rs.' }[user?.currency || 'NPR'] || 'Rs.';

    useEffect(() => {
        fetchAll();
    }, [period, selectedYear]);

    useEffect(() => {
        fetchForecast();
    }, [forecastCategory]);

    const fetchForecast = async () => {
        try {
            const res = await api.get(`/expenses/forecast${forecastCategory !== 'All' ? `?category=${forecastCategory}` : ''}`);
            setForecast(res.data);
        } catch (e) {
            console.error(e);
        }
    };

    const fetchAll = async () => {
        setLoading(true);
        try {
            const expenseUrl = period === 'all'
                ? `/expenses/`
                : period === 'year'
                ? `/expenses/?year=${selectedYear}`
                : `/expenses/?year=${selectedYear}&month=${new Date().getMonth() + 1}`;

            const [summaryRes, expensesRes] = await Promise.all([
                api.get(`/expenses/summary?period=${period}`),
                api.get(expenseUrl)
            ]);
            setSummary(summaryRes.data);
            setAllExpenses(expensesRes.data);
            fetchForecast();
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    // ── Derived Data ──────────────────────────────────────────────────
    const stats = useMemo(() => {
        if (!allExpenses.length) return { total: 0, avg: 0, max: 0, count: 0, thisMonth: 0, lastMonth: 0 };
        const now = new Date();
        const total = allExpenses.reduce((s, e) => s + (e.amount || 0), 0);
        const thisMonth = allExpenses.filter(e => {
            const d = new Date(e.date);
            return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
        }).reduce((s, e) => s + (e.amount || 0), 0);
        const lastMonthDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const lastMonth = allExpenses.filter(e => {
            const d = new Date(e.date);
            return d.getMonth() === lastMonthDate.getMonth() && d.getFullYear() === lastMonthDate.getFullYear();
        }).reduce((s, e) => s + (e.amount || 0), 0);
        return {
            total,
            avg: total / allExpenses.length,
            max: Math.max(...allExpenses.map(e => e.amount || 0)),
            count: allExpenses.length,
            thisMonth,
            lastMonth,
            trend: lastMonth > 0 ? ((thisMonth - lastMonth) / lastMonth) * 100 : 0
        };
    }, [allExpenses]);

    const monthlyData = useMemo(() => {
        const map = {};
        allExpenses.forEach(e => {
            const d = new Date(e.date);
            if (!isNaN(d)) {
                const key = `${d.getFullYear()}-${d.getMonth()}`;
                if (!map[key]) map[key] = { month: MONTH_NAMES[d.getMonth()], amount: 0, count: 0, year: d.getFullYear() };
                map[key].amount += e.amount || 0;
                map[key].count += 1;
            }
        });
        return Object.values(map).sort((a, b) => {
            const ai = MONTH_NAMES.indexOf(a.month), bi = MONTH_NAMES.indexOf(b.month);
            return a.year !== b.year ? a.year - b.year : ai - bi;
        }).slice(-12);
    }, [allExpenses]);

    const dailyData = useMemo(() => {
        const map = {};
        allExpenses.forEach(e => {
            const d = new Date(e.date);
            if (!isNaN(d)) {
                const key = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                map[key] = (map[key] || 0) + (e.amount || 0);
            }
        });
        return Object.entries(map).map(([date, amount]) => ({ date, amount })).slice(-30);
    }, [allExpenses]);

    const topMerchants = useMemo(() => {
        const map = {};
        allExpenses.forEach(e => {
            const name = e.description || 'Unknown';
            if (!map[name]) map[name] = { name, total: 0, count: 0 };
            map[name].total += e.amount || 0;
            map[name].count += 1;
        });
        return Object.values(map).sort((a, b) => b.total - a.total).slice(0, 8);
    }, [allExpenses]);

    const categoryRadarData = useMemo(() => {
        return summary.map(s => ({ category: s._id, amount: s.total })).slice(0, 7);
    }, [summary]);

    const weekdayData = useMemo(() => {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const map = { Sun: 0, Mon: 0, Tue: 0, Wed: 0, Thu: 0, Fri: 0, Sat: 0 };
        allExpenses.forEach(e => {
            const d = new Date(e.date);
            if (!isNaN(d)) map[days[d.getDay()]] += e.amount || 0;
        });
        return days.map(d => ({ day: d, amount: map[d] }));
    }, [allExpenses]);

    const biggestCategory = summary.reduce((a, b) => a.total > b.total ? a : b, { _id: 'None', total: 0 });
    const totalSummary = summary.reduce((s, c) => s + c.total, 0);

    const tabs = [
        { id: 'overview', label: 'Overview', icon: BarChart2 },
        { id: 'trends', label: 'Trends', icon: TrendingUp },
        { id: 'categories', label: 'Categories', icon: PieChartIcon },
        { id: 'merchants', label: 'Merchants', icon: ShoppingBag },
    ];

    return (
        <Layout>
            <div className="space-y-8 animate-fade-in">
                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div>
                        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
                            Analytics
                        </h1>
                        <p className="text-gray-500 mt-1">Your complete financial intelligence dashboard</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex bg-gray-900 border border-gray-800 rounded-xl p-1 gap-1">
                            {['month', 'year', 'all'].map(p => (
                                <button key={p} onClick={() => setPeriod(p)}
                                    className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-200 ${period === p ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'text-gray-400 hover:text-white'}`}>
                                    {p.charAt(0).toUpperCase() + p.slice(1)}
                                </button>
                            ))}
                        </div>
                        <select value={selectedYear} onChange={e => setSelectedYear(+e.target.value)}
                            className="bg-gray-900 border border-gray-800 text-gray-300 text-sm rounded-xl px-3 py-2 outline-none">
                            {[2024, 2025, 2026, 2027].map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                        <button onClick={fetchAll} className="p-2 bg-gray-900 border border-gray-800 rounded-xl text-gray-400 hover:text-white transition">
                            <RefreshCw size={18} />
                        </button>
                    </div>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="flex flex-col items-center gap-4">
                            <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
                            <p className="text-gray-500 font-medium">Loading your analytics...</p>
                        </div>
                    </div>
                ) : (
                    <>
                        {/* KPI Cards */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <KPICard title="This Month" value={stats.thisMonth.toFixed(0)} symbol={sym}
                                icon={Calendar} color="indigo" trend={stats.trend}
                                trendLabel={`vs ${sym}${stats.lastMonth.toFixed(0)} last month`} />
                            <KPICard title="Total Spending" value={stats.total.toFixed(0)} symbol={sym}
                                icon={DollarSign} color="purple"
                                subtitle={`${stats.count} transactions`} />
                            <KPICard title="Avg Transaction" value={stats.avg.toFixed(0)} symbol={sym}
                                icon={Activity} color="blue"
                                subtitle="Per expense" />
                            <KPICard title="Largest Expense" value={stats.max.toFixed(0)} symbol={sym}
                                icon={Zap} color="amber"
                                subtitle="Single transaction" />
                        </div>

                        {/* AI Forecast + Biggest Category */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="md:col-span-2 bg-gradient-to-br from-indigo-900/60 via-purple-900/40 to-gray-900 rounded-2xl border border-indigo-500/20 p-6 relative overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/5 to-purple-600/5 pointer-events-none" />
                                <div className="absolute -top-8 -right-8 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl" />
                                <div className="relative">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2 text-indigo-300 font-bold text-xs uppercase tracking-widest">
                                            <Zap size={14} className="text-yellow-400" /> AI Forecast
                                        </div>
                                        <select 
                                            value={forecastCategory} 
                                            onChange={(e) => setForecastCategory(e.target.value)}
                                            className="bg-indigo-950/50 border border-indigo-500/30 text-indigo-200 text-xs rounded-lg px-2 py-1 outline-none font-medium cursor-pointer hover:bg-indigo-900/60 transition"
                                        >
                                            <option value="All">All Categories</option>
                                            {summary.map(s => <option key={s._id} value={s._id}>{s._id}</option>)}
                                        </select>
                                    </div>
                                    <div className="flex items-end gap-3 mb-3">
                                        <span className="text-5xl font-black text-white tracking-tight">
                                            {sym}{forecast?.predicted_amount?.toFixed(0) || '—'}
                                        </span>
                                        <span className="text-indigo-300 pb-1 text-sm">next month</span>
                                    </div>
                                    <div className="bg-black/30 border border-white/10 rounded-xl p-4 mt-4">
                                        <p className="text-xs text-gray-300 leading-relaxed italic">
                                            "{forecast?.advice || 'Keep tracking your expenses to receive smarter AI insights.'}"
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <div className="space-y-3">
                                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Award size={16} className="text-yellow-400" />
                                        <p className="text-gray-400 text-xs font-bold uppercase tracking-wider">Top Category</p>
                                    </div>
                                    <p className="text-white text-xl font-bold">{biggestCategory._id}</p>
                                    <p className="text-yellow-400 font-mono font-bold text-lg">{sym}{biggestCategory.total.toFixed(0)}</p>
                                    <p className="text-gray-600 text-xs mt-1">
                                        {totalSummary > 0 ? ((biggestCategory.total / totalSummary) * 100).toFixed(1) : 0}% of total
                                    </p>
                                </div>
                                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Target size={16} className="text-green-400" />
                                        <p className="text-gray-400 text-xs font-bold uppercase tracking-wider">Categories</p>
                                    </div>
                                    <p className="text-white text-xl font-bold">{summary.length}</p>
                                    <p className="text-gray-500 text-xs mt-1">Active spending areas</p>
                                </div>
                            </div>
                        </div>

                        {/* Tabs */}
                        <div className="flex gap-1 bg-gray-900/80 border border-gray-800 rounded-2xl p-1.5 w-fit">
                            {tabs.map(t => (
                                <button key={t.id} onClick={() => setActiveTab(t.id)}
                                    className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${activeTab === t.id ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}>
                                    <t.icon size={15} />
                                    {t.label}
                                </button>
                            ))}
                        </div>

                        {/* ── Overview Tab ── */}
                        {activeTab === 'overview' && (
                            <div className="space-y-6">
                                {/* Monthly Trend Line Chart */}
                                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                    <h3 className="text-white font-bold text-lg mb-6 flex items-center gap-2">
                                        <Activity size={20} className="text-indigo-400" /> Monthly Spending Trend
                                    </h3>
                                    <div className="h-72">
                                        {monthlyData.length > 0 ? (
                                            <ResponsiveContainer width="100%" height="100%">
                                                <AreaChart data={monthlyData}>
                                                    <defs>
                                                        <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                                                            <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                                                        </linearGradient>
                                                    </defs>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                                                    <XAxis dataKey="month" stroke="#4B5563" tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                                                    <YAxis stroke="#4B5563" tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                                                    <Tooltip content={<CustomTooltip symbol={sym} />} />
                                                    <Area type="monotone" dataKey="amount" name="Spending" stroke="#6366F1" strokeWidth={2.5} fill="url(#grad1)" dot={{ fill: '#6366F1', strokeWidth: 0, r: 4 }} activeDot={{ r: 6, fill: '#818CF8' }} />
                                                </AreaChart>
                                            </ResponsiveContainer>
                                        ) : <div className="flex items-center justify-center h-full text-gray-600">No data available</div>}
                                    </div>
                                </div>

                                {/* Daily Spending + Weekday Pattern */}
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                        <h3 className="text-white font-bold mb-6 flex items-center gap-2">
                                            <Clock size={18} className="text-blue-400" /> Daily Pattern (Last 30 Days)
                                        </h3>
                                        <div className="h-56">
                                            {dailyData.length > 0 ? (
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <BarChart data={dailyData} barSize={8}>
                                                        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                                                        <XAxis dataKey="date" stroke="#4B5563" tick={{ fontSize: 10, fill: '#6B7280' }} interval={4} />
                                                        <YAxis stroke="#4B5563" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                                        <Tooltip content={<CustomTooltip symbol={sym} />} />
                                                        <Bar dataKey="amount" name="Amount" radius={[3, 3, 0, 0]}>
                                                            {dailyData.map((_, i) => (
                                                                <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />
                                                            ))}
                                                        </Bar>
                                                    </BarChart>
                                                </ResponsiveContainer>
                                            ) : <div className="flex items-center justify-center h-full text-gray-600">No data</div>}
                                        </div>
                                    </div>
                                    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                        <h3 className="text-white font-bold mb-6 flex items-center gap-2">
                                            <Layers size={18} className="text-purple-400" /> Spending by Day of Week
                                        </h3>
                                        <div className="h-56">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart data={weekdayData} barSize={28}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                                                    <XAxis dataKey="day" stroke="#4B5563" tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                                                    <YAxis stroke="#4B5563" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                                    <Tooltip content={<CustomTooltip symbol={sym} />} />
                                                    <Bar dataKey="amount" name="Amount" radius={[5, 5, 0, 0]} fill="#8B5CF6" fillOpacity={0.85} />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* ── Trends Tab ── */}
                        {activeTab === 'trends' && (
                            <div className="space-y-6">
                                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                    <h3 className="text-white font-bold text-lg mb-6 flex items-center gap-2">
                                        <TrendingUp size={20} className="text-green-400" /> 12-Month Spending Overview
                                    </h3>
                                    <div className="h-80">
                                        {monthlyData.length > 0 ? (
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart data={monthlyData}>
                                                    <defs>
                                                        <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="0%" stopColor="#6366F1" />
                                                            <stop offset="100%" stopColor="#4F46E5" />
                                                        </linearGradient>
                                                    </defs>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                                                    <XAxis dataKey="month" stroke="#4B5563" tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                                                    <YAxis stroke="#4B5563" tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                                                    <Tooltip content={<CustomTooltip symbol={sym} />} />
                                                    <Bar dataKey="amount" name="Spending" fill="url(#barGrad)" radius={[6, 6, 0, 0]} />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        ) : <div className="flex items-center justify-center h-full text-gray-600">No trend data</div>}
                                    </div>
                                </div>
                                {/* Month comparison table */}
                                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                    <h3 className="text-white font-bold mb-5 flex items-center gap-2">
                                        <BarChart2 size={18} className="text-indigo-400" /> Month-by-Month Breakdown
                                    </h3>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="text-gray-500 uppercase text-xs tracking-wider border-b border-gray-800">
                                                    <th className="pb-3 text-left font-semibold">Month</th>
                                                    <th className="pb-3 text-right font-semibold">Total</th>
                                                    <th className="pb-3 text-right font-semibold">Transactions</th>
                                                    <th className="pb-3 text-right font-semibold">Avg/tx</th>
                                                    <th className="pb-3 text-left font-semibold pl-4">Share</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-800/50">
                                                {monthlyData.map((m, i) => {
                                                    const share = stats.total > 0 ? (m.amount / stats.total) * 100 : 0;
                                                    return (
                                                        <tr key={i} className="group hover:bg-gray-800/30 transition">
                                                            <td className="py-3 text-white font-semibold">{m.month} {m.year}</td>
                                                            <td className="py-3 text-right font-mono font-bold text-indigo-400">{sym}{m.amount.toFixed(0)}</td>
                                                            <td className="py-3 text-right text-gray-400">{m.count}</td>
                                                            <td className="py-3 text-right text-gray-400">{sym}{m.count > 0 ? (m.amount / m.count).toFixed(0) : '0'}</td>
                                                            <td className="py-3 pl-4">
                                                                <div className="flex items-center gap-2">
                                                                    <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden w-24">
                                                                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${share}%` }} />
                                                                    </div>
                                                                    <span className="text-gray-500 text-xs w-10">{share.toFixed(1)}%</span>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* ── Categories Tab ── */}
                        {activeTab === 'categories' && (
                            <div className="space-y-6">
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    {/* Donut Chart */}
                                    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                        <h3 className="text-white font-bold mb-4 flex items-center gap-2">
                                            <PieChartIcon size={18} className="text-purple-400" /> Spending Breakdown
                                        </h3>
                                        <div className="h-72">
                                            {summary.length > 0 ? (
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <PieChart>
                                                        <Pie data={summary} cx="50%" cy="50%" outerRadius={110} innerRadius={65}
                                                            paddingAngle={4} dataKey="total" nameKey="_id" stroke="none">
                                                            {summary.map((entry, i) => (
                                                                <Cell key={i} fill={getCategoryColor(entry._id).hex} />
                                                            ))}
                                                        </Pie>
                                                        <Tooltip formatter={v => `${sym}${v.toFixed(2)}`}
                                                            contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', color: '#F3F4F6', borderRadius: '0.75rem' }} />
                                                        <Legend iconType="circle" iconSize={10}
                                                            formatter={(val) => <span style={{ color: '#D1D5DB', fontSize: 12 }}>{val}</span>} />
                                                    </PieChart>
                                                </ResponsiveContainer>
                                            ) : <div className="flex items-center justify-center h-full text-gray-600">No category data</div>}
                                        </div>
                                    </div>
                                    {/* Radar Chart */}
                                    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                        <h3 className="text-white font-bold mb-4 flex items-center gap-2">
                                            <Target size={18} className="text-pink-400" /> Category Radar
                                        </h3>
                                        <div className="h-72">
                                            {categoryRadarData.length > 0 ? (
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <RadarChart data={categoryRadarData}>
                                                        <PolarGrid stroke="#1F2937" />
                                                        <PolarAngleAxis dataKey="category" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                                                        <Radar name="Spending" dataKey="amount" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.25} strokeWidth={2} />
                                                        <Tooltip formatter={v => `${sym}${v.toFixed(0)}`}
                                                            contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.75rem' }} />
                                                    </RadarChart>
                                                </ResponsiveContainer>
                                            ) : <div className="flex items-center justify-center h-full text-gray-600">No data</div>}
                                        </div>
                                    </div>
                                </div>
                                {/* Category list */}
                                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                    <h3 className="text-white font-bold mb-5">All Categories</h3>
                                    <div className="space-y-3">
                                        {summary.sort((a, b) => b.total - a.total).map((cat, i) => {
                                            const pct = totalSummary > 0 ? (cat.total / totalSummary) * 100 : 0;
                                            const color = getCategoryColor(cat._id);
                                            return (
                                                <div key={i} className="flex items-center gap-4 group">
                                                    <span className={`text-xs font-bold px-2.5 py-1 rounded-full border w-28 text-center ${color.badgeClasses}`}>
                                                        {cat._id}
                                                    </span>
                                                    <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                                                        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: color.hex }} />
                                                    </div>
                                                    <span className="text-gray-300 font-mono text-sm w-20 text-right">{sym}{cat.total.toFixed(0)}</span>
                                                    <span className="text-gray-600 text-xs w-12 text-right">{pct.toFixed(1)}%</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* ── Merchants Tab ── */}
                        {activeTab === 'merchants' && (
                            <div className="space-y-6">
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                        <h3 className="text-white font-bold mb-6 flex items-center gap-2">
                                            <ShoppingBag size={18} className="text-orange-400" /> Top Merchants by Spend
                                        </h3>
                                        <div className="h-72">
                                            {topMerchants.length > 0 ? (
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <BarChart data={topMerchants} layout="vertical" barSize={14}>
                                                        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" horizontal={false} />
                                                        <XAxis type="number" stroke="#4B5563" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                                                        <YAxis type="category" dataKey="name" stroke="#4B5563" tick={{ fontSize: 11, fill: '#9CA3AF' }} width={90} />
                                                        <Tooltip content={<CustomTooltip symbol={sym} />} />
                                                        <Bar dataKey="total" name="Total Spent" radius={[0, 4, 4, 0]}>
                                                            {topMerchants.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                                                        </Bar>
                                                    </BarChart>
                                                </ResponsiveContainer>
                                            ) : <div className="flex items-center justify-center h-full text-gray-600">No merchant data</div>}
                                        </div>
                                    </div>
                                    {/* Merchant Table */}
                                    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                        <h3 className="text-white font-bold mb-5">Merchant Leaderboard</h3>
                                        <div className="space-y-2">
                                            {topMerchants.map((m, i) => (
                                                <div key={i} className="flex items-center gap-3 p-3 bg-gray-800/40 hover:bg-gray-800 rounded-xl transition group">
                                                    <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-black"
                                                        style={{ backgroundColor: COLORS[i % COLORS.length] + '22', color: COLORS[i % COLORS.length] }}>
                                                        {i + 1}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-white font-semibold text-sm truncate">{m.name}</p>
                                                        <p className="text-gray-500 text-xs">{m.count} visits</p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="font-mono font-bold text-sm" style={{ color: COLORS[i % COLORS.length] }}>
                                                            {sym}{m.total.toFixed(0)}
                                                        </p>
                                                        <p className="text-gray-600 text-xs">{sym}{m.count > 0 ? (m.total / m.count).toFixed(0) : 0}/visit</p>
                                                    </div>
                                                </div>
                                            ))}
                                            {topMerchants.length === 0 && (
                                                <div className="text-center py-8 text-gray-600">No merchant data available</div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                {/* All transactions summary */}
                                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                                    <h3 className="text-white font-bold mb-5">Recent Transactions ({allExpenses.length} total)</h3>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="text-gray-500 uppercase text-xs tracking-wider border-b border-gray-800">
                                                    <th className="pb-3 text-left">Date</th>
                                                    <th className="pb-3 text-left">Description</th>
                                                    <th className="pb-3 text-left">Category</th>
                                                    <th className="pb-3 text-right">Amount</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-800/40">
                                                {allExpenses.slice(0, 20).map((e, i) => {
                                                    const color = getCategoryColor(e.category);
                                                    return (
                                                        <tr key={i} className="hover:bg-gray-800/30 transition">
                                                            <td className="py-2.5 text-gray-500 text-xs whitespace-nowrap">
                                                                {e.date ? new Date(e.date).toLocaleDateString() : '—'}
                                                            </td>
                                                            <td className="py-2.5 text-gray-200 font-medium max-w-[180px] truncate pr-3">{e.description}</td>
                                                            <td className="py-2.5">
                                                                <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${color.badgeClasses}`}>
                                                                    {e.category}
                                                                </span>
                                                            </td>
                                                            <td className="py-2.5 text-right font-mono font-bold text-white">{sym}{(e.amount || 0).toFixed(2)}</td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </Layout>
    );
}
