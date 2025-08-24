import { useState } from "react";

export interface ConversationInfo {
  conversation_id: string;
  title: string;
  updated_at: string;
  message_count: number;
  last_message?: string;
}


interface ConversationListProps {
  conversations: ConversationInfo[];
  currentConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (conversationId: string) => void;
  onRefreshConversations?: () => void;
  show: boolean;
}

export default function ConversationList({ conversations, currentConversationId, onSelectConversation, onNewConversation, onDeleteConversation, onRefreshConversations, show }: ConversationListProps) {
  const [editingTitle, setEditingTitle] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState('');

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    
    if (isNaN(date.getTime())) {
      return 'Data inválida';
    }
    
    const diffTime = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffTime / (1000 * 60));
    const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    const diffWeeks = Math.floor(diffDays / 7);
    const diffYears = Math.floor(diffDays / 365);

    if (diffMinutes < 1) return 'Agora mesmo';
    if (diffMinutes < 60) return `${diffMinutes} min atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    
    const today = new Date();
    const isToday = date.toDateString() === today.toDateString();
    if (isToday) {
      return date.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit'
      });
    }
    
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = date.toDateString() === yesterday.toDateString();
    if (isYesterday) {
      return `Ontem às ${date.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit'
      })}`;
    }
    
    if (diffDays < 7) {
      const dayName = date.toLocaleDateString('pt-BR', { weekday: 'long' });
      return `${dayName.charAt(0).toUpperCase() + dayName.slice(1)} às ${date.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit'
      })}`;
    }
    
    if (diffWeeks < 4) {
      return `${diffWeeks} semana${diffWeeks > 1 ? 's' : ''} atrás`;
    }
    
    
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: diffYears > 0 ? 'numeric' : undefined
    });
  };

  const handleTitleEdit = async (conversationId: string, title: string) => {
    try {
      const response = await fetch(`http://localhost:8000/conversations/${conversationId}/title`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ title })
      });

      if (response.ok) {
        setEditingTitle(null);
        setNewTitle('');
        // Refresh conversations to show updated title
        if (onRefreshConversations) {
          onRefreshConversations();
        }
      }
    } catch (error) {
      console.error('Error updating title:', error);
    }
  };
  const startEditTitle = (conversationId: string, currentTitle: string) => {
    setEditingTitle(conversationId);
    setNewTitle(currentTitle);
  };

  const cancelEdit = () => {
    setEditingTitle(null);
    setNewTitle('');
  };

  const handleKeyPress = (e: React.KeyboardEvent, conversationId: string) => {
    if (e.key === 'Enter') {
      handleTitleEdit(conversationId, newTitle);
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };


  return (
    <div className={`h-full overflow-y-auto overflow-x-hidden custom-scrollbar smooth-scroll transition-all duration-300 ease-in-out ${
      show ? 'opacity-100' : 'opacity-0 pointer-events-none'
    }`}>
    {conversations.length === 0 ? (
      <div className={`p-4 text-center text-gray-400 transition-all duration-300 ease-in-out delay-150 ${
        show ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}>
        <p>Nenhuma conversa ainda</p>
        <button
          onClick={onNewConversation}
          className="mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm transition-all duration-200"
        >
          Iniciar primeira conversa
        </button>
      </div>
    ) : (
      <div className="p-2 space-y-2">
        {conversations.map((conversation, index) => (
          <div
            key={conversation.conversation_id}
            className={`group relative p-3 rounded-lg cursor-pointer transition-all duration-300 ease-in-out overflow-hidden ${
              conversation.conversation_id === currentConversationId
                ? 'bg-blue-600/20 border border-blue-500/30'
                : 'hover:bg-gray-800'
            } ${
              show 
                ? 'opacity-100 translate-x-0' 
                : 'opacity-0 -translate-x-4'
            }`}
            style={{
              transitionDelay: show ? `${150 + index * 50}ms` : '0ms'
            }}
            onClick={() => onSelectConversation(conversation.conversation_id)}
          >
            {/* Title */}
            <div className="flex items-center justify-between mb-1">
              {editingTitle === conversation.conversation_id ? (
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  onKeyPress={(e) => handleKeyPress(e, conversation.conversation_id)}
                  onBlur={() => handleTitleEdit(conversation.conversation_id, newTitle)}
                  className="bg-gray-800 text-white text-sm px-2 py-1 rounded flex-1 mr-2"
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <h3
                  className="text-white text-sm font-medium truncate pr-2 flex-1 overflow-hidden text-ellipsis whitespace-nowrap"
                  title={conversation.title}
                >
                  {conversation.title}
                </h3>
              )}

              {/* Action buttons */}
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-all duration-200 ease-in-out">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    startEditTitle(conversation.conversation_id, conversation.title);
                  }}
                  className="p-1 hover:bg-gray-600 rounded text-gray-400 hover:text-white transition-all duration-200 hover:scale-110"
                  title="Editar título"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Tem certeza que deseja excluir esta conversa?')) {
                      onDeleteConversation(conversation.conversation_id);
                    }
                  }}
                  className="p-1 hover:bg-red-600 rounded text-gray-400 hover:text-white transition-all duration-200 hover:scale-110"
                  title="Excluir conversa"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Metadata */}
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>{conversation.message_count} mensagens</span>
              <span>{formatDate(conversation.updated_at)}</span>
            </div>

            {/* Last message preview */}
            {conversation.last_message && (
              <p className="text-xs text-gray-500 mt-1 truncate overflow-hidden text-ellipsis whitespace-nowrap">
                {conversation.last_message}
              </p>
            )}

            {/* Current conversation indicator */}
            {conversation.conversation_id === currentConversationId && (
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-r"></div>
            )}
          </div>
        ))}
      </div>
    )}
  </div>
  )
}