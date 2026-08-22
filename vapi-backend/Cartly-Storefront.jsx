import React, { useState, useMemo, useRef, useEffect } from "react";
import {
  Search, Mic, ShoppingCart, X, Plus, Minus, Star, Sparkles,
  RefreshCw, Leaf, ArrowLeftRight, MapPin, User, Check,
  Apple, Milk, Croissant, CupSoda, Package, Cookie, SprayCan, Beef,
  ChevronRight, Menu,
} from "lucide-react";

/* ----------------------------- demo catalog ----------------------------- */

const CATEGORIES = [
  { id: "produce", label: "Produce", icon: Apple, tint: "bg-emerald-50 text-emerald-700", ring: "ring-emerald-100" },
  { id: "dairy", label: "Dairy", icon: Milk, tint: "bg-sky-50 text-sky-700", ring: "ring-sky-100" },
  { id: "bakery", label: "Bakery", icon: Croissant, tint: "bg-amber-50 text-amber-700", ring: "ring-amber-100" },
  { id: "beverages", label: "Beverages", icon: CupSoda, tint: "bg-cyan-50 text-cyan-700", ring: "ring-cyan-100" },
  { id: "pantry", label: "Pantry", icon: Package, tint: "bg-orange-50 text-orange-700", ring: "ring-orange-100" },
  { id: "snacks", label: "Snacks", icon: Cookie, tint: "bg-rose-50 text-rose-700", ring: "ring-rose-100" },
  { id: "household", label: "Household", icon: SprayCan, tint: "bg-violet-50 text-violet-700", ring: "ring-violet-100" },
  { id: "meat", label: "Meat & Protein", icon: Beef, tint: "bg-red-50 text-red-700", ring: "ring-red-100" },
];

const catMap = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]));

const PRODUCTS = [
  { id: "p1", name: "Organic Strawberries", category: "produce", price: 4.49, unit: "1 lb box", rating: 4.7, reviews: 812 },
  { id: "p2", name: "Avocados", category: "produce", price: 2.99, unit: "pack of 3", rating: 4.5, reviews: 431 },
  { id: "p3", name: "Baby Spinach", category: "produce", price: 3.29, unit: "5 oz bag", rating: 4.4, reviews: 265 },
  { id: "p4", name: "Whole Milk", category: "dairy", price: 3.79, unit: "1 gal", rating: 4.6, reviews: 998 },
  { id: "p5", name: "Oat Milk", category: "dairy", price: 4.99, unit: "64 fl oz", rating: 4.8, reviews: 540 },
  { id: "p6", name: "Greek Yogurt", category: "dairy", price: 5.49, unit: "32 oz tub", rating: 4.6, reviews: 322 },
  { id: "p7", name: "Sourdough Loaf", category: "bakery", price: 4.99, unit: "1 loaf", rating: 4.7, reviews: 210 },
  { id: "p8", name: "Everything Bagels", category: "bakery", price: 3.49, unit: "pack of 6", rating: 4.5, reviews: 176 },
  { id: "p9", name: "Sparkling Water", category: "beverages", price: 5.99, unit: "12-pack", rating: 4.6, reviews: 601 },
  { id: "p10", name: "Cold Brew Coffee", category: "beverages", price: 6.49, unit: "32 fl oz", rating: 4.4, reviews: 189 },
  { id: "p11", name: "Basmati Rice", category: "pantry", price: 7.99, unit: "5 lb bag", rating: 4.8, reviews: 733 },
  { id: "p12", name: "Extra Virgin Olive Oil", category: "pantry", price: 9.49, unit: "16.9 fl oz", rating: 4.7, reviews: 402 },
  { id: "p13", name: "Honey", category: "pantry", price: 6.29, unit: "12 oz jar", rating: 4.6, reviews: 288 },
  { id: "p14", name: "Baked Veggie Chips", category: "snacks", price: 3.99, unit: "8 oz bag", rating: 4.3, reviews: 154 },
  { id: "p15", name: "Mixed Nuts", category: "snacks", price: 8.99, unit: "16 oz jar", rating: 4.7, reviews: 267 },
  { id: "p16", name: "Dish Soap", category: "household", price: 3.29, unit: "16 fl oz", rating: 4.5, reviews: 341 },
  { id: "p17", name: "Paper Towels", category: "household", price: 12.99, unit: "pack of 6", rating: 4.6, reviews: 522 },
  { id: "p18", name: "Free-Range Chicken Breast", category: "meat", price: 9.99, unit: "1.5 lb", rating: 4.6, reviews: 298 },
  { id: "p19", name: "Wild Salmon Fillet", category: "meat", price: 13.49, unit: "1 lb", rating: 4.8, reviews: 176 },
  { id: "p20", name: "Extra-Firm Tofu", category: "meat", price: 2.79, unit: "14 oz", rating: 4.4, reviews: 122 },
];

const byId = Object.fromEntries(PRODUCTS.map((p) => [p.id, p]));

const SUGGESTIONS = [
  { kind: "replenish", title: "Running low on Sourdough Loaf", note: "You usually re-add this every 6\u20137 days", productId: "p7", icon: RefreshCw },
  { kind: "seasonal", title: "Strawberries are in season", note: "Peak freshness through late August", productId: "p1", icon: Leaf },
  { kind: "substitute", title: "Try Oat Milk instead of Whole Milk", note: "Dairy-free, similar texture", productId: "p5", icon: ArrowLeftRight },
];

const VOICE_DEMO_LINE = "\u201cAdd two bottles of oat milk and some strawberries\u201d";

/* --------------------------------- utils --------------------------------- */

function currency(n) {
  return `$${n.toFixed(2)}`;
}

/* --------------------------------- app --------------------------------- */

export default function CartlyStorefront() {
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [maxPrice, setMaxPrice] = useState(null);
  const [cart, setCart] = useState({}); // productId -> qty
  const [cartOpen, setCartOpen] = useState(false);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceState, setVoiceState] = useState("idle"); // idle | listening | heard | done
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);

  const showToast = (msg) => {
    setToast(msg);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2400);
  };

  const addToCart = (id, qty = 1, label) => {
    setCart((c) => ({ ...c, [id]: (c[id] || 0) + qty }));
    showToast(`Added ${label || byId[id]?.name} to your list`);
  };
  const setQty = (id, qty) => {
    setCart((c) => {
      if (qty <= 0) {
        const next = { ...c };
        delete next[id];
        return next;
      }
      return { ...c, [id]: qty };
    });
  };
  const removeFromCart = (id) => setQty(id, 0);
  const swapItem = (fromId, toId) => {
    setCart((c) => {
      const next = { ...c };
      const qty = next[fromId] || 1;
      delete next[fromId];
      next[toId] = (next[toId] || 0) + qty;
      return next;
    });
    showToast(`Swapped for ${byId[toId]?.name}`);
  };

  const cartCount = Object.values(cart).reduce((a, b) => a + b, 0);
  const cartTotal = Object.entries(cart).reduce((sum, [id, qty]) => sum + (byId[id]?.price || 0) * qty, 0);
  const hasMilk = !!cart["p4"];

  const filtered = useMemo(() => {
    return PRODUCTS.filter((p) => {
      const matchesQuery = query.trim() === "" || p.name.toLowerCase().includes(query.toLowerCase());
      const matchesCategory = activeCategory === "all" || p.category === activeCategory;
      const matchesPrice = maxPrice == null || p.price <= maxPrice;
      return matchesQuery && matchesCategory && matchesPrice;
    });
  }, [query, activeCategory, maxPrice]);

  /* scripted voice demo sequence \u2014 illustrates the UX; not live recognition.
     Wire the real thing with @elevenlabs/react's useConversation + clientTools,
     see the integration notes shared alongside this file. */
  const runVoiceDemo = () => {
    setVoiceOpen(true);
    setVoiceState("listening");
    setTimeout(() => setVoiceState("heard"), 1700);
    setTimeout(() => {
      addToCart("p5", 2, "Oat Milk");
      addToCart("p1", 1, "Organic Strawberries");
      setVoiceState("done");
    }, 2600);
    setTimeout(() => setVoiceOpen(false), 4200);
  };

  useEffect(() => () => clearTimeout(toastTimer.current), []);

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      {/* utility bar */}
      <div className="hidden sm:flex items-center justify-between bg-slate-950 px-6 py-1.5 text-xs text-slate-300">
        <span className="flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" /> Deliver to Ashta, Madhya Pradesh 465001</span>
        <span className="flex items-center gap-1.5 text-indigo-300"><Sparkles className="h-3.5 w-3.5" /> Say it, and it's on your list \u2014 powered by Cartly</span>
      </div>

      {/* main header */}
      <header className="sticky top-0 z-30 bg-slate-900 px-4 py-3 shadow-sm sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center gap-3 sm:gap-6">
          <button className="text-slate-300 sm:hidden"><Menu className="h-6 w-6" /></button>
          <div className="flex items-baseline gap-1 select-none">
            <span className="font-serif text-2xl font-bold tracking-tight text-white">Cartly</span>
            <span className="hidden h-1.5 w-1.5 rounded-full bg-indigo-400 sm:inline-block" />
          </div>

          {/* listening search bar \u2014 the signature element */}
          <div className="relative flex-1">
            <div
              className={`flex items-center rounded-full border-2 bg-white pl-4 pr-1.5 py-1.5 transition-colors ${
                voiceOpen ? "border-indigo-400 ring-4 ring-indigo-100" : "border-transparent"
              }`}
            >
              <Search className="h-4 w-4 shrink-0 text-slate-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search Cartly, or tap the mic and just say it"
                className="ml-2 w-full bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
              />
              <button
                onClick={runVoiceDemo}
                aria-label="Talk to Cartly"
                className={`ml-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors ${
                  voiceOpen ? "bg-indigo-600 text-white" : "bg-indigo-50 text-indigo-600 hover:bg-indigo-100"
                }`}
              >
                <Mic className="h-4 w-4" />
              </button>
            </div>
          </div>

          <button className="hidden items-center gap-1.5 text-sm text-slate-200 hover:text-white sm:flex">
            <User className="h-5 w-5" /> Account
          </button>
          <button onClick={() => setCartOpen(true)} className="relative flex items-center gap-1.5 text-slate-200 hover:text-white">
            <ShoppingCart className="h-6 w-6" />
            <span className="hidden text-sm sm:inline">List</span>
            {cartCount > 0 && (
              <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-amber-400 text-[11px] font-bold text-slate-900">
                {cartCount}
              </span>
            )}
          </button>
        </div>

        {/* category strip */}
        <div className="mx-auto mt-3 flex max-w-7xl gap-2 overflow-x-auto pb-0.5">
          <button
            onClick={() => setActiveCategory("all")}
            className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
              activeCategory === "all" ? "bg-white text-slate-900" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            All items
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              onClick={() => setActiveCategory(c.id)}
              className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
                activeCategory === c.id ? "bg-white text-slate-900" : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {/* hero */}
        <section className="mb-8 grid grid-cols-1 items-center gap-6 overflow-hidden rounded-2xl bg-slate-900 px-6 py-8 sm:grid-cols-2 sm:px-10 sm:py-10">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-300">Voice-first grocery list</p>
            <h1 className="font-serif text-3xl font-bold leading-tight text-white sm:text-4xl">
              Just say what you need.
            </h1>
            <p className="mt-3 max-w-md text-sm text-slate-300">
              Cartly listens, sorts, and remembers \u2014 so your list stays accurate whether you speak it, type it, or tap it.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {["\u201cAdd milk\u201d", "\u201cFind snacks under $5\u201d", "\u201cRemove bread\u201d"].map((c) => (
                <span key={c} className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-200">{c}</span>
              ))}
            </div>
            <button
              onClick={runVoiceDemo}
              className="mt-6 flex items-center gap-2 rounded-full bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              <Mic className="h-4 w-4" /> Try talking to Cartly
            </button>
          </div>
          <div className="relative mx-auto flex h-40 w-40 items-center justify-center sm:h-48 sm:w-48">
            <span className="absolute h-full w-full animate-ping rounded-full bg-indigo-500/20" />
            <span className="absolute h-3/4 w-3/4 animate-pulse rounded-full bg-indigo-500/30" />
            <span className="relative flex h-20 w-20 items-center justify-center rounded-full bg-indigo-600 shadow-lg shadow-indigo-900/40">
              <Mic className="h-9 w-9 text-white" />
            </span>
          </div>
        </section>

        {/* smart suggestions */}
        <section className="mb-8">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-600" />
            <h2 className="font-serif text-lg font-bold text-slate-900">Suggested for you</h2>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {SUGGESTIONS.map((s) => {
              const Icon = s.icon;
              const product = byId[s.productId];
              return (
                <div key={s.title} className="flex items-start gap-3 rounded-xl border border-indigo-100 bg-indigo-50/60 p-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-indigo-600 ring-4 ring-indigo-50">
                    <Icon className="h-4.5 w-4.5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-800">{s.title}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{s.note}</p>
                    <button
                      onClick={() => addToCart(product.id, 1)}
                      className="mt-2 text-xs font-semibold text-indigo-700 hover:text-indigo-900"
                    >
                      Add to list \u2192
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* filters row */}
        <section className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Price</span>
          {[
            { label: "Any", val: null },
            { label: "Under $5", val: 5 },
            { label: "Under $10", val: 10 },
          ].map((f) => (
            <button
              key={f.label}
              onClick={() => setMaxPrice(f.val)}
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                maxPrice === f.val ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
              }`}
            >
              {f.label}
            </button>
          ))}
          <span className="ml-auto text-xs text-slate-400">{filtered.length} items</span>
        </section>

        {/* product grid */}
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {filtered.map((p) => {
            const cat = catMap[p.category];
            const Icon = cat.icon;
            const qty = cart[p.id] || 0;
            return (
              <div key={p.id} className="group flex flex-col rounded-xl border border-slate-200 bg-white p-3 transition-shadow hover:shadow-md">
                <div className={`mb-3 flex h-24 items-center justify-center rounded-lg ${cat.tint} ring-1 ${cat.ring}`}>
                  <Icon className="h-9 w-9" strokeWidth={1.5} />
                </div>
                <span className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{cat.label}</span>
                <h3 className="text-sm font-semibold leading-snug text-slate-800">{p.name}</h3>
                <p className="mt-0.5 text-xs text-slate-400">{p.unit}</p>
                <div className="mt-1 flex items-center gap-1 text-xs text-amber-500">
                  <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                  <span className="text-slate-500">{p.rating} ({p.reviews})</span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="font-serif text-base font-bold text-slate-900">{currency(p.price)}</span>
                  {qty === 0 ? (
                    <button
                      onClick={() => addToCart(p.id)}
                      className="rounded-full bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
                    >
                      Add
                    </button>
                  ) : (
                    <div className="flex items-center gap-1 rounded-full bg-slate-100 px-1">
                      <button onClick={() => setQty(p.id, qty - 1)} className="rounded-full p-1.5 text-slate-600 hover:bg-slate-200"><Minus className="h-3.5 w-3.5" /></button>
                      <span className="w-4 text-center text-xs font-semibold">{qty}</span>
                      <button onClick={() => setQty(p.id, qty + 1)} className="rounded-full p-1.5 text-slate-600 hover:bg-slate-200"><Plus className="h-3.5 w-3.5" /></button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="col-span-full rounded-xl border border-dashed border-slate-300 p-10 text-center text-sm text-slate-400">
              Nothing matches that search. Try a different item or clear the price filter.
            </div>
          )}
        </section>
      </main>

      <footer className="mt-10 bg-slate-950 px-6 py-8 text-sm text-slate-400">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 sm:flex-row">
          <span className="font-serif text-lg font-bold text-white">Cartly</span>
          <p className="text-xs">Manages your shopping list by voice or text. Doesn't place orders or process payments.</p>
        </div>
      </footer>

      {/* cart drawer */}
      {cartOpen && (
        <div className="fixed inset-0 z-40 flex justify-end">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setCartOpen(false)} />
          <div className="relative flex h-full w-full max-w-sm flex-col bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <h2 className="font-serif text-lg font-bold">Your list</h2>
              <button onClick={() => setCartOpen(false)} className="text-slate-400 hover:text-slate-700"><X className="h-5 w-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              {cartCount === 0 && (
                <p className="mt-8 text-center text-sm text-slate-400">Your list is empty. Try the mic in the search bar.</p>
              )}
              {Object.entries(cart).map(([id, qty]) => {
                const p = byId[id];
                const cat = catMap[p.category];
                return (
                  <div key={id} className="mb-3 flex items-center gap-3 rounded-lg border border-slate-100 p-2.5">
                    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${cat.tint}`}>
                      <cat.icon className="h-5 w-5" strokeWidth={1.5} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800">{p.name}</p>
                      <p className="text-xs text-slate-400">{currency(p.price)} \u00b7 {p.unit}</p>
                    </div>
                    <div className="flex items-center gap-1 rounded-full bg-slate-100 px-1">
                      <button onClick={() => setQty(id, qty - 1)} className="rounded-full p-1.5 text-slate-600 hover:bg-slate-200"><Minus className="h-3.5 w-3.5" /></button>
                      <span className="w-4 text-center text-xs font-semibold">{qty}</span>
                      <button onClick={() => setQty(id, qty + 1)} className="rounded-full p-1.5 text-slate-600 hover:bg-slate-200"><Plus className="h-3.5 w-3.5" /></button>
                    </div>
                    <button onClick={() => removeFromCart(id)} className="text-slate-300 hover:text-red-500"><X className="h-4 w-4" /></button>
                  </div>
                );
              })}

              {hasMilk && (
                <div className="mt-2 flex items-start gap-2 rounded-lg border border-indigo-100 bg-indigo-50/60 p-3">
                  <ArrowLeftRight className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
                  <div className="flex-1">
                    <p className="text-xs font-semibold text-slate-700">Prefer dairy-free? Swap Whole Milk for Oat Milk.</p>
                    <button onClick={() => swapItem("p4", "p5")} className="mt-1 text-xs font-semibold text-indigo-700 hover:text-indigo-900">Swap it \u2192</button>
                  </div>
                </div>
              )}
            </div>
            <div className="border-t border-slate-100 px-5 py-4">
              <div className="mb-3 flex items-center justify-between text-sm">
                <span className="text-slate-500">Estimated total</span>
                <span className="font-serif text-lg font-bold">{currency(cartTotal)}</span>
              </div>
              <button className="w-full rounded-full bg-slate-900 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">
                Mark list ready for the store
              </button>
              <p className="mt-2 text-center text-[11px] text-slate-400">Cartly manages your list \u2014 it doesn't place orders or take payment.</p>
            </div>
          </div>
        </div>
      )}

      {/* voice panel */}
      {voiceOpen && (
        <div className="fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-6 sm:items-center sm:pb-0">
          <div className="w-full max-w-sm rounded-2xl border border-indigo-100 bg-white p-5 text-center shadow-2xl">
            <div className="relative mx-auto mb-3 flex h-16 w-16 items-center justify-center">
              {voiceState === "listening" && <span className="absolute h-full w-full animate-ping rounded-full bg-indigo-400/40" />}
              <span className={`relative flex h-14 w-14 items-center justify-center rounded-full ${voiceState === "done" ? "bg-emerald-500" : "bg-indigo-600"}`}>
                {voiceState === "done" ? <Check className="h-6 w-6 text-white" /> : <Mic className="h-6 w-6 text-white" />}
              </span>
            </div>
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500">
              {voiceState === "listening" ? "Listening\u2026" : voiceState === "heard" ? "Got it" : "Added to your list"}
            </p>
            <p className="mt-2 text-sm text-slate-700">
              {voiceState === "listening" ? "Say something like " + VOICE_DEMO_LINE : VOICE_DEMO_LINE}
            </p>
            {voiceState === "done" && (
              <p className="mt-2 text-xs text-slate-400">2 \u00d7 Oat Milk, 1 \u00d7 Organic Strawberries</p>
            )}
          </div>
        </div>
      )}

      {/* toast */}
      {toast && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-full bg-slate-900 px-4 py-2 text-xs font-medium text-white shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
