import Link from "next/link";
import { BarChart3 } from "lucide-react";

const links = [
  { href: "/", label: "Home" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/markets", label: "Market Search" },
  { href: "/evidence", label: "Evidence" },
  { href: "/benchmark", label: "Benchmark" },
  { href: "/methodology", label: "Methodology" }
];

export function Nav() {
  return (
    <header className="border-b bg-white/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BarChart3 className="size-5" aria-hidden="true" />
          </span>
          <span>Polymarket Sentiment vs Price Movement Dashboard</span>
        </Link>
        <nav className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-2 hover:bg-muted hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
