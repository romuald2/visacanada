"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { RevenueData } from "@/lib/types";

interface RevenueChartProps {
  data: RevenueData;
}

export function RevenueChart({ data }: RevenueChartProps) {
  if (data.series.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-500">
        Aucune donnée disponible
      </div>
    );
  }

  const chartData = data.series.map((item) => ({
    period: item.period,
    Revenus: item.amount,
  }));

  return (
    <div>
      <div className="mb-4">
        <div className="text-sm text-gray-600">
          Total : <span className="font-semibold text-gray-900">{data.total.toLocaleString()} $</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" />
          <YAxis />
          <Tooltip
            formatter={(value) => `${Number(value).toLocaleString()} $`}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="Revenus"
            stroke="#8b5cf6"
            strokeWidth={2}
            dot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
