// CS2: Product Catalog — BEFORE (clean)
import React, { useState, useCallback, useMemo } from 'react';

interface Product {
  id: number;
  name: string;
  price: number;
  category: string;
  stock: number;
}

interface ProductCardProps {
  product: Product;
  onAddToCart: (id: number) => void;
}

const ProductCard = React.memo(function ProductCard({ product, onAddToCart }: ProductCardProps) {
  return (
    <div className="product-card">
      <h3>{product.name}</h3>
      <p className="price">${product.price.toFixed(2)}</p>
      <p className="category">{product.category}</p>
      <p className="stock">{product.stock > 0 ? `${product.stock} in stock` : 'Out of stock'}</p>
      <button disabled={product.stock === 0} onClick={() => onAddToCart(product.id)}>
        Add to Cart
      </button>
    </div>
  );
});

export default function ProductCatalog({ products }: { products: Product[] }) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [sortBy, setSortBy] = useState<'price' | 'name'>('name');

  const categories = useMemo(() =>
    ['all', ...new Set(products.map(p => p.category))],
    [products]
  );

  const handleAddToCart = useCallback((id: number) => {
    console.log('added to cart:', id);
  }, []);

  const filtered = useMemo(() =>
    products
      .filter(p => category === 'all' || p.category === category)
      .filter(p => p.name.toLowerCase().includes(search.toLowerCase()))
      .sort((a, b) => sortBy === 'price' ? a.price - b.price : a.name.localeCompare(b.name)),
    [products, category, search, sortBy]
  );

  return (
    <div className="catalog">
      <div className="controls">
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..." />
        <select value={category} onChange={e => setCategory(e.target.value)}>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={sortBy} onChange={e => setSortBy(e.target.value as 'price' | 'name')}>
          <option value="name">Sort by Name</option>
          <option value="price">Sort by Price</option>
        </select>
      </div>
      <div className="product-grid">
        {filtered.map(p => <ProductCard key={p.id} product={p} onAddToCart={handleAddToCart} />)}
      </div>
    </div>
  );
}
