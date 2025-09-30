import React from 'react';
import { YieldCurveData } from '../types/api';

interface YieldCurveTableProps {
  yieldCurve: YieldCurveData[];
  onRateChange: (maturity: number, newRate: number) => void;
  className?: string;
}

const YieldCurveTable: React.FC<YieldCurveTableProps> = ({ 
  yieldCurve, 
  onRateChange, 
  className = '' 
}) => {
  const handleRateChange = (maturity: number, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      onRateChange(maturity, numValue);
    }
  };

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="min-w-full bg-white border border-gray-300">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Maturity (Years)
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
              Rate (%)
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {yieldCurve.map((point, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border-b">
                <input
                  type="number"
                  step="any"
                  value={point["Maturity (Years)"]}
                  className="w-full p-1 border rounded bg-gray-100 text-gray-600"
                  readOnly
                />
              </td>
              <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border-b">
                <input
                  type="number"
                  step="0.01"
                  value={point.Rate.toFixed(4)}
                  onChange={(e) => handleRateChange(point["Maturity (Years)"], e.target.value)}
                  className="w-full p-1 border rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default YieldCurveTable;
