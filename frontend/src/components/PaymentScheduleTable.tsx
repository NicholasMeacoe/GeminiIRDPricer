import React from 'react';
import { PaymentScheduleItem } from '../types/api';

interface PaymentScheduleTableProps {
  schedule: PaymentScheduleItem[];
  className?: string;
}

const PaymentScheduleTable: React.FC<PaymentScheduleTableProps> = ({ 
  schedule, 
  className = '' 
}) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatNumber = (value: number, decimals: number = 6) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  };

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="min-w-full bg-white border border-gray-300">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Payment Date
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Days
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Fixed Payment
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Floating Payment
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Discount Factor
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Fixed PV
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Floating PV
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {schedule.map((payment, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border-b">
                {payment.payment_date}
              </td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border-b">
                {payment.days}
              </td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 text-right border-b">
                {formatCurrency(payment.fixed_payment)}
              </td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 text-right border-b">
                {formatCurrency(payment.floating_payment)}
              </td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 text-right border-b">
                {formatNumber(payment.discount_factor)}
              </td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 text-right border-b">
                {formatCurrency(payment.pv_fixed)}
              </td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 text-right border-b">
                {formatCurrency(payment.pv_floating)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PaymentScheduleTable;
