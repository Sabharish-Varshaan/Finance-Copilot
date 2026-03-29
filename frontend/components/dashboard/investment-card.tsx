"use client";

import { useState } from "react";
import { UserInvestmentRead, UserInvestmentCreate } from "@/types";
import { updateInvestment } from "@/services/profileService";
import { formatCurrencyCompact } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface InvestmentCardProps {
  investment: UserInvestmentRead | null | undefined;
  onInvestmentUpdated?: (investment: UserInvestmentRead) => void;
}

export function InvestmentCard({ investment, onInvestmentUpdated }: InvestmentCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState<UserInvestmentCreate>(
    investment || {
      total_amount: 0,
      equity_amount: 0,
      debt_amount: 0,
      gold_amount: 0,
    }
  );

  const handleInputChange = (field: keyof UserInvestmentCreate, value: number) => {
    const newData = { ...formData, [field]: value };
    
    // If updating an amount component, update total
    if (field !== "total_amount") {
      newData.total_amount =
        (newData.equity_amount || 0) + (newData.debt_amount || 0) + (newData.gold_amount || 0);
    }
    
    setFormData(newData);
  };

  const handleSubmit = async () => {
    if (formData.total_amount === 0) {
      alert("Please enter investment amount");
      return;
    }

    try {
      setIsLoading(true);
      const result = await updateInvestment(formData);
      onInvestmentUpdated?.(result);
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to update investment:", error);
      alert("Failed to update investment. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const equityPercent = investment?.total_amount ? ((investment.equity_amount / investment.total_amount) * 100).toFixed(0) : 0;
  const debtPercent = investment?.total_amount ? ((investment.debt_amount / investment.total_amount) * 100).toFixed(0) : 0;
  const goldPercent = investment?.total_amount ? ((investment.gold_amount / investment.total_amount) * 100).toFixed(0) : 0;

  if (isEditing) {
    return (
      <Card>
        <div className="pb-4 border-b border-borderSoft">
          <h3 className="text-lg font-semibold">Update Investments</h3>
        </div>
        <div className="space-y-4 pt-4">
          <div>
            <label className="text-sm font-medium">Equity Amount (₹)</label>
            <Input
              type="number"
              min="0"
              value={formData.equity_amount}
              onChange={(e) => handleInputChange("equity_amount", parseFloat(e.target.value) || 0)}
              placeholder="0"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Debt Amount (₹)</label>
            <Input
              type="number"
              min="0"
              value={formData.debt_amount}
              onChange={(e) => handleInputChange("debt_amount", parseFloat(e.target.value) || 0)}
              placeholder="0"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Gold Amount (₹)</label>
            <Input
              type="number"
              min="0"
              value={formData.gold_amount}
              onChange={(e) => handleInputChange("gold_amount", parseFloat(e.target.value) || 0)}
              placeholder="0"
            />
          </div>
          <div className="pt-2 border-t">
            <p className="text-sm font-semibold">
              Total: {formatCurrencyCompact(formData.total_amount)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Equity: {equityPercent}% | Debt: {debtPercent}% | Gold: {goldPercent}%
            </p>
          </div>
          <div className="flex gap-2 pt-4">
            <Button
              onClick={handleSubmit}
              disabled={isLoading}
              className="flex-1"
            >
              {isLoading ? "Saving..." : "Save"}
            </Button>
            <Button
              onClick={() => setIsEditing(false)}
              className="flex-1 bg-transparent border border-accent/30 text-accent hover:bg-accent/10"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  if (!investment || investment.total_amount === 0) {
    return (
      <Card>
        <div className="pb-4 border-b border-borderSoft">
          <h3 className="text-lg font-semibold">Investments</h3>
        </div>
        <div className="space-y-4 pt-4">
          <p className="text-sm text-gray-600">
            No investments recorded — add details to improve your Money Health Score
          </p>
          <Button onClick={() => setIsEditing(true)} className="w-full">
            Add Investments
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="pb-4 border-b border-borderSoft">
        <h3 className="text-lg font-semibold">Investments</h3>
      </div>
      <div className="space-y-4 pt-4">
        <div>
          <p className="text-2xl font-bold">
            {formatCurrencyCompact(investment.total_amount)} invested
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Last updated: {new Date(investment.created_at).toLocaleDateString()}
          </p>
        </div>
        
        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span>Equity</span>
            <span className="font-semibold">{equityPercent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded h-2">
            <div
              className="bg-blue-500 h-2 rounded"
              style={{ width: `${equityPercent}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">{formatCurrencyCompact(investment.equity_amount)}</p>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span>Debt</span>
            <span className="font-semibold">{debtPercent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded h-2">
            <div
              className="bg-green-500 h-2 rounded"
              style={{ width: `${debtPercent}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">{formatCurrencyCompact(investment.debt_amount)}</p>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span>Gold</span>
            <span className="font-semibold">{goldPercent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded h-2">
            <div
              className="bg-yellow-500 h-2 rounded"
              style={{ width: `${goldPercent}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">{formatCurrencyCompact(investment.gold_amount)}</p>
        </div>

        <Button onClick={() => setIsEditing(true)} className="w-full mt-4 bg-transparent border border-accent/30 text-accent hover:bg-accent/10">
          Edit
        </Button>
      </div>
    </Card>
  );
}
