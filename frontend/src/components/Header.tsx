import Link from "next/link";
import { ShoppingBasket } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-bold text-brand">
          <ShoppingBasket className="h-6 w-6" />
          <span className="text-lg">Price Pantry</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm text-gray-600">
          <Link href="/" className="hover:text-brand">
            Home
          </Link>
          <Link href="/search" className="hover:text-brand">
            Search
          </Link>
        </nav>
      </div>
    </header>
  );
}
