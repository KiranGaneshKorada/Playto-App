import React from 'react';

export const LoadingSkeleton = ({ type = 'card' }) => {
  if (type === 'card') {
    return (
      <div className="p-6 bg-gray-800 rounded-xl animate-pulse w-full max-w-sm">
        <div className="h-4 bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="h-10 bg-gray-700 rounded w-3/4 mb-4"></div>
        <div className="h-4 bg-gray-700 rounded w-1/2 mt-8"></div>
        <div className="h-4 bg-gray-700 rounded w-1/2 mt-2"></div>
      </div>
    );
  }

  if (type === 'table') {
    return (
      <div className="w-full animate-pulse space-y-4">
        <div className="h-10 bg-gray-800 rounded w-full"></div>
        <div className="h-12 bg-gray-800 rounded w-full opacity-70"></div>
        <div className="h-12 bg-gray-800 rounded w-full opacity-60"></div>
        <div className="h-12 bg-gray-800 rounded w-full opacity-50"></div>
      </div>
    );
  }

  return <div className="h-4 bg-gray-700 rounded w-full animate-pulse"></div>;
};
