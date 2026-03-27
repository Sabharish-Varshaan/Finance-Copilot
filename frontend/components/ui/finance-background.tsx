import type { CSSProperties } from "react";

export function FinanceBackground() {
  const floatingSymbols = [
    { symbol: "₹", left: "8%", delay: "0s", duration: "16s" },
    { symbol: "$", left: "18%", delay: "2.2s", duration: "18s" },
    { symbol: "%", left: "28%", delay: "4.4s", duration: "17s" },
    { symbol: "₹", left: "40%", delay: "1.4s", duration: "19s" },
    { symbol: "$", left: "52%", delay: "6s", duration: "16s" },
    { symbol: "%", left: "64%", delay: "3.8s", duration: "20s" },
    { symbol: "₹", left: "74%", delay: "7.1s", duration: "17s" },
    { symbol: "$", left: "86%", delay: "5.2s", duration: "18s" },
    { symbol: "%", left: "93%", delay: "8.8s", duration: "21s" },
  ];

  return (
    <div className="finance-bg" aria-hidden="true">
      <div className="finance-grid" />
      <div className="wave" />
      <div className="wave wave-2" />

      {floatingSymbols.map((item, index) => (
        <span
          key={`${item.symbol}-${index}`}
          className="currency-float"
          style={
            {
              "--float-left": item.left,
              "--float-delay": item.delay,
              "--float-duration": item.duration,
            } as CSSProperties
          }
        >
          {item.symbol}
        </span>
      ))}
    </div>
  );
}
