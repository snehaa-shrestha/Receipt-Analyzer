import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/axios';
import { Users, Plus, Trash2, ArrowLeft, Receipt as ReceiptIcon, Calculator } from 'lucide-react';

export default function BillSplitter() {
    const { receipt_id } = useParams();
    const navigate = useNavigate();
    const [receipt, setReceipt] = useState(null);
    const [loading, setLoading] = useState(true);
    
    const [people, setPeople] = useState([{ id: '0', name: 'Me' }]);
    const [assignments, setAssignments] = useState({}); // itemId (index) -> array of person ids
    const [saving, setSaving] = useState(false);
    
    useEffect(() => {
        const fetchReceipt = async () => {
            try {
                const res = await api.get(`/receipts/${receipt_id}`);
                setReceipt(res.data);
                
                if (res.data.split_people && res.data.split_assignments) {
                    setPeople(res.data.split_people);
                    setAssignments(res.data.split_assignments);
                } else if (res.data && res.data.items) {
                    const initAssign = {};
                    res.data.items.forEach((_, idx) => {
                        initAssign[idx] = ['0'];
                    });
                    setAssignments(initAssign);
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };
        fetchReceipt();
    }, [receipt_id]);

    const addPerson = () => {
        const id = Date.now().toString();
        setPeople([...people, { id, name: `Person ${people.length + 1}` }]);
    };
    
    const removePerson = (id) => {
        if (id === '0') return; // Cannot remove 'Me'
        setPeople(people.filter(p => p.id !== id));
        
        // Remove this person from assignments
        const newAssign = { ...assignments };
        Object.keys(newAssign).forEach(itemId => {
            newAssign[itemId] = newAssign[itemId].filter(pid => pid !== id);
            if (newAssign[itemId].length === 0) {
                newAssign[itemId] = ['0']; // Re-assign to Me if empty
            }
        });
        setAssignments(newAssign);
    };

    const updatePersonName = (id, newName) => {
        setPeople(people.map(p => p.id === id ? { ...p, name: newName } : p));
    };

    const toggleAssignment = (itemId, personId) => {
        const currentAssigns = assignments[itemId] || [];
        let newAssigns;
        if (currentAssigns.includes(personId)) {
            newAssigns = currentAssigns.filter(id => id !== personId);
            if (newAssigns.length === 0) return; // Prevent empty assignment
        } else {
            newAssigns = [...currentAssigns, personId];
        }
        setAssignments({ ...assignments, [itemId]: newAssigns });
    };

    const saveSplits = async () => {
        setSaving(true);
        try {
            await api.put(`/receipts/${receipt_id}/split`, {
                people: people,
                assignments: assignments
            });
            // brief visual feedback could be added here
        } catch (e) {
            console.error("Failed to save splits", e);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex justify-center items-center min-h-[50vh]">
                    <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full"></div>
                </div>
            </Layout>
        );
    }

    if (!receipt) {
        return (
            <Layout>
                <div className="text-center text-gray-500 py-20">Receipt not found.</div>
            </Layout>
        );
    }

    // Calculations
    const items = receipt.items || [];
    const itemSubtotal = items.reduce((sum, item) => sum + (item.amount || item.price || 0), 0);
    const receiptTotal = receipt.total_amount || itemSubtotal;
    const taxAndTip = Math.max(0, receiptTotal - itemSubtotal);

    const personTotals = people.map(p => {
        let assignedSubtotal = 0;
        items.forEach((item, idx) => {
            const assignees = assignments[idx] || [];
            if (assignees.includes(p.id)) {
                assignedSubtotal += (item.amount || item.price || 0) / assignees.length;
            }
        });
        
        const proportion = itemSubtotal > 0 ? (assignedSubtotal / itemSubtotal) : 0;
        const assignedTaxTip = taxAndTip * proportion;
        const totalOwed = assignedSubtotal + assignedTaxTip;
        
        return {
            ...p,
            subtotal: assignedSubtotal,
            taxTip: assignedTaxTip,
            total: totalOwed
        };
    });

    const currencySymbol = 'Rs.'; // could read from user context

    return (
        <Layout>
            <div className="max-w-6xl mx-auto animate-fade-in">
                <button 
                    onClick={() => navigate('/gallery')}
                    className="text-gray-400 hover:text-white flex items-center gap-2 mb-6 transition"
                >
                    <ArrowLeft size={16} /> Back to Gallery
                </button>

                <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 mb-8">
                    <div>
                        <div className="flex items-center gap-2 text-indigo-400 text-sm mb-1 font-bold tracking-wide uppercase">
                            <Calculator size={16} /> Bill Splitter
                        </div>
                        <h1 className="text-3xl font-extrabold text-white">
                            {receipt.merchant_name}
                        </h1>
                        <p className="text-gray-400 mt-1">
                            {new Date(receipt.date_extracted).toLocaleDateString()} • Total: {currencySymbol}{receiptTotal.toFixed(2)}
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <button 
                            onClick={saveSplits}
                            disabled={saving}
                            className="bg-gray-800 hover:bg-gray-700 text-white px-5 py-2.5 rounded-xl font-bold transition flex items-center gap-2 border border-gray-700 disabled:opacity-50"
                        >
                            {saving ? <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div> : <Calculator size={18} />}
                            {saving ? 'Saving...' : 'Save Split'}
                        </button>
                        <button 
                            onClick={addPerson}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-bold transition flex items-center gap-2 shadow-lg"
                        >
                            <Plus size={18} /> Add Person
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left side: Items */}
                    <div className="lg:col-span-2 space-y-4">
                        <h2 className="text-xl font-bold text-white mb-4">Assign Items</h2>
                        {items.length === 0 ? (
                            <div className="text-gray-500 bg-gray-900/50 p-6 rounded-2xl border border-gray-700/50 text-center">
                                No items found on this receipt.
                            </div>
                        ) : (
                            items.map((item, idx) => {
                                const amount = item.amount || item.price || 0;
                                const assignees = assignments[idx] || [];
                                
                                return (
                                    <div key={idx} className="bg-gray-800/40 border border-gray-700/50 rounded-2xl p-4 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                                        <div className="flex-1">
                                            <h3 className="text-gray-200 font-bold">{item.description || item.item_name}</h3>
                                            <p className="text-gray-400 text-sm">{currencySymbol}{amount.toFixed(2)}</p>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {people.map(p => {
                                                const isAssigned = assignees.includes(p.id);
                                                return (
                                                    <button
                                                        key={p.id}
                                                        onClick={() => toggleAssignment(idx, p.id)}
                                                        className={`px-3 py-1.5 rounded-lg text-sm font-bold transition ${
                                                            isAssigned 
                                                            ? 'bg-indigo-500 text-white shadow-[0_0_10px_rgba(99,102,241,0.3)]' 
                                                            : 'bg-gray-900 text-gray-500 border border-gray-700 hover:border-gray-500'
                                                        }`}
                                                    >
                                                        {p.name}
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    </div>
                                )
                            })
                        )}
                        
                        {taxAndTip > 0 && (
                            <div className="bg-gray-800/20 border border-gray-700/30 rounded-2xl p-4 flex justify-between items-center mt-4">
                                <div>
                                    <h3 className="text-gray-400 font-bold">Tax, Tip & Fees</h3>
                                    <p className="text-gray-500 text-xs">Automatically split proportionally</p>
                                </div>
                                <p className="text-gray-400 font-bold">{currencySymbol}{taxAndTip.toFixed(2)}</p>
                            </div>
                        )}
                    </div>

                    {/* Right side: People & Summary */}
                    <div className="space-y-6">
                        <div className="bg-gradient-to-b from-gray-800 to-gray-900 rounded-3xl p-6 border border-gray-700 shadow-xl sticky top-6">
                            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                                <Users size={20} className="text-indigo-400"/> Split Breakdown
                            </h2>
                            
                            <div className="space-y-4">
                                {personTotals.map(p => (
                                    <div key={p.id} className="bg-gray-900/80 rounded-2xl p-4 border border-gray-800 relative group">
                                        <div className="flex justify-between items-center mb-3">
                                            <input 
                                                type="text" 
                                                value={p.name}
                                                onChange={(e) => updatePersonName(p.id, e.target.value)}
                                                className="bg-transparent text-white font-bold outline-none border-b border-transparent focus:border-indigo-500 w-32 transition"
                                            />
                                            {p.id !== '0' && (
                                                <button 
                                                    onClick={() => removePerson(p.id)}
                                                    className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition"
                                                    title="Remove person"
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            )}
                                        </div>
                                        
                                        <div className="space-y-1 text-sm">
                                            <div className="flex justify-between text-gray-400">
                                                <span>Subtotal</span>
                                                <span>{currencySymbol}{p.subtotal.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between text-gray-400 pb-2 border-b border-gray-800">
                                                <span>Tax/Tip</span>
                                                <span>{currencySymbol}{p.taxTip.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between text-indigo-300 font-bold pt-1 text-lg">
                                                <span>Owes</span>
                                                <span>{currencySymbol}{p.total.toFixed(2)}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            
                            <div className="mt-6 pt-4 border-t border-gray-800">
                                <div className="flex justify-between text-gray-400 text-sm mb-1">
                                    <span>Calculated Total</span>
                                    <span>{currencySymbol}{(itemSubtotal + taxAndTip).toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-gray-400 text-sm">
                                    <span>Receipt Total</span>
                                    <span>{currencySymbol}{receiptTotal.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
}
