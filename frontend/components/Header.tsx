"use client";

import Image from "next/image";

export function Header() {
  return (
    <header className="border-b border-outline-variant/30 bg-surface-container-lowest">
      <div className="mx-auto flex max-w-[1200px] items-center justify-between px-8 py-5">
        <div className="flex items-center gap-3">
          <Image
            src="/logo.svg"
            alt="Zomato AI Recommendations logo"
            width={40}
            height={40}
            priority
          />
          <div>
            <h1 className="text-xl font-bold text-primary">
              Zomato AI Recommendations
            </h1>
            <p className="text-sm text-on-surface-variant">
              Find your perfect restaurant
            </p>
          </div>
        </div>
        <p className="hidden text-sm font-medium text-primary sm:block">
          Find your perfect restaurant
        </p>
      </div>
    </header>
  );
}
