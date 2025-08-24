import { useCallback } from 'react';
import { useChatContext } from '../contexts/ChatContext';
import { useConversations } from './useConversations';
import type { Message } from '../types/Message';
import { getCookie } from '../utils/cookies';
import { API_URL } from '../utils/urls';

export function useChat() {
  const { state, dispatch } = useChatContext();
  const { loadUserConversations } = useConversations();

  const sendMessage = useCallback(async (messageContent: string) => {
    if (!messageContent.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: messageContent,
      sender: 'user',
      timestamp: new Date()
    };

    dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
    dispatch({ type: 'SET_INPUT_VALUE', payload: '' });

    const loadingMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: '',
      sender: 'assistant',
      timestamp: new Date(),
      isLoading: true
    };
    dispatch({ type: 'ADD_MESSAGE', payload: loadingMessage });

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          message: messageContent,
          user_id: getCookie('user_id'),
          conversation_id: getCookie('conversation_id')
        })
      });

      if (!response.ok) {
        let errorMessage = 'Erro de conexão. Verifique sua conexão com a internet.';
        if (response.status === 404) {
          errorMessage = 'Serviço não encontrado. Verifique se o servidor está rodando.';
        } else if (response.status === 500) {
          errorMessage = 'Erro interno do servidor. Tente novamente mais tarde.';
        } else if (response.status >= 400 && response.status < 500) {
          errorMessage = 'Erro na solicitação. Verifique os dados enviados.';
        }
        throw new Error(errorMessage);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

      let accumulatedContent = '';

      dispatch({
        type: 'UPDATE_MESSAGE',
        payload: {
          id: loadingMessage.id,
          updates: { isLoading: false, content: '' }
        }
      });

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonData = line.slice(6);

              if (jsonData === '[DONE]') {
                continue;
              }

              const data = JSON.parse(jsonData);

              if (data.type === 'agent_selection') {
                if (data.data.conversation_id) {
                  dispatch({
                    type: 'SET_CURRENT_CONVERSATION_ID',
                    payload: data.data.conversation_id
                  });
                }
                if (data.data.agent) {
                  dispatch({
                    type: 'UPDATE_MESSAGE',
                    payload: {
                      id: loadingMessage.id,
                      updates: {
                        agent: data.data.agent
                      }
                    }
                  });
                }
              } else if (data.type === 'chunk') {
                const newContent = data.data?.content || '';
                if (newContent) {
                  accumulatedContent += newContent;

                  dispatch({
                    type: 'UPDATE_MESSAGE',
                    payload: {
                      id: loadingMessage.id,
                      updates: {
                        content: accumulatedContent,
                        agent: data.data?.agent
                      }
                    }
                  });
                }
              } else if (data.type === 'complete') {
                loadUserConversations();
              }
            } catch (parseError) {
              console.error('Error parsing streaming data:', parseError);
            }
          }
        }
      }

    } catch (error) {
      console.error('Error sending message:', error);

      const errorContent = error instanceof Error ? error.message : 'Desculpe, houve um erro ao processar sua solicitação. Por favor, tente novamente.';
      
      dispatch({
        type: 'UPDATE_MESSAGE',
        payload: {
          id: loadingMessage.id,
          updates: {
            content: errorContent,
            isLoading: false
          }
        }
      });
    }
  }, [dispatch, loadUserConversations]);

  return {
    messages: state.messages,
    inputValue: state.inputValue,
    setInputValue: (value: string) => dispatch({ type: 'SET_INPUT_VALUE', payload: value }),
    sendMessage,
  };
}