export interface Message {
    id: string;
    content: string;
    sender: 'user' | 'assistant';
    timestamp: Date;
    agent?: string;
    metadata?: any;
    isLoading?: boolean;
}

export interface ConversationInfo {
    conversation_id: string;
    title: string;
    updated_at: string;
    message_count: number;
    last_message?: string;
}