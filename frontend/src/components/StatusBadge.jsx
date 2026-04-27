import React from 'react';

export const StatusBadge = ({ state }) => {
  const normalized = (state || 'pending').toLowerCase();
  
  let baseClasses = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize";
  let colorClasses = "";
  let showDot = false;

  switch (normalized) {
    case 'completed':
      colorClasses = "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border border-green-200 dark:border-green-800";
      break;
    case 'failed':
      colorClasses = "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800";
      break;
    case 'processing':
      colorClasses = "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-800";
      showDot = true;
      break;
    case 'pending':
    default:
      colorClasses = "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400 border border-gray-200 dark:border-gray-700";
      break;
  }

  return (
    <span className={`${baseClasses} ${colorClasses}`}>
      {showDot && (
        <span className="flex h-2 w-2 mr-1.5 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
        </span>
      )}
      {normalized}
    </span>
  );
};
