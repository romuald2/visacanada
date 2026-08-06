"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { SuccessRateByProgram } from "@/lib/types";

interface ApprovalRateChartProps {
  data: SuccessRateByProgram[];
}

export function ApprovalRateChart({ data }: ApprovalRateChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-500">
        Aucune donnée disponible
      </div>
    );
  }

  const chartData = data.map((item) => ({
    name: item.program_name,
    Approuvés: item.approved,
    Refusés: item.refused,
    "Taux d'approbation": item.approval_rate,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="Approuvés" fill="#10b981" />
        <Bar dataKey="Refusés" fill="#ef4444" />
      </BarChart>
    </ResponsiveContainer>
  );
}
