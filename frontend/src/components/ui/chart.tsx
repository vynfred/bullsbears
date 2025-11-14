// src/components/ui/chart.tsx
'use client';

import * as React from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { cn } from '@/lib/utils';

// Chart Container - keeps your relative positioning
export function ChartContainer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("w-full h-full relative", className)}>{children}</div>;
}

// Chart Tooltip - Recharts default, but we replace it with ChartTooltipContent
export function ChartTooltip({ content }: { content?: React.ReactNode }) {
  return <Tooltip content={content} />;
}

// Chart Tooltip Content - YOUR EXACT DESIGN
export function ChartTooltipContent({
  active,
  payload,
  label,
  formatter,
  labelFormatter,
  className,
}: {
  active?: boolean;
  payload?: any[];
  label?: string;
  formatter?: (value: any, name: any) => any[];
  labelFormatter?: (label: any) => string;
  className?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;

  const formattedLabel = labelFormatter ? labelFormatter(label) : label;

  return (
    <div
      className={cn(
        "bg-gray-900 p-3 border border-gray-700 rounded-lg shadow-xl",
        className
      )}
    >
      {formattedLabel && (
        <p className="text-xs font-medium text-gray-300 mb-1">{formattedLabel}</p>
      )}
      {payload.map((entry, index) => {
        const [formattedValue, formattedName] =
          formatter && entry.value !== undefined
            ? formatter(entry.value, entry.name)
            : [entry.value, entry.name];
        return (
          <div
            key={index}
            className="flex items-center justify-between gap-4 text-sm"
          >
            <span className="text-gray-400">{formattedName}:</span>
            <span className="font-medium text-white">{formattedValue}</span>
          </div>
        );
      })}
    </div>
  );
}

// Main Chart Component
export function Chart({
  data,
  config,
  type = 'line',
  height = 300,
  className,
}: {
  data: any[];
  config: Record<string, { label?: string; color?: string }>;
  type?: 'line' | 'bar' | 'pie';
  height?: number;
  className?: string;
}) {
  const colors = Object.values(config).map(c => c.color || '#8884d8');

  if (type === 'pie') {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={(props: any) => {
              const { name, percent } = props;
              return `${name} ${(percent * 100).toFixed(0)}%`;
            }}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltipContent />} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  const ChartComponent = type === 'bar' ? BarChart : LineChart;
  const DataComponent = type === 'bar' ? Bar : Line;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ChartComponent data={data} className={className}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip content={<ChartTooltipContent />} />
        {Object.keys(config).map((key) => {
          const configItem = config[key];
          return (
            <DataComponent
              key={key}
              type="monotone"
              dataKey={key}
              stroke={configItem.color || '#8884d8'}
              fill={configItem.color || '#8884d8'}
            />
          );
        })}
      </ChartComponent>
    </ResponsiveContainer>
  );
}