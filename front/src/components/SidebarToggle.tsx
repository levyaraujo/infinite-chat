import { useState, useEffect } from 'react';
import { useChatContext } from '../contexts/ChatContext';

interface SidebarToggleProps {
  className?: string;
  position?: 'header' | 'sidebar' | 'floating';
  showLabel?: boolean;
}

export default function SidebarToggle({ 
  className = '', 
  position = 'sidebar',
  showLabel = false 
}: SidebarToggleProps) {
  const { state, dispatch } = useChatContext();
  const [isHovered, setIsHovered] = useState(false);
  const [isPressed, setIsPressed] = useState(false);


  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {

      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        toggleSidebar();
      }

      if (e.key === 'Escape' && state.showSidebar) {
        dispatch({ type: 'SET_SHOW_SIDEBAR', payload: false });
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [state.showSidebar, dispatch]);

  const toggleSidebar = () => {
    dispatch({ type: 'SET_SHOW_SIDEBAR', payload: !state.showSidebar });
  };

  const handleMouseDown = () => setIsPressed(true);
  const handleMouseUp = () => setIsPressed(false);
  const handleMouseLeave = () => {
    setIsPressed(false);
    setIsHovered(false);
  };


  const baseStyles = `
    relative inline-flex items-center justify-center
    transition-all duration-200 ease-in-out
    focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-2 focus:ring-offset-gray-900
    active:scale-95
    ${isPressed ? 'scale-95' : 'scale-100'}
    ${className}
  `;

  const positionStyles = {
    header: `
      w-10 h-10 rounded-lg
      bg-gray-800/80 hover:bg-gray-700/90
      border border-gray-600/50 hover:border-gray-500/70
      text-gray-300 hover:text-white
      backdrop-blur-sm
      shadow-lg hover:shadow-xl
    `,
    sidebar: `
      w-8 h-8 rounded-md
      bg-gray-800/60 hover:bg-gray-700/80
      border border-gray-600/30 hover:border-gray-500/50
      text-gray-400 hover:text-white
      ${state.showSidebar ? 'bg-blue-600/20 border-blue-500/30 text-blue-300' : ''}
    `,
    floating: `
      w-12 h-12 rounded-full
      bg-gray-900/90 hover:bg-gray-800/95
      border border-gray-600/40 hover:border-gray-500/60
      text-gray-300 hover:text-white
      backdrop-blur-md
      shadow-2xl hover:shadow-3xl
      fixed top-4 left-4 z-50
    `
  };


  const iconRotation = state.showSidebar ? 'rotate-180' : 'rotate-0';


  const getTooltipText = () => {
    const action = state.showSidebar ? 'Fechar' : 'Abrir';
    const shortcut = position !== 'floating' ? ' (Ctrl+B)' : '';
    return `${action} barra lateral${shortcut}`;
  };

  return (
    <div className="relative group">
      <button
        onClick={toggleSidebar}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={handleMouseLeave}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        className={`${baseStyles} ${positionStyles[position]}`}
        title={getTooltipText()}
        aria-label={getTooltipText()}
        aria-expanded={state.showSidebar}
      >

        <div className={`
          absolute inset-0 rounded-inherit
          bg-gradient-to-r from-blue-500/20 to-purple-500/20
          opacity-0 group-hover:opacity-100
          transition-opacity duration-300
          ${position === 'floating' ? 'blur-md' : 'blur-sm'}
        `} />


        <div className={`
          relative z-10 transition-transform duration-300 ease-out
          ${iconRotation}
          ${isHovered ? 'scale-110' : 'scale-100'}
        `}>

          <svg 
            className={`
              ${position === 'floating' ? 'w-6 h-6' : position === 'header' ? 'w-5 h-5' : 'w-4 h-4'}
              transition-all duration-200
            `} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
            strokeWidth={position === 'floating' ? 1.5 : 2}
          >
            {state.showSidebar ? (

              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                d="M6 18L18 6M6 6l12 12" 
              />
            ) : (

              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                d="M4 6h16M4 12h16M4 18h16" 
              />
            )}
          </svg>
        </div>


      </button>


      {isHovered && !showLabel && (
        <div className={`
          absolute z-50 px-3 py-2 text-xs font-medium text-white
          bg-gray-900/95 border border-gray-600/50 rounded-lg
          backdrop-blur-sm shadow-xl
          transition-all duration-200 ease-out
          ${position === 'floating' 
            ? 'top-full left-1/2 transform -translate-x-1/2 mt-2' 
            : position === 'header'
            ? 'bottom-full left-1/2 transform -translate-x-1/2 mb-2'
            : 'left-full top-1/2 transform -translate-y-1/2 ml-2'
          }
          ${isHovered ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}
        `}>
          {getTooltipText()}
          

          <div className={`
            absolute w-2 h-2 bg-gray-900/95 border-gray-600/50 rotate-45
            ${position === 'floating' 
              ? 'top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 border-b border-r' 
              : position === 'header'
              ? 'bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2 border-t border-l'
              : 'left-0 top-1/2 transform -translate-x-1/2 -translate-y-1/2 border-t border-r'
            }
          `} />
        </div>
      )}
    </div>
  );
}