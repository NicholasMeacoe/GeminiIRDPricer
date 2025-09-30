import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// Form validation schema
const swapFormSchema = z.object({
  notional: z.string().min(1, 'Notional is required'),
  fixed_rate: z.number().min(0, 'Fixed rate must be positive'),
  maturity_date: z.string().min(1, 'Maturity date is required'),
});

type SwapFormData = z.infer<typeof swapFormSchema>;

interface SwapPricingFormProps {
  onPriceSwap: (data: SwapFormData) => void;
  onSolveParRate: (data: Omit<SwapFormData, 'fixed_rate'>) => void;
  initialValues?: Partial<SwapFormData>;
  loading?: boolean;
  className?: string;
}

const SwapPricingForm: React.FC<SwapPricingFormProps> = ({
  onPriceSwap,
  onSolveParRate,
  initialValues,
  loading = false,
  className = '',
}) => {
  const [action, setAction] = useState<'price' | 'solve' | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    getValues,
  } = useForm<SwapFormData>({
    resolver: zodResolver(swapFormSchema),
    defaultValues: {
      notional: initialValues?.notional || '10m',
      fixed_rate: initialValues?.fixed_rate || 0,
      maturity_date: initialValues?.maturity_date || '5y',
    },
  });

  const onSubmit = (data: SwapFormData) => {
    if (action === 'price') {
      onPriceSwap(data);
    } else if (action === 'solve') {
      const { fixed_rate, ...solveData } = data;
      onSolveParRate(solveData);
    }
  };

  const handlePriceClick = () => {
    setAction('price');
    handleSubmit(onSubmit)();
  };

  const handleSolveClick = () => {
    setAction('solve');
    handleSubmit(onSubmit)();
  };

  return (
    <div className={className}>
      <form className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Notional */}
          <div>
            <label htmlFor="notional" className="block text-sm font-medium text-gray-700">
              Notional
            </label>
            <input
              {...register('notional')}
              type="text"
              id="notional"
              placeholder="e.g., 10m"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
            {errors.notional && (
              <p className="mt-1 text-sm text-red-600">{errors.notional.message}</p>
            )}
          </div>

          {/* Fixed Rate */}
          <div>
            <label htmlFor="fixed_rate" className="block text-sm font-medium text-gray-700">
              Fixed Rate (%)
            </label>
            <input
              {...register('fixed_rate', { valueAsNumber: true })}
              type="number"
              id="fixed_rate"
              step="0.01"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
            {errors.fixed_rate && (
              <p className="mt-1 text-sm text-red-600">{errors.fixed_rate.message}</p>
            )}
          </div>

          {/* Maturity Date */}
          <div>
            <label htmlFor="maturity_date" className="block text-sm font-medium text-gray-700">
              Maturity
            </label>
            <input
              {...register('maturity_date')}
              type="text"
              id="maturity_date"
              placeholder="e.g., 5y or 2028-12-31"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
            {errors.maturity_date && (
              <p className="mt-1 text-sm text-red-600">{errors.maturity_date.message}</p>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-4">
          <button
            type="button"
            onClick={handlePriceClick}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading && action === 'price' && (
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            Price Swap
          </button>

          <button
            type="button"
            onClick={handleSolveClick}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading && action === 'solve' && (
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-700" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            Solve Par Rate
          </button>
        </div>
      </form>
    </div>
  );
};

export default SwapPricingForm;
