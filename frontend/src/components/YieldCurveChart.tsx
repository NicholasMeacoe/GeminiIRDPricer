import React, { useEffect, useRef } from 'react';

interface YieldCurveChartProps {
  plotData: any;
  className?: string;
}

const YieldCurveChart: React.FC<YieldCurveChartProps> = ({ plotData, className }) => {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current || !plotData) return;

    let destroyed = false;
    (async () => {
      try {
        const parsedData = typeof plotData === 'string' ? JSON.parse(plotData) : plotData;

        // Lazy‑load Plotly only when needed
        const mod: any = await import('plotly.js/dist/plotly');
        const Plotly = mod?.default || mod;
        if (destroyed || !chartRef.current || !Plotly) return;

        // Clear any existing plot
        try { Plotly.purge(chartRef.current); } catch {}

        // Update layout for dark theme
        const darkLayout = {
          ...parsedData.layout,
          responsive: true,
          margin: { l: 60, r: 40, t: 60, b: 60 },
          paper_bgcolor: 'rgba(15, 23, 42, 0.8)',
          plot_bgcolor: 'rgba(15, 23, 42, 0.4)',
          font: {
            color: '#e2e8f0',
            family: 'Inter, sans-serif'
          },
          title: {
            text: 'Yield Curve',
            font: {
              color: '#64ffda',
              size: 18,
              family: 'Inter, sans-serif'
            }
          },
          xaxis: {
            title: {
              text: 'Date',
              font: { color: '#94a3b8' }
            },
            tickfont: { color: '#cbd5e1' },
            gridcolor: 'rgba(100, 255, 218, 0.1)',
            showgrid: true
          },
          yaxis: {
            title: {
              text: 'Rate',
              font: { color: '#94a3b8' }
            },
            tickfont: { color: '#cbd5e1' },
            gridcolor: 'rgba(100, 255, 218, 0.1)',
            showgrid: true
          }
        } as any;

        // Update trace styling for dark theme
        const darkData = parsedData.data.map((trace: any) => ({
          ...trace,
          line: {
            color: '#64ffda',
            width: 3
          },
          marker: {
            color: '#00bcd4',
            size: 6,
            line: {
              color: '#64ffda',
              width: 2
            }
          }
        }));

        // Create the plot
        await Plotly.newPlot(
          chartRef.current,
          darkData,
          darkLayout,
          {
            displayModeBar: false,
            staticPlot: false
          }
        );
      } catch (error) {
        console.error('Error creating yield curve plot (Plotly may be missing):', error);
        if (chartRef.current) {
          chartRef.current.innerHTML = '<div style="padding:8px;color:#94a3b8">Chart unavailable (Plotly not loaded). Showing data table instead.</div>';
        }
      }
    })();

    return () => {
      destroyed = true;
      // Best effort cleanup if Plotly was loaded
      const cleanup = async () => {
        try {
          const mod: any = await import('plotly.js/dist/plotly');
          const Plotly = mod?.default || mod;
          if (chartRef.current && Plotly?.purge) Plotly.purge(chartRef.current);
        } catch {}
      };
      cleanup();
    };
  }, [plotData]);

  return (
    <div className={className}>
      <div ref={chartRef} style={{ width: '100%', height: '400px' }} />
    </div>
  );
};

export default YieldCurveChart;
