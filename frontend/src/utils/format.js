import { format } from 'date-fns';
import { v4 as uuidv4 } from 'uuid';

export const formatPaise = (paise) => {
  if (paise == null) return '₹0.00';
  const rupeesStr = (Math.abs(paise) / 100).toFixed(2);
  const [integerPart, decimalPart] = rupeesStr.split('.');
  
  let formattedInteger = integerPart;
  if (integerPart.length > 3) {
    const lastThree = integerPart.slice(-3);
    const otherNumbers = integerPart.slice(0, -3);
    const chunks = [];
    for (let i = otherNumbers.length; i > 0; i -= 2) {
      chunks.unshift(otherNumbers.slice(Math.max(0, i - 2), i));
    }
    formattedInteger = chunks.join(',') + ',' + lastThree;
  }
  
  const sign = paise < 0 ? '-' : '';
  return `${sign}₹${formattedInteger}.${decimalPart}`;
};

export const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return format(date, 'dd MMM yyyy, h:mm a');
};

export const formatState = (state) => {
  switch (state?.toLowerCase()) {
    case 'completed':
      return { label: 'Completed', color: 'green' };
    case 'failed':
      return { label: 'Failed', color: 'red' };
    case 'processing':
      return { label: 'Processing', color: 'blue' };
    case 'pending':
    default:
      return { label: 'Pending', color: 'yellow' };
  }
};

export const generateIdempotencyKey = () => {
  return uuidv4();
};
