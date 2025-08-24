import React, { createContext, useContext, useReducer, type ReactNode } from 'react';
import type { Message, ConversationInfo } from '../types/Message';

interface ChatState {
  messages: Message[];
  conversations: ConversationInfo[];
  currentConversationId: string | null;
  isLoadingHistory: boolean;
  showSidebar: boolean;
  inputValue: string;
}

type ChatAction =
  | { type: 'SET_MESSAGES'; payload: Message[] }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE'; payload: { id: string; updates: Partial<Message> } }
  | { type: 'SET_CONVERSATIONS'; payload: ConversationInfo[] }
  | { type: 'SET_CURRENT_CONVERSATION_ID'; payload: string | null }
  | { type: 'SET_LOADING_HISTORY'; payload: boolean }
  | { type: 'SET_SHOW_SIDEBAR'; payload: boolean }
  | { type: 'SET_INPUT_VALUE'; payload: string }
  | { type: 'RESET_MESSAGES' };

const initialState: ChatState = {
  messages: [],
  conversations: [],
  currentConversationId: null,
  isLoadingHistory: false,
  showSidebar: false,
  inputValue: '',
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'UPDATE_MESSAGE':
      return {
        ...state,
        messages: state.messages.map(msg =>
          msg.id === action.payload.id
            ? { ...msg, ...action.payload.updates }
            : msg
        ),
      };
    case 'SET_CONVERSATIONS':
      return { ...state, conversations: action.payload };
    case 'SET_CURRENT_CONVERSATION_ID':
      return { ...state, currentConversationId: action.payload };
    case 'SET_LOADING_HISTORY':
      return { ...state, isLoadingHistory: action.payload };
    case 'SET_SHOW_SIDEBAR':
      return { ...state, showSidebar: action.payload };
    case 'SET_INPUT_VALUE':
      return { ...state, inputValue: action.payload };
    case 'RESET_MESSAGES':
      return { ...state, messages: [] };
    default:
      return state;
  }
}

interface ChatContextType {
  state: ChatState;
  dispatch: React.Dispatch<ChatAction>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  return (
    <ChatContext.Provider value={{ state, dispatch }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}
