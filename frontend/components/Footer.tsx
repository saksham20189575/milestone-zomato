export function Footer() {
  return (
    <footer className="mt-auto border-t border-outline-variant/30 bg-surface-container-lowest">
      <div className="mx-auto max-w-[1200px] px-8 py-6 text-center">
        <p className="text-sm font-semibold text-on-surface">Zomato AI</p>
        <p className="mt-1 text-xs text-on-surface-variant">
          © {new Date().getFullYear()} Zomato AI Recommendations. All rights
          reserved.
        </p>
      </div>
    </footer>
  );
}
