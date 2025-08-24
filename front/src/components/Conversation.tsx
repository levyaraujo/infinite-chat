import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import type { Message } from '../types/Message';

interface ConversationProps {
    messages: Message[];
}

export default function Conversation({ messages }: ConversationProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    return (
        <div className="p-4 rounded-t-2xl">
            {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
        </div>
    );
}