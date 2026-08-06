"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { ProcessingTimeData } from "@/lib/types";

interface ProcessingTimeChartProps {
  data: ProcessingTimeData;
}

export function ProcessingTimeChart({ data }: ProcessingTimeChartProps) {
  if (data.by_program.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-500">
        Aucune donnée disponible
      </div>
    );
  }

  const chartData = data.by_program.map((item) => ({
    name: item.program_name,
    "Jours moyens": Math.round(item.avg_days),
    "Nombre de dossiers": item.count,
  }));

  return (
    <div>
      <div className="mb-4">
        <div className="text-sm text-gray-600">
          Temps moyen global : <span className="font-semibold text-gray-900">{Math.round(data.overall_avg)} jours</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="Jours moyens" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
