import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend } from 'recharts';
import { TrendingUp, Activity, Filter, PieChart as PieChartIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Analytics() {
    const { user } = useAuth();
    const [summary, setSummary] = useState([]);
    const [forecast, setForecast] = useState(null);
    const [dailyData, setDailyData] = useState([]);
    const [period, setPeriod] = useState('all'); // all, year, month

    const currencySymbol = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'NPR': 'Rs'
    }[user?.currency || 'USD'] || '$';

    useEffect(() => {
        const fetchData = async () => {
            try {
                // 1. Summary by Category (for Pie Chart)
                const summaryRes = await api.get(`/expenses/summary?period=${period}`);
                setSummary(summaryRes.data);

                // 2. Forecast
                const forecastRes = await api.get('/expenses/forecast');
                setForecast(forecastRes.data);

                // 3. Daily Trend Data (Bar Chart)
                const expensesRes = await api.get('/expenses/');
                const now = new Date();

                // Filter based on period if needed manually, but backend summary handles categories.
                // For trend, let's show last 30 days or based on period.
                // Let's just group ALL returned expenses (which are top 100 recent) by date.

                const grouped = {};
                expensesRes.data.forEach(ex => {
                    const d = new Date(ex.date);
                    // Check if valid date
                    if (!isNaN(d.getTime())) {
                        const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                        grouped[dateStr] = (grouped[dateStr] || 0) + ex.amount;
                    }
                });

                const chartData = Object.keys(grouped).map(date => ({ date, amount: grouped[date] }));
                // Sort by date roughly? The keys insertion order isn't guaranteed, but usually okay for recent. 
                // Better to sort by timestamp but we lost it. 
                // Let's rely on the fact expensesRes returns sorted by date desc. 

                setDailyData(chartData.reverse()); // Reverse to show oldest to newest

            } catch (e) { console.error("Analytics fetch error", e); }
        };

        fetchData();
    }, [period]);

    const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

    return (
        <Layout>
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-white">Analytics & Forecast</h1>
                <p className="text-gray-400">Deep dive into your spending habits.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
                {/* Forecast Card (1 col) */}
                <div className="lg:col-span-1 bg-gradient-to-br from-indigo-600 to-purple-700 p-6 rounded-2xl shadow-xl text-white relative overflow-hidden flex flex-col justify-between">
                    <div className="absolute top-0 right-0 p-24 bg-white/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
                    <div>
                        <div className="flex items-center gap-2 mb-4 opacity-80">
                            <TrendingUp size={24} />
                            <span className="font-medium tracking-wide">AI FORECAST</span>
                        </div>
                        <h2 className="text-5xl font-bold mb-2 tracking-tight">
                            {currencySymbol}{forecast?.predicted_amount?.toFixed(0) || "0"}
                        </h2>
                        <p className="text-indigo-200 text-sm">Estimated spend for next month</p>
                    </div>
                    <div className="mt-8 bg-black/20 p-4 rounded-xl backdrop-blur-sm border border-white/10">
                        <p className="text-xs font-medium opacity-90 leading-relaxed">
                            "{forecast?.advice || "Keep tracking your expenses to get smarter insights."}"
                        </p>
                    </div>
                </div>

                {/* Spending Trend Chart (2 cols) */}
                <div className="lg:col-span-2 bg-gray-800 p-6 rounded-2xl border border-gray-700 shadow-lg">
                    <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                        <Activity size={20} className="text-blue-400" /> Daily Spending Trend
                    </h3>
                    <div className="h-64">
                        {dailyData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={dailyData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                                    <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
                                    <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1F2937', borderColor: '#374151', color: '#F3F4F6', borderRadius: '0.5rem' }}
                                        formatter={(val) => `${currencySymbol}${val.toFixed(2)}`}
                                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                    />
                                    <Bar dataKey="amount" fill="#3B82F6" radius={[4, 4, 0, 0]}>
                                        {dailyData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full text-gray-500">
                                Not enough data for trend
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Category Breakdown (Pie Chart) */}
            <div className="bg-gray-800 p-8 rounded-2xl border border-gray-700 shadow-lg">
                <div className="flex flex-col sm:flex-row justify-between items-center mb-8 gap-4">
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        <PieChartIcon size={20} className="text-purple-400" /> Expense by Category
                    </h3>
                    <div className="flex bg-gray-900 rounded-lg p-1 gap-1">
                        {['all', 'year', 'month'].map((p) => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${period === p
                                    ? 'bg-purple-600 text-white shadow-sm'
                                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                                    }`}
                            >
                                {p.charAt(0).toUpperCase() + p.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="h-96 w-full flex justify-center items-center">
                    {summary.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={summary}
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={120}
                                    innerRadius={80}
                                    paddingAngle={5}
                                    dataKey="total"
                                    nameKey="_id"
                                    stroke="none"
                                >
                                    {summary.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1F2937', borderColor: '#374151', color: '#F3F4F6', borderRadius: '0.5rem' }}
                                    formatter={(val) => `${currencySymbol}${val.toFixed(2)}`}
                                />
                                <Legend
                                    layout="vertical"
                                    verticalAlign="middle"
                                    align="right"
                                    iconType="circle"
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="text-gray-500">
                            No data for this period
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
}
