import type { Message } from '../types/Message';
import Markdown from "react-markdown";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.sender === 'user';

  // Function to get agent display info
  const getAgentInfo = (agent?: string) => {
    if (!agent) return null;
    
    const agentMap: Record<string, { name: string; color: string; icon: string }> = {
      'KnowledgeAgent': { name: 'KnowledgeAgent', color: 'bg-gradient-to-r from-[#EDC902] to-[#22E920]', icon: '📚' },
      'MathAgent': { name: 'MathAgent', color: 'bg-gray-500', icon: '🤖' },
    };
    
    return agentMap[agent] || { name: agent, color: 'bg-gray-500', icon: '🤖' };
  };

  const agentInfo = getAgentInfo(message.agent);

  return (
    <div className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`px-4 py-2 rounded-lg relative ${isUser
        ? 'bg-[#303030] text-white ml-auto max-w-xs lg:max-w-md'
        : 'border border-gray-900 text-gray-100 w-full pt-5'
        }`}>
        {message.isLoading || !message.content ? (
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-300">Pensando</span>
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        ) : (
          <div className={`prose max-w-none break-words ${
            isUser ? 'prose-invert' : 'prose-gray prose-invert'
          }`}>
            <Markdown
              components={{
                ul: ({ children }) => (
                  <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-inside space-y-1 my-2">{children}</ol>
                ),
                li: ({ children }) => (
                  <li className="text-inherit">{children}</li>
                ),
                p: ({ children }) => (
                  <p className="mb-2 last:mb-0">{children}</p>
                ),
                h1: ({ children }) => (
                  <h1 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-base font-bold mb-2 mt-3 first:mt-0">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-sm font-bold mb-1 mt-2 first:mt-0">{children}</h3>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold">{children}</strong>
                ),
                em: ({ children }) => (
                  <em className="italic">{children}</em>
                ),
                code: ({ children }) => (
                  <code className="bg-gray-700/50 px-1 py-0.5 rounded text-sm font-mono">{children}</code>
                ),
                pre: ({ children }) => (
                  <pre className="bg-gray-700/50 p-3 rounded-md overflow-x-auto my-2">{children}</pre>
                )
              }}
            >
              {message.content}
            </Markdown>
          </div>
        )}
        
        {!isUser && agentInfo && (
          <div 
            className={`absolute -top-3 -left-3 px-2 py-1 ${agentInfo.color} rounded-full flex items-center 
            justify-center text-white text-xs font-medium shadow-lg border-2 border-gray-800 z-10 whitespace-nowrap`}
            title={`Agent: ${message.agent}`}
          >
            <span className="text-[12px]">{agentInfo.name}</span>
          </div>
        )}
      </div>
    </div>
  );
}