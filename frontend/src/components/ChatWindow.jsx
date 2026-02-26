import { useState, useEffect, useRef } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import { useAuth } from '../context/AuthContext';
import { Send, MessageSquare, X } from 'lucide-react';
import api from '../api/axios';

export default function ChatWindow() {
    const { activeWorkspace } = useWorkspace();
    const { user } = useAuth();

    const [messages, setMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const ws = useRef(null);
    const messagesEndRef = useRef(null);

    // Fetch history and connect WS when workspace changes
    useEffect(() => {
        if (!activeWorkspace) {
            setIsOpen(false);
            if (ws.current) {
                ws.current.close();
                ws.current = null;
            }
            return;
        }

        const fetchHistory = async () => {
            try {
                const res = await api.get(`/chat/history/${activeWorkspace._id}`);
                setMessages(res.data);
                scrollToBottom();
            } catch (error) {
                console.error("Error fetching chat history", error);
            }
        };

        const connectWebSocket = () => {
            const token = localStorage.getItem('token');
            if (!token) return;

            // Close existing connection if any
            if (ws.current) ws.current.close();

            const wsUrl = `ws://localhost:8000/api/chat/ws/${activeWorkspace._id}?token=${token}`;
            ws.current = new WebSocket(wsUrl);

            ws.current.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setMessages(prev => [...prev, data]);
            };

            ws.current.onerror = (error) => {
                console.error("WebSocket Error:", error);
            };
        };

        fetchHistory();
        connectWebSocket();

        return () => {
            if (ws.current) {
                ws.current.close();
                ws.current = null;
            }
        };
    }, [activeWorkspace]);

    useEffect(() => {
        scrollToBottom();
    }, [messages, isOpen]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const sendMessage = (e) => {
        e.preventDefault();
        if (!newMessage.trim() || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;

        ws.current.send(newMessage);
        setNewMessage('');
    };

    if (!activeWorkspace) return null;

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
            {/* Chat Toggle Button */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-full shadow-2xl transition flex items-center justify-center relative group"
                >
                    <MessageSquare size={24} />
                    {/* Optional: unread indicator here */}
                </button>
            )}

            {/* Chat Panel */}
            {isOpen && (
                <div className="w-80 md:w-96 h-[500px] bg-gray-800 border border-gray-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-5">
                    {/* Header */}
                    <div className="bg-gray-700 p-4 flex justify-between items-center border-b border-gray-600">
                        <div className="flex items-center gap-2">
                            <MessageSquare size={18} className="text-blue-400" />
                            <h3 className="font-semibold">{activeWorkspace.name} Chat</h3>
                        </div>
                        <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white transition">
                            <X size={20} />
                        </button>
                    </div>

                    {/* Messages Area */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {messages.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                                No messages yet. Start the conversation!
                            </div>
                        ) : (
                            messages.map((msg, index) => {
                                const isMe = msg.sender_id === user?.id || msg.sender_id === user?.user_id; // accommodate structural differences
                                return (
                                    <div key={index} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                                        <span className="text-xs text-gray-400 mb-1 ml-1 mr-1">
                                            {isMe ? 'You' : msg.sender_name}
                                        </span>
                                        <div
                                            className={`px-4 py-2 rounded-2xl max-w-[80%] break-words ${isMe
                                                    ? 'bg-blue-600 text-white rounded-br-sm'
                                                    : 'bg-gray-700 text-gray-100 rounded-bl-sm border border-gray-600'
                                                }`}
                                        >
                                            {msg.text}
                                        </div>
                                    </div>
                                );
                            })
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <form onSubmit={sendMessage} className="p-3 bg-gray-900 border-t border-gray-700 flex gap-2">
                        <input
                            type="text"
                            value={newMessage}
                            onChange={(e) => setNewMessage(e.target.value)}
                            placeholder="Type a message..."
                            className="flex-1 bg-gray-800 border border-gray-700 rounded-full px-4 text-sm text-white focus:outline-none focus:border-blue-500 transition"
                        />
                        <button
                            type="submit"
                            disabled={!newMessage.trim()}
                            className="bg-blue-600 disabled:bg-gray-700 hover:bg-blue-700 text-white p-2 rounded-full transition"
                        >
                            <Send size={18} className="ml-1" />
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
}
