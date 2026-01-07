import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { Trophy, Flame, Star, Target, Gift } from 'lucide-react';
import clsx from 'clsx';

export default function Game() {
    const [progress, setProgress] = useState(null);
    const [loading, setLoading] = useState(true);

    const { logout } = useAuth();

    useEffect(() => {
        async function fetchProgress() {
            try {
                const res = await api.get('/game/progress');
                setProgress(res.data);
            } catch (e) {
                console.error(e);
                if (e.response?.status === 401) {
                    logout();
                }
            } finally {
                setLoading(false);
            }
        }
        fetchProgress();
    }, [logout]);

    return (
        <Layout>
            <header className="mb-8 text-center">
                <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-500 mb-2">
                    Financial Quest
                </h1>
                <p className="text-gray-400">Level up your financial habits!</p>
            </header>

            {loading || !progress ? (
                <div className="text-white text-center">Loading Quest...</div>
            ) : (
                <div className="max-w-4xl mx-auto space-y-8">
                    {/* Main Level Card */}
                    <div className="bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 p-8 rounded-3xl shadow-2xl text-center relative overflow-hidden">
                        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>

                        <div className="relative z-10">
                            <div className="w-24 h-24 mx-auto bg-yellow-500/20 rounded-full flex items-center justify-center mb-4 border-4 border-yellow-500/50">
                                <Trophy size={48} className="text-yellow-400" />
                            </div>
                            <h2 className="text-3xl font-bold text-white mb-1">Level {progress.level}</h2>
                            <p className="text-purple-200 mb-6">Novice Saver</p>

                            <div className="w-full max-w-md mx-auto bg-gray-900/50 rounded-full h-4 relative overflow-hidden">
                                <div
                                    className="absolute left-0 top-0 h-full bg-gradient-to-r from-blue-400 to-purple-500 transition-all duration-1000"
                                    style={{ width: `${(progress.points % 100)}%` }}
                                ></div>
                            </div>
                            <p className="text-sm text-gray-400 mt-2">{progress.points % 100} / 100 XP to next level</p>
                        </div>
                    </div>

                    {/* Stats Row */}
                    <div className="grid grid-cols-2 gap-6">
                        <div className="bg-gray-800 p-6 rounded-2xl border border-gray-700 flex items-center gap-4">
                            <div className="p-4 bg-orange-500/20 rounded-xl text-orange-500">
                                <Flame size={32} />
                            </div>
                            <div>
                                <p className="text-gray-400 text-sm">Daily Streak</p>
                                <h3 className="text-2xl font-bold text-white">{progress.streak_count} Days</h3>
                            </div>
                        </div>
                        <div className="bg-gray-800 p-6 rounded-2xl border border-gray-700 flex items-center gap-4">
                            <div className="p-4 bg-yellow-500/20 rounded-xl text-yellow-500">
                                <Star size={32} />
                            </div>
                            <div>
                                <p className="text-gray-400 text-sm">Total Points</p>
                                <h3 className="text-2xl font-bold text-white">{progress.points}</h3>
                            </div>
                        </div>
                    </div>

                    {/* Quests */}
                    <div className="bg-gray-800 p-6 rounded-2xl border border-gray-700">
                        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                            <Target className="text-red-400" /> Active Quests
                        </h3>

                        <div className="space-y-4">
                            <QuestItem
                                title="Upload First Receipt"
                                xp={50}
                                completed={progress.points >= 50}
                            />
                            <QuestItem
                                title="7 Day Streak"
                                xp={200}
                                completed={progress.streak_count >= 7}
                            />
                            <QuestItem
                                title="Stay Under Budget"
                                xp={100}
                                completed={false} // Placeholder logic
                            />
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

function QuestItem({ title, xp, completed }) {
    return (
        <div className={clsx("p-4 rounded-xl border flex justify-between items-center transition",
            completed ? "bg-green-500/10 border-green-500/30" : "bg-gray-700/30 border-gray-600"
        )}>
            <div className="flex items-center gap-4">
                <div className={clsx("w-6 h-6 rounded-full flex items-center justify-center border-2",
                    completed ? "bg-green-500 border-green-500" : "border-gray-500"
                )}>
                    {completed && <CheckIcon />}
                </div>
                <span className={clsx("font-medium", completed ? "text-gray-300 line-through" : "text-white")}>
                    {title}
                </span>
            </div>
            <div className="flex items-center gap-1 text-yellow-400 font-bold text-sm">
                +{xp} XP
            </div>
        </div>
    )
}

function CheckIcon() {
    return <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
}
