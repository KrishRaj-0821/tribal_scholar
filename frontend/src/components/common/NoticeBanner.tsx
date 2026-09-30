import React from 'react';
import { AlertCircle, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';

interface NoticeBannerProps {
  type?: 'warning' | 'info' | 'error' | 'success';
  title?: string;
  message: string | React.ReactNode;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export const NoticeBanner: React.FC<NoticeBannerProps> = ({
  type = 'info',
  title,
  message,
  actionText,
  onAction,
  className = ''
}) => {
  const configs = {
    warning: {
      bg: 'bg-[#FFF9C4]',
      border: 'border-[#FFC107]',
      text: 'text-[#7A5E00]',
      titleColor: 'text-[#5D4037]',
      icon: <AlertTriangle className="w-5 h-5 text-[#C85A17] flex-shrink-0" />
    },
    info: {
      bg: 'bg-[#E1F5FE]',
      border: 'border-[#0288D1]',
      text: 'text-[#01579B]',
      titleColor: 'text-[#0D47A1]',
      icon: <Info className="w-5 h-5 text-[#0288D1] flex-shrink-0" />
    },
    error: {
      bg: 'bg-[#FFEBEE]',
      border: 'border-[#A71D2A]',
      text: 'text-[#B71C1C]',
      titleColor: 'text-[#7F0000]',
      icon: <AlertCircle className="w-5 h-5 text-[#A71D2A] flex-shrink-0" />
    },
    success: {
      bg: 'bg-[#E8F5E9]',
      border: 'border-[#198754]',
      text: 'text-[#1B5E20]',
      titleColor: 'text-[#1B5E20]',
      icon: <CheckCircle2 className="w-5 h-5 text-[#198754] flex-shrink-0" />
    }
  };

  const config = configs[type];

  return (
    <div 
      className={`border-l-4 ${config.border} ${config.bg} p-3.5 rounded-r text-sm border-t border-r border-b ${config.border} ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        {config.icon}
        <div className="flex-1">
          {title && (
            <div className={`font-bold ${config.titleColor} mb-0.5`}>
              {title}
            </div>
          )}
          <div className={`${config.text} leading-relaxed`}>
            {message}
          </div>
        </div>
        {actionText && onAction && (
          <button
            onClick={onAction}
            className="gov-btn gov-btn-warning text-xs font-bold py-1 px-3 ml-2 flex-shrink-0 self-center"
          >
            {actionText}
          </button>
        )}
      </div>
    </div>
  );
};
